"""
Silae-style BPA "État d'avancement" matrix API.

Stored statuses (table employee_period_status): SAISIE, EN_CALCUL, CLOTURE.
Derived at read time (never stored, so never fake):
  - NONE        : month before the employee's hire month
  - FUTUR       : month after the current calendar month
  - A_CALCULER  : past month with no stored row (overdue)
  - EN_COURS    : current month with no row, or stored SAISIE
  - EN_CALCUL   : calculated, waiting for closing
  - CLOTURE     : sealed (also derived from a closed payroll_cycles row)
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from syncra_engine.db import get_connection

router = APIRouter(prefix="/api/matrix", tags=["matrix"])

STORED = ("SAISIE", "EN_CALCUL", "CLOTURE")
MAX_MONTHS = 120


# ------------------------------ payroll maths ------------------------------ #
def calculate_irg(taxable_base: float) -> int:
    """Barème IRG 2022 (same rules as the payslip view)."""
    base = int(taxable_base // 10) * 10
    if base <= 30000:
        return 0
    brut = 0.0
    brackets = [(20000, 40000, 0.23), (40000, 80000, 0.27), (80000, 160000, 0.30),
                (160000, 320000, 0.33), (320000, None, 0.35)]
    for low, high, rate in brackets:
        if base > low:
            upper = min(base, high) if high else base
            brut += (upper - low) * rate
    abatt = max(1000.0, min(1500.0, brut * 0.40))
    net_tax = max(0.0, brut - abatt)
    if 30000 < base < 35000:
        net_tax = max(0.0, net_tax * (137 / 51) - (27925 / 8))
    return int(round(net_tax))


def compute_payslip(emp, cur=None, year=None, month=None, variables=None) -> dict:
    emp = dict(emp)
    base = float(emp.get("base_salary") or 0)
    seniority = float(emp.get("seniority_allowance") or 0)
    
    # Load variables for the period if available from DB
    v = variables or {}
    if not v and cur and year and month:
        cur.execute("""
            SELECT * FROM employee_monthly_variables
            WHERE tenant_id = ? AND employee_id = ? AND year = ? AND month = ?
        """, (emp["tenant_id"], emp["id"], year, month))
        row = cur.fetchone()
        if row:
            v = dict(row)

    # 1. Base salary adjustments (Absences: Article 86 / Algerian Labor Law)
    absence_days = float(v.get("absence_days") or 0.0)
    daily_rate = base / 30.0 if base > 0 else 0.0
    absence_deduction = round(absence_days * daily_rate, 2)
    adjusted_base = max(0.0, base - absence_deduction)

    # 2. Overtime (Heures supplémentaires: Law 90-11 Art. 31/32)
    # Monthly standard working hours = 173.33 hours (40 hours/week)
    hourly_rate = (base / 173.33) if base > 0 else 0.0
    hs_50 = float(v.get("heures_supp_50") or 0.0)
    hs_100 = float(v.get("heures_supp_100") or 0.0)
    overtime_amount = round((hs_50 * hourly_rate * 1.50) + (hs_100 * hourly_rate * 2.00), 2)

    # 3. Monthly variable primes & bonuses
    prime_rendement = float(v.get("prime_rendement") or 0.0)
    monthly_bonus = float(v.get("bonus") or 0.0)
    contract_bonus = float(emp["bonus"] or 0.0)
    total_bonus = round(contract_bonus + monthly_bonus + prime_rendement, 2)

    # 4. Gross Cotisable Salary (Assiette Cotisable SS)
    gross = round(adjusted_base + seniority + overtime_amount + total_bonus, 2)

    # 5. CNAS 9% (Salariale) & 25% (Patronale)
    cnas_employee = round(gross * 0.09, 2)
    cnas_patronale = round(gross * 0.25, 2)

    # 6. IRG Taxable Base & Calculation (Barème 2022)
    taxable_base = max(0.0, gross - cnas_employee)
    irg = calculate_irg(taxable_base)

    # 7. Non-cotisable, non-imposable indemnities (Art. 86 Loi 90-11)
    transport = float(v.get("transport_allowance") or emp.get("transport_allowance") or 0.0)
    basket = float(v.get("basket_allowance") or emp.get("basket_allowance") or 0.0)
    mission = float(v.get("mission_expense") or emp.get("mission_expense") or 0.0)
    total_exempt_allowances = round(transport + basket + mission, 2)

    # 8. Advances / Acomptes
    acompte = float(v.get("acompte") or 0.0)

    # 9. Net à payer
    net = round(gross - cnas_employee - irg + total_exempt_allowances - acompte, 2)

    return {
        "base": round(base, 2),
        "adjusted_base": round(adjusted_base, 2),
        "absence_days": absence_days,
        "absence_deduction": absence_deduction,
        "seniority": round(seniority, 2),
        "heures_supp_50": hs_50,
        "heures_supp_100": hs_100,
        "overtime_amount": overtime_amount,
        "prime_rendement": prime_rendement,
        "bonus": total_bonus,
        "gross": gross,
        "cnas_employee": cnas_employee,
        "cnas_patronale": cnas_patronale,
        "taxable_base": round(taxable_base, 2),
        "irg": float(irg),
        "transport_allowance": transport,
        "basket_allowance": basket,
        "mission_expense": mission,
        "exempt_allowances": total_exempt_allowances,
        "acompte": acompte,
        "net": net
    }


# -------------------------------- helpers --------------------------------- #
def _parse_period(p: str):
    try:
        y, m = p.split("-")
        y, m = int(y), int(m)
        if not (1 <= m <= 12):
            raise ValueError
        return y, m
    except Exception:
        raise HTTPException(status_code=400, detail=f"Période invalide: {p} (attendu YYYY-MM)")


def _range(frm: str, to: str):
    fy, fm = _parse_period(frm)
    ty, tm = _parse_period(to)
    out = []
    y, m = fy, fm
    while (y, m) <= (ty, tm):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
        if len(out) > MAX_MONTHS:
            raise HTTPException(status_code=400, detail=f"Plage trop grande (max {MAX_MONTHS} mois)")
    if not out:
        raise HTTPException(status_code=400, detail="Plage vide: 'from' doit précéder 'to'")
    return out


def _now_period():
    n = datetime.now()
    return n.year, n.month


def _hire_period(hire_date: Optional[str]):
    try:
        y, m = (hire_date or "")[:7].split("-")
        return int(y), int(m)
    except Exception:
        return (1900, 1)


def _derive(period, hire, stored, cycle_closed):
    """Return display status for one cell."""
    if period < hire:
        return "NONE"
    if stored:
        return stored
    if cycle_closed:
        return "CLOTURE"
    now = _now_period()
    if period > now:
        return "FUTUR"
    if period < now:
        return "A_CALCULER"
    return "EN_COURS"


def _display(status):
    return "EN_COURS" if status == "SAISIE" else status


def _audit(cursor, tenant_id, action, details):
    cursor.execute("INSERT INTO audit_logs (tenant_id, action, details) VALUES (?, ?, ?)",
                   (tenant_id, action, details))


# ---------------------------------- read ----------------------------------- #
@router.get("")
def get_matrix(tenant_id: str = Query(...), frm: str = Query(..., alias="from"), to: str = Query(...)):
    periods = _range(frm, to)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE tenant_id = ? AND COALESCE(is_active,1) = 1 ORDER BY id", (tenant_id,))
    emps = cur.fetchall()
    cur.execute("SELECT * FROM employee_period_status WHERE tenant_id = ?", (tenant_id,))
    rows = {(r["employee_id"], r["year"], r["month"]): r for r in cur.fetchall()}
    cur.execute("SELECT year, month FROM payroll_cycles WHERE tenant_id = ? AND status = 'CLOTURE'", (tenant_id,))
    closed_cycles = {(r["year"], r["month"]) for r in cur.fetchall()}
    conn.close()

    emp_out = []
    agg = {p: [] for p in periods}
    for e in emps:
        hire = _hire_period(e["hire_date"])
        cells = {}
        for p in periods:
            r = rows.get((e["id"], p[0], p[1]))
            st = _derive(p, hire, r["status"] if r else None, p in closed_cycles and not r)
            cell = {"status": st}
            if r and r["net"] is not None:
                cell.update({"gross": r["gross"], "net": r["net"], "irg": r["irg"],
                             "cnas_employee": r["cnas_employee"]})
            cells[f"{p[0]:04d}-{p[1]:02d}"] = cell
            agg[p].append(_display(st))
        emp_out.append({"id": e["id"], "name": e["name"], "job_title": e["job_title"],
                        "department": e["department"], "contract_type": e["contract_type"],
                        "base_salary": e["base_salary"], "cells": cells})

    # Task rows derived from the employee statuses (no hard-coded arrays)
    tasks = {"bulletins": {}, "virements": {}, "declarations": {}}
    for p in periods:
        key = f"{p[0]:04d}-{p[1]:02d}"
        sts = [s for s in agg[p] if s != "NONE"]
        if not sts:
            b = "FUTUR" if p > _now_period() else "NONE"
        elif all(s == "CLOTURE" for s in sts):
            b = "CLOTURE"
        elif all(s == "FUTUR" for s in sts):
            b = "FUTUR"
        elif any(s == "A_CALCULER" for s in sts):
            b = "A_CALCULER"
        else:
            b = "EN_COURS"
        tasks["bulletins"][key] = b
        ready = "EN_COURS" if b == "CLOTURE" else ("FUTUR" if b in ("FUTUR", "NONE") else "FUTUR")
        tasks["virements"][key] = ready
        tasks["declarations"][key] = ready

    return {"tenant_id": tenant_id,
            "current": f"{_now_period()[0]:04d}-{_now_period()[1]:02d}",
            "periods": [f"{y:04d}-{m:02d}" for y, m in periods],
            "employees": emp_out, "tasks": tasks}


# --------------------------------- write ----------------------------------- #
class CellsRequest(BaseModel):
    tenant_id: str
    employee_ids: List[str]
    periods: List[str]
    status: Optional[str] = None


def _load_emp(cur, tenant_id, emp_id):
    cur.execute("SELECT * FROM employees WHERE tenant_id = ? AND id = ?", (tenant_id, emp_id))
    return cur.fetchone()


def _apply(req: CellsRequest, target: str):
    if target not in STORED:
        raise HTTPException(status_code=400, detail=f"Statut non valide: {target}")
    conn = get_connection()
    cur = conn.cursor()
    changed, skipped = [], []
    now = datetime.utcnow().isoformat()
    touched = set()
    for pstr in req.periods:
        period = _parse_period(pstr)
        for emp_id in req.employee_ids:
            emp = _load_emp(cur, req.tenant_id, emp_id)
            if not emp:
                skipped.append({"employee_id": emp_id, "period": pstr, "reason": "employé introuvable"})
                continue
            if period > _now_period():
                skipped.append({"employee_id": emp_id, "period": pstr, "reason": "période future"})
                continue
            if period < _hire_period(emp["hire_date"]):
                skipped.append({"employee_id": emp_id, "period": pstr, "reason": "avant embauche"})
                continue
            cur.execute("""SELECT * FROM employee_period_status
                           WHERE tenant_id=? AND employee_id=? AND year=? AND month=?""",
                        (req.tenant_id, emp_id, period[0], period[1]))
            row = cur.fetchone()
            current = row["status"] if row else None
            if current == "CLOTURE":
                skipped.append({"employee_id": emp_id, "period": pstr, "reason": "bulletin clôturé : réouverture strictement interdite"})
                continue
            if target == "SAISIE":
                skipped.append({"employee_id": emp_id, "period": pstr, "reason": "la réouverture d'un bulletin est strictement interdite"})
                continue
            pid = f"PS-{req.tenant_id}-{emp_id}-{period[0]}-{period[1]}"
            calc = compute_payslip(emp, cur=cur, year=period[0], month=period[1])
            gross, cnas, irg, net = calc["gross"], calc["cnas_employee"], calc["irg"], calc["net"]
            calc_at = (row["calculated_at"] if row and row["calculated_at"] else now) if target == "CLOTURE" else now
            closed_at = now if target == "CLOTURE" else None
            cur.execute("""
                INSERT INTO employee_period_status
                  (id, tenant_id, employee_id, year, month, status, gross, cnas_employee, irg, net,
                   calculated_at, closed_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id, employee_id, year, month) DO UPDATE SET
                  status=excluded.status, gross=excluded.gross, cnas_employee=excluded.cnas_employee,
                  irg=excluded.irg, net=excluded.net, calculated_at=excluded.calculated_at,
                  closed_at=excluded.closed_at, updated_at=excluded.updated_at
            """, (pid, req.tenant_id, emp_id, period[0], period[1], target, gross, cnas, irg, net,
                  calc_at, closed_at, now))
            changed.append({"employee_id": emp_id, "period": pstr, "status": _display(target), "net": net})
            touched.add(period)

    # Sync company-level cycle when every active employee of a month is closed
    for (y, m) in touched:
        cur.execute("SELECT COUNT(*) c FROM employees WHERE tenant_id=? AND COALESCE(is_active,1)=1",
                    (req.tenant_id,))
        total_emps = cur.fetchone()["c"]
        cur.execute("""SELECT COUNT(*) c, COALESCE(SUM(gross),0) g, COALESCE(SUM(cnas_employee),0) s,
                              COALESCE(SUM(irg),0) i, COALESCE(SUM(net),0) n
                       FROM employee_period_status
                       WHERE tenant_id=? AND year=? AND month=? AND status='CLOTURE'""",
                    (req.tenant_id, y, m))
        agg = cur.fetchone()
        cycle_id = f"CYCLE-{req.tenant_id}-{m}-{y}"
        if total_emps and agg["c"] >= total_emps:
            cur.execute("""
                INSERT INTO payroll_cycles (id, tenant_id, month, year, status, total_brut,
                                            total_cnas_sal, total_irg, total_net, closed_at)
                VALUES (?,?,?,?, 'CLOTURE', ?,?,?,?, ?)
                ON CONFLICT(id) DO UPDATE SET status='CLOTURE', total_brut=excluded.total_brut,
                  total_cnas_sal=excluded.total_cnas_sal, total_irg=excluded.total_irg,
                  total_net=excluded.total_net, closed_at=excluded.closed_at
            """, (cycle_id, req.tenant_id, m, y, agg["g"], agg["s"], agg["i"], agg["n"], now))
        elif target == "SAISIE":
            cur.execute("UPDATE payroll_cycles SET status='SAISIE', closed_at=NULL WHERE id=? AND status='CLOTURE'",
                        (cycle_id,))

    if changed:
        _audit(cur, req.tenant_id, f"MATRIX_{target}",
               f"{len(changed)} cellule(s) -> {target} ({', '.join(sorted({c['period'] for c in changed}))})")
    conn.commit()
    conn.close()
    return {"success": True, "changed": changed, "skipped": skipped}


@router.post("/status")
def set_status(req: CellsRequest):
    if not req.status:
        raise HTTPException(status_code=400, detail="status requis")
    return _apply(req, req.status)


@router.post("/calculate")
def calculate(req: CellsRequest):
    return _apply(req, "EN_CALCUL")


@router.post("/close")
def close(req: CellsRequest):
    return _apply(req, "CLOTURE")


@router.post("/reopen")
def reopen(req: CellsRequest):
    raise HTTPException(status_code=403, detail="La réouverture des bulletins est strictement interdite (non autorisée).")
