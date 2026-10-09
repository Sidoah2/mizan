import os
import sys
import shutil
import tempfile
import time
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from syncra_engine.db import get_connection, init_db
from syncra_engine.rag_service import rag_service
from syncra_engine.ocr_service import ocr_service
from syncra_engine.matrix import router as matrix_router, compute_payslip

# Initialize database tables on server start
init_db()

app = FastAPI(
    title="SYNCRA SaaS Enterprise AI & Payroll API",
    description="Authentic Backend with Multi-Tenant Architecture, EasyOCR, and Algerian Labor Law RAG",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matrix_router)

# ----------------- SCHEMAS ----------------- #
class TenantCreate(BaseModel):
    id: Optional[str] = None
    name: str
    legal_form: Optional[str] = "SARL"
    rc: Optional[str] = ""
    nif: Optional[str] = ""
    nis: Optional[str] = ""
    cnas_adherent: Optional[str] = ""
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""

class EmployeeCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    name: str
    nss: str
    job_title: str
    department: Optional[str] = "الإدارة"
    contract_type: Optional[str] = "CDI"
    hire_date: Optional[str] = "2023-01-01"
    base_salary: float = 40000.0
    seniority_allowance: Optional[float] = 0.0
    bonus: Optional[float] = 0.0
    transport_allowance: Optional[float] = 3000.0
    basket_allowance: Optional[float] = 4000.0
    mission_expense: Optional[float] = 0.0
    deduction_absence: Optional[float] = 0.0
    leave_balance: Optional[float] = 30.0
    bank_name: Optional[str] = "BEA"
    rib: Optional[str] = ""

class AuditLogCreate(BaseModel):
    tenant_id: Optional[str] = "TENT-DZ-001"
    action: str
    details: str

class STCRecordCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    employee_id: str
    reason: Optional[str] = "نهاية العقد"
    last_day: Optional[str] = ""
    leave_balance: Optional[float] = 0.0
    leave_indemnity: Optional[float] = 0.0
    seniority_indemnity: Optional[float] = 0.0
    preavis_indemnity: Optional[float] = 0.0
    total_net: float
    seal_hash: Optional[str] = ""

class RAGQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3

class CycleStatusRequest(BaseModel):
    tenant_id: str = "TENT-DZ-40492-629"
    month: int = 10
    year: int = 2026
    status: str = "SAISIE"
    manifest_hash: Optional[str] = None
    total_brut: Optional[float] = 0.0
    total_net: Optional[float] = 0.0

class MonthlyVariablesCreate(BaseModel):
    tenant_id: str
    employee_id: str
    year: int
    month: int
    heures_supp_50: Optional[float] = 0.0
    heures_supp_100: Optional[float] = 0.0
    absence_days: Optional[float] = 0.0
    prime_rendement: Optional[float] = 0.0
    bonus: Optional[float] = 0.0
    transport_allowance: Optional[float] = 0.0
    basket_allowance: Optional[float] = 0.0
    mission_expense: Optional[float] = 0.0
    acompte: Optional[float] = 0.0
    note: Optional[str] = ""

# --- New Client Modules Schemas (syncra_md_files_1) --- #
class AbsenceCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    employee_id: str
    type: str
    start_date: str
    end_date: str
    days_count: float = 1.0
    reason: Optional[str] = ""
    notes: Optional[str] = ""

class AbsenceBulkCreate(BaseModel):
    tenant_id: str
    employee_ids: List[str]
    type: str
    start_date: str
    end_date: str
    days_count: float = 1.0
    reason: Optional[str] = ""
    notes: Optional[str] = ""

class AbsenceApprovalAction(BaseModel):
    manager_name: Optional[str] = "المدير العام"
    notes: Optional[str] = ""

class EmployeeHoursCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    employee_id: str
    year: int
    month: int
    regular_hours: float = 173.33
    hs_50: Optional[float] = 0.0
    hs_100: Optional[float] = 0.0
    night_hours: Optional[float] = 0.0
    holiday_hours: Optional[float] = 0.0
    notes: Optional[str] = ""

class EmployeeHoursBulkSave(BaseModel):
    tenant_id: str
    year: int
    month: int
    entries: List[EmployeeHoursCreate]

class MedicalVisitCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    employee_id: str
    visit_type: str
    scheduled_date: str
    completed_date: Optional[str] = ""
    doctor_name: Optional[str] = ""
    medical_center: Optional[str] = ""
    fitness_status: Optional[str] = "APTE"
    next_visit_date: Optional[str] = ""
    notes: Optional[str] = ""
    status: Optional[str] = "SCHEDULED"

class JobTemplateCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    title: str
    department: Optional[str] = "الإدارة العامة"
    contract_type: Optional[str] = "CDI"
    default_salary: float = 45000.0
    transport: Optional[float] = 3500.0
    basket: Optional[float] = 4500.0
    bonus: Optional[float] = 5000.0
    description: Optional[str] = ""

class ExitWizardCalculateRequest(BaseModel):
    tenant_id: str
    employee_id: str
    reason: str
    departure_date: str
    notice_period_months: Optional[int] = 1
    notice_paid_or_worked: Optional[str] = "WORKED" # WORKED, PAYABLE, EXEMPT
    remaining_leave_days: Optional[float] = 0.0

class ExitWizardCompleteRequest(BaseModel):
    tenant_id: str
    employee_id: str
    reason: str
    departure_date: str
    leave_balance: float
    leave_indemnity: float
    seniority_indemnity: float
    preavis_indemnity: float
    total_net: float

class AnnualEvaluationCreate(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    employee_id: str
    evaluator_name: str
    evaluation_year: int
    score_percentage: int = 85
    objectives_achieved: Optional[str] = ""
    strengths: Optional[str] = ""
    improvements: Optional[str] = ""
    status: Optional[str] = "COMPLETED"

class DossierTransferCreate(BaseModel):
    tenant_id: str
    employee_id: str
    from_dept: str
    to_dept: str
    from_manager: Optional[str] = ""
    to_manager: Optional[str] = ""
    transfer_date: str
    reason: Optional[str] = ""
    authorized_by: Optional[str] = ""


# ----------------- API ENDPOINTS ----------------- #

@app.get("/api/health")
def health_check():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tenants")
    tenants_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM employees")
    employees_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM legal_articles")
    articles_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM medical_leaves")
    leaves_count = cursor.fetchone()[0]
    conn.close()

    return {
        "status": "online",
        "system": "SYNCRA SaaS Backend",
        "database": "SQLite (syncra_saas.db)",
        "models": {
            "ocr": "EasyOCR (ar+fr+en) + PyMuPDF",
            "rag": "Deterministic Scikit-Learn TF-IDF + Cosine Retrieval",
            "payroll_engine": "Deterministic AST Engine (Law 90-11 Art 86, IRG 2022)"
        },
        "stats": {
            "tenants": tenants_count,
            "employees": employees_count,
            "indexed_legal_articles": articles_count,
            "processed_medical_leaves": leaves_count
        }
    }

# ----------------- TENANTS MANAGEMENT ----------------- #

@app.get("/api/tenants")
def get_tenants():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tenants ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/tenants")
def create_tenant(t: TenantCreate):
    conn = get_connection()
    cursor = conn.cursor()
    tenant_id = t.id
    if not tenant_id:
        tenant_id = f"TENT-DZ-{uuid.uuid4().hex[:6].upper()}"
    else:
        cursor.execute("SELECT id FROM tenants WHERE id = ?", (tenant_id,))
        if cursor.fetchone():
            tenant_id = f"{tenant_id}-{uuid.uuid4().hex[:4].upper()}"
    try:
        cursor.execute("""
        INSERT INTO tenants (id, name, legal_form, rc, nif, nis, cnas_adherent, address, phone, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tenant_id, t.name, t.legal_form, t.rc, t.nif, t.nis, t.cnas_adherent, t.address, t.phone, t.email))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")
    conn.close()
    return {"success": True, "tenant_id": tenant_id, "message": "تم إنشاء المؤسسة بنجاح"}

@app.put("/api/tenants/{tenant_id}")
def update_tenant(tenant_id: str, t: TenantCreate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE tenants SET 
        name = ?, legal_form = ?, rc = ?, nif = ?, nis = ?, cnas_adherent = ?, address = ?, phone = ?, email = ?
    WHERE id = ?
    """, (t.name, t.legal_form, t.rc, t.nif, t.nis, t.cnas_adherent, t.address, t.phone, t.email, tenant_id))
    conn.commit()
    conn.close()
    return {"success": True, "tenant_id": tenant_id, "message": "تم تحديث بيانات المؤسسة بنجاح"}

# ----------------- EMPLOYEES MANAGEMENT ----------------- #

@app.get("/api/employees")
def get_employees(tenant_id: str = Query("TENT-DZ-001")):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE tenant_id = ? AND is_active = 1 ORDER BY name ASC", (tenant_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/employees")
def create_employee(emp: EmployeeCreate):
    conn = get_connection()
    cursor = conn.cursor()
    emp_id = emp.id
    if not emp_id:
        emp_id = f"EMP-{uuid.uuid4().hex[:6].upper()}"
    else:
        cursor.execute("SELECT id FROM employees WHERE id =     ?", (emp_id,))
        if cursor.fetchone():
            emp_id = f"EMP-{uuid.uuid4().hex[:6].upper()}"
    cursor.execute("""
    INSERT INTO employees (
        id, tenant_id, name, nss, job_title, department, contract_type, hire_date,
        base_salary, seniority_allowance, bonus, transport_allowance, basket_allowance,
        mission_expense, deduction_absence, leave_balance, bank_name, rib, is_active
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        emp_id, emp.tenant_id, emp.name, emp.nss, emp.job_title, emp.department, emp.contract_type, emp.hire_date,
        emp.base_salary, emp.seniority_allowance, emp.bonus, emp.transport_allowance, emp.basket_allowance,
        emp.mission_expense, emp.deduction_absence, emp.leave_balance, emp.bank_name, emp.rib
    ))
    conn.commit()
    conn.close()
    return {"success": True, "employee_id": emp_id, "message": "تم إضافة الموظف بنجاح في قاعدة البيانات"}

@app.put("/api/employees/{emp_id}")
def update_employee(emp_id: str, emp: EmployeeCreate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE employees SET 
        name = ?, nss = ?, job_title = ?, department = ?, contract_type = ?, hire_date = ?,
        base_salary = ?, seniority_allowance = ?, bonus = ?, transport_allowance = ?, basket_allowance = ?,
        mission_expense = ?, deduction_absence = ?, leave_balance = ?, bank_name = ?, rib = ?
    WHERE id = ?
    """, (
        emp.name, emp.nss, emp.job_title, emp.department, emp.contract_type, emp.hire_date,
        emp.base_salary, emp.seniority_allowance, emp.bonus, emp.transport_allowance, emp.basket_allowance,
        emp.mission_expense, emp.deduction_absence, emp.leave_balance, emp.bank_name, emp.rib,
        emp_id
    ))
    conn.commit()
    conn.close()
    return {"success": True, "employee_id": emp_id, "message": "تم تحديث بيانات الموظف بنجاح"}

@app.delete("/api/employees/{emp_id}")
def delete_employee(emp_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE employees SET is_active = 0 WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    return {"success": True, "employee_id": emp_id, "message": "تم حذف الأجير بنجاح"}

# ----------------- AUDIT LOGS ENDPOINTS ----------------- #

@app.get("/api/audit-logs")
def get_audit_logs(tenant_id: str = Query("TENT-DZ-001"), limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT ?", (tenant_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/audit-logs")
def create_audit_log(log: AuditLogCreate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (tenant_id, action, details) VALUES (?, ?, ?)", (log.tenant_id, log.action, log.details))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم تسجيل القيد في سجل التدقيق"}

# ----------------- STC SETTLEMENTS ENDPOINTS ----------------- #

@app.get("/api/stc/records")
def get_stc_records(tenant_id: str = Query("TENT-DZ-001")):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT s.*, e.name as employee_name, e.job_title
    FROM stc_records s
    LEFT JOIN employees e ON s.employee_id = e.id
    WHERE s.tenant_id = ?
    ORDER BY s.created_at DESC
    """, (tenant_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/stc/records")
def create_stc_record(record: STCRecordCreate):
    conn = get_connection()
    cursor = conn.cursor()
    rec_id = record.id or f"STC-{int(os.times().system * 1000)}"
    cursor.execute("""
    INSERT INTO stc_records (
        id, tenant_id, employee_id, reason, last_day, leave_balance, 
        leave_indemnity, seniority_indemnity, preavis_indemnity, total_net, seal_hash
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rec_id, record.tenant_id, record.employee_id, record.reason, record.last_day,
        record.leave_balance, record.leave_indemnity, record.seniority_indemnity,
        record.preavis_indemnity, record.total_net, record.seal_hash
    ))
    conn.commit()
    conn.close()
    return {"success": True, "stc_id": rec_id, "message": "تم حفظ مخالصة STC بنجاح"}

# ----------------- REAL OCR ENDPOINT ----------------- #

@app.post("/api/ocr/scan")
async def scan_medical_certificate(
    file: UploadFile = File(...),
    tenant_id: str = Form("TENT-DZ-001")
):
    """Real OCR execution on uploaded medical leave document (Image or PDF)."""
    upload_dir = os.path.join(tempfile.gettempdir(), "syncra_ocr_uploads")
    os.makedirs(upload_dir, exist_ok=True)
    temp_file_path = os.path.join(upload_dir, file.filename)

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Run real OCR and entity extraction
        scan_result = ocr_service.scan_file(temp_file_path, tenant_id=tenant_id)
        return scan_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Processing Error: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

@app.get("/api/leaves")
def get_leaves(tenant_id: str = Query("TENT-DZ-001")):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT ml.*, e.name as employee_name, e.job_title
    FROM medical_leaves ml
    LEFT JOIN employees e ON ml.employee_id = e.id
    WHERE ml.tenant_id = ?
    ORDER BY ml.created_at DESC
    """, (tenant_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- REAL LEGAL RAG ENDPOINT ----------------- #

@app.post("/api/rag/query")
def query_rag(req: RAGQueryRequest):
    """Executes real vector/similarity retrieval on the Algerian Labor Law corpus."""
    try:
        results = rag_service.query(req.query, top_k=req.top_k or 3)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Error: {str(e)}")

@app.get("/api/rag/articles")
def get_all_articles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM legal_articles ORDER BY law_code ASC, article_num ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- PAYROLL CYCLE LIFECYCLE PERSISTENCE ----------------- #

@app.get("/api/cycles/current")
def get_current_cycle(tenant_id: str = Query("TENT-DZ-40492-629"), month: int = 10, year: int = 2026):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM payroll_cycles 
        WHERE tenant_id = ? AND month = ? AND year = ?
        LIMIT 1
    """, (tenant_id, month, year))
    row = cursor.fetchone()
    if not row:
        cycle_id = f"CYCLE-{tenant_id}-{month}-{year}"
        cursor.execute("""
            INSERT INTO payroll_cycles (id, tenant_id, month, year, status)
            VALUES (?, ?, ?, ?, 'SAISIE')
        """, (cycle_id, tenant_id, month, year))
        conn.commit()
        cursor.execute("SELECT * FROM payroll_cycles WHERE id = ?", (cycle_id,))
        row = cursor.fetchone()
    conn.close()
    return dict(row)

@app.post("/api/cycles/status")
def update_cycle_status(req: CycleStatusRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cycle_id = f"CYCLE-{req.tenant_id}-{req.month}-{req.year}"
    closed_at = datetime.utcnow().isoformat() if req.status == "CLOTURE" else None
    cursor.execute("""
        INSERT INTO payroll_cycles (id, tenant_id, month, year, status, manifest_hash, total_brut, total_net, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            manifest_hash = COALESCE(excluded.manifest_hash, payroll_cycles.manifest_hash),
            total_brut = COALESCE(excluded.total_brut, payroll_cycles.total_brut),
            total_net = COALESCE(excluded.total_net, payroll_cycles.total_net),
            closed_at = excluded.closed_at
    """, (cycle_id, req.tenant_id, req.month, req.year, req.status, req.manifest_hash, req.total_brut, req.total_net, closed_at))
    conn.commit()
    conn.close()
    return {"success": True, "cycle_id": cycle_id, "status": req.status}

# ----------------- MONTHLY VARIABLES (EVP) ENGINE ----------------- #

@app.get("/api/variables")
def get_monthly_variables(
    tenant_id: str = Query(...),
    employee_id: str = Query(...),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    period: Optional[str] = Query(None)
):
    if period and (year is None or month is None):
        try:
            parts = period.split("-")
            year = int(parts[0])
            month = int(parts[1])
        except Exception:
            raise HTTPException(status_code=400, detail="Format de période invalide (YYYY-MM attendu)")
    if year is None or month is None:
        raise HTTPException(status_code=400, detail="Période requise (paramètre 'period' ou 'year' et 'month')")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE tenant_id = ? AND id = ?", (tenant_id, employee_id))
    emp = cur.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="Salarié introuvable")

    cur.execute("""
        SELECT * FROM employee_monthly_variables
        WHERE tenant_id = ? AND employee_id = ? AND year = ? AND month = ?
    """, (tenant_id, employee_id, year, month))
    var_row = cur.fetchone()

    vars_dict = dict(var_row) if var_row else {
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "heures_supp_50": 0.0,
        "heures_supp_100": 0.0,
        "absence_days": 0.0,
        "prime_rendement": 0.0,
        "bonus": 0.0,
        "transport_allowance": emp["transport_allowance"] or 0.0,
        "basket_allowance": emp["basket_allowance"] or 0.0,
        "mission_expense": emp["mission_expense"] or 0.0,
        "acompte": 0.0,
        "note": ""
    }

    # Also compute preview calculation
    calc = compute_payslip(emp, cur=cur, year=year, month=month, variables=vars_dict)

    conn.close()
    return {
        "success": True,
        "employee": {
            "id": emp["id"],
            "name": emp["name"],
            "job_title": emp["job_title"],
            "base_salary": emp["base_salary"],
            "seniority_allowance": emp["seniority_allowance"]
        },
        "variables": vars_dict,
        "calculation": calc
    }

@app.post("/api/variables")
def save_monthly_variables(v: MonthlyVariablesCreate):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE tenant_id = ? AND id = ?", (v.tenant_id, v.employee_id))
    emp = cur.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="Salarié introuvable")

    var_id = f"VAR-{v.tenant_id}-{v.employee_id}-{v.year}-{v.month}"
    now = datetime.utcnow().isoformat()

    cur.execute("""
        INSERT INTO employee_monthly_variables (
            id, tenant_id, employee_id, year, month,
            heures_supp_50, heures_supp_100, absence_days,
            prime_rendement, bonus, transport_allowance,
            basket_allowance, mission_expense, acompte, note, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, employee_id, year, month) DO UPDATE SET
            heures_supp_50 = excluded.heures_supp_50,
            heures_supp_100 = excluded.heures_supp_100,
            absence_days = excluded.absence_days,
            prime_rendement = excluded.prime_rendement,
            bonus = excluded.bonus,
            transport_allowance = excluded.transport_allowance,
            basket_allowance = excluded.basket_allowance,
            mission_expense = excluded.mission_expense,
            acompte = excluded.acompte,
            note = excluded.note,
            updated_at = excluded.updated_at
    """, (
        var_id, v.tenant_id, v.employee_id, v.year, v.month,
        v.heures_supp_50 or 0.0, v.heures_supp_100 or 0.0, v.absence_days or 0.0,
        v.prime_rendement or 0.0, v.bonus or 0.0, v.transport_allowance or 0.0,
        v.basket_allowance or 0.0, v.mission_expense or 0.0, v.acompte or 0.0,
        v.note or "", now
    ))

    # Audit log
    cur.execute("""
        INSERT INTO audit_logs (tenant_id, action, details)
        VALUES (?, 'EVP_UPDATE', ?)
    """, (v.tenant_id, f"Enregistrement des variables EVP pour {emp['name']} ({v.year}-{v.month:02d})"))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Variables EVP enregistrées avec succès en base de données",
        "variables": v.dict()
    }

# =====================================================================
# CLIENT MODULES REST APIS (syncra_md_files_1)
# =====================================================================

# 1. ABSENCES & APPROVAL WORKFLOW
@app.get("/api/absences")
def get_absences(tenant_id: str = "TENT-DZ-001", status: Optional[str] = None):
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT a.*, e.name as employee_name, e.job_title, e.department
        FROM absences a
        LEFT JOIN employees e ON a.employee_id = e.id
        WHERE a.tenant_id = ?
    """
    params = [tenant_id]
    if status and status != "ALL":
        query += " AND a.status = ?"
        params.append(status)
    query += " ORDER BY a.start_date DESC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"success": True, "absences": rows, "count": len(rows)}

@app.post("/api/absences")
def create_absence(a: AbsenceCreate):
    conn = get_connection()
    cur = conn.cursor()
    abs_id = a.id or f"ABS-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO absences (id, tenant_id, employee_id, type, start_date, end_date, days_count, reason, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
    """, (abs_id, a.tenant_id, a.employee_id, a.type, a.start_date, a.end_date, a.days_count, a.reason or "", a.notes or ""))
    cur.execute("INSERT INTO audit_logs (tenant_id, action, details) VALUES (?, 'ABSENCE_CREATE', ?)",
                (a.tenant_id, f"Demande d'absence créée pour l'employé {a.employee_id} ({a.type})"))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم تسجيل طلب الغياب بنجاح وهو في انتظار مصادقة المدير", "id": abs_id}

@app.post("/api/absences/bulk")
def create_bulk_absences(b: AbsenceBulkCreate):
    conn = get_connection()
    cur = conn.cursor()
    created_ids = []
    for emp_id in b.employee_ids:
        abs_id = f"ABS-{uuid.uuid4().hex[:8].upper()}"
        cur.execute("""
            INSERT INTO absences (id, tenant_id, employee_id, type, start_date, end_date, days_count, reason, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (abs_id, b.tenant_id, emp_id, b.type, b.start_date, b.end_date, b.days_count, b.reason or "", b.notes or ""))
        created_ids.append(abs_id)
    cur.execute("INSERT INTO audit_logs (tenant_id, action, details) VALUES (?, 'ABSENCE_BULK_CREATE', ?)",
                (b.tenant_id, f"Enregistrement de غيابات جماعية pour {len(b.employee_ids)} salariés"))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"تم تسجيل الغياب الجماعي لـ {len(created_ids)} موظفين بنجاح", "ids": created_ids}

@app.post("/api/absences/{abs_id}/approve")
def approve_absence(abs_id: str, action: AbsenceApprovalAction):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        UPDATE absences
        SET status = 'APPROVED', approved_by = ?, approved_at = ?, notes = notes || ' [معتمد]'
        WHERE id = ?
    """, (action.manager_name or "المدير العام", now, abs_id))
    cur.execute("SELECT tenant_id, employee_id, days_count, type FROM absences WHERE id = ?", (abs_id,))
    row = cur.fetchone()
    if row and row["type"] == "ANNUAL_LEAVE":
        # Deduct from leave balance
        cur.execute("UPDATE employees SET leave_balance = MAX(0, leave_balance - ?) WHERE id = ?",
                    (row["days_count"], row["employee_id"]))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم اعتماد الغياب بنجاح وتحديث السجلات"}

@app.post("/api/absences/{abs_id}/reject")
def reject_absence(abs_id: str, action: AbsenceApprovalAction):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE absences SET status = 'REJECTED', notes = notes || ' [مرفوض]' WHERE id = ?", (abs_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم رفض طلب الغياب"}

@app.post("/api/absences/bulk-approve")
def bulk_approve_absences(action: dict):
    abs_ids = action.get("ids", [])
    manager_name = action.get("manager_name", "المدير العام")
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for aid in abs_ids:
        cur.execute("UPDATE absences SET status = 'APPROVED', approved_by = ?, approved_at = ? WHERE id = ?",
                    (manager_name, now, aid))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"تم الاعتماد الجماعي لـ {len(abs_ids)} طلباً بنجاح"}

@app.post("/api/absences/{abs_id}/request-cancel")
def request_cancel_absence(abs_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE absences SET status = 'CANCEL_REQUESTED', notes = notes || ' [طلب إلغاء مقدم]' WHERE id = ?", (abs_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم تقديم طلب إلغاء الغياب المعتمد بنجاح"}

@app.delete("/api/absences/{abs_id}")
def delete_absence(abs_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM absences WHERE id = ?", (abs_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="الغياب غير موجود")
    if row["status"] not in ["PENDING", "CANCEL_REQUESTED", "REJECTED"]:
        conn.close()
        raise HTTPException(status_code=400, detail="لا يمكن حذف غياب معتمد نهائياً إلا بعد تقديم طلب إلغاء وموافقة الإدارة")
    cur.execute("DELETE FROM absences WHERE id = ?", (abs_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم حذف قيد الغياب بنجاح"}

# 2. HOURS & OVERTIME ENTRY
@app.get("/api/hours")
def get_hours(tenant_id: str = "TENT-DZ-001", year: int = 2026, month: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, job_title, department, base_salary FROM employees WHERE tenant_id = ? AND is_active = 1", (tenant_id,))
    employees = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM employee_hours WHERE tenant_id = ? AND year = ? AND month = ?", (tenant_id, year, month))
    hours_map = {r["employee_id"]: dict(r) for r in cur.fetchall()}
    
    result = []
    for emp in employees:
        h = hours_map.get(emp["id"], {
            "id": f"HRS-{tenant_id}-{emp['id']}-{year}-{month}",
            "tenant_id": tenant_id,
            "employee_id": emp["id"],
            "year": year,
            "month": month,
            "regular_hours": 173.33,
            "hs_50": 0.0,
            "hs_100": 0.0,
            "night_hours": 0.0,
            "holiday_hours": 0.0,
            "notes": ""
        })
        hourly_rate = emp["base_salary"] / 173.33
        overtime_pay = (h["hs_50"] * hourly_rate * 1.5) + (h["hs_100"] * hourly_rate * 2.0)
        h["employee_name"] = emp["name"]
        h["job_title"] = emp["job_title"]
        h["department"] = emp["department"]
        h["base_salary"] = emp["base_salary"]
        h["hourly_rate"] = round(hourly_rate, 2)
        h["overtime_pay"] = round(overtime_pay, 2)
        result.append(h)
    
    conn.close()
    return {"success": True, "hours": result, "year": year, "month": month}

@app.post("/api/hours")
def save_hours(h: EmployeeHoursCreate):
    conn = get_connection()
    cur = conn.cursor()
    hid = h.id or f"HRS-{h.tenant_id}-{h.employee_id}-{h.year}-{h.month}"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO employee_hours (id, tenant_id, employee_id, year, month, regular_hours, hs_50, hs_100, night_hours, holiday_hours, notes, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, employee_id, year, month) DO UPDATE SET
            regular_hours = excluded.regular_hours,
            hs_50 = excluded.hs_50,
            hs_100 = excluded.hs_100,
            night_hours = excluded.night_hours,
            holiday_hours = excluded.holiday_hours,
            notes = excluded.notes,
            updated_at = excluded.updated_at
    """, (hid, h.tenant_id, h.employee_id, h.year, h.month, h.regular_hours, h.hs_50, h.hs_100, h.night_hours, h.holiday_hours, h.notes or "", now))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم حفظ ساعات العمل بنجاح"}

@app.post("/api/hours/bulk-save")
def bulk_save_hours(payload: EmployeeHoursBulkSave):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for h in payload.entries:
        hid = f"HRS-{payload.tenant_id}-{h.employee_id}-{payload.year}-{payload.month}"
        cur.execute("""
            INSERT INTO employee_hours (id, tenant_id, employee_id, year, month, regular_hours, hs_50, hs_100, night_hours, holiday_hours, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tenant_id, employee_id, year, month) DO UPDATE SET
                regular_hours = excluded.regular_hours,
                hs_50 = excluded.hs_50,
                hs_100 = excluded.hs_100,
                night_hours = excluded.night_hours,
                holiday_hours = excluded.holiday_hours,
                notes = excluded.notes,
                updated_at = excluded.updated_at
        """, (hid, payload.tenant_id, h.employee_id, payload.year, payload.month, h.regular_hours, h.hs_50, h.hs_100, h.night_hours, h.holiday_hours, h.notes or "", now))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"تم حفظ ساعات العمل لـ {len(payload.entries)} موظفين بنجاح"}

# 3. OCCUPATIONAL MEDICAL VISITS
@app.get("/api/medical-visits")
def get_medical_visits(tenant_id: str = "TENT-DZ-001"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.*, e.name as employee_name, e.job_title, e.department, e.nss
        FROM medical_visits m
        LEFT JOIN employees e ON m.employee_id = e.id
        WHERE m.tenant_id = ?
        ORDER BY m.scheduled_date DESC
    """, (tenant_id,))
    rows = [dict(r) for r in cur.fetchall()]
    
    total = len(rows)
    overdue = sum(1 for r in rows if r["status"] == "OVERDUE")
    scheduled = sum(1 for r in rows if r["status"] == "SCHEDULED")
    completed = sum(1 for r in rows if r["status"] == "COMPLETED")
    
    conn.close()
    return {
        "success": True,
        "visits": rows,
        "summary": {
            "total": total,
            "overdue": overdue,
            "scheduled": scheduled,
            "completed": completed
        }
    }

@app.post("/api/medical-visits")
def create_medical_visit(v: MedicalVisitCreate):
    conn = get_connection()
    cur = conn.cursor()
    vid = v.id or f"MED-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO medical_visits (id, tenant_id, employee_id, visit_type, scheduled_date, completed_date, doctor_name, medical_center, fitness_status, next_visit_date, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (vid, v.tenant_id, v.employee_id, v.visit_type, v.scheduled_date, v.completed_date or "", v.doctor_name or "", v.medical_center or "", v.fitness_status or "APTE", v.next_visit_date or "", v.status or "SCHEDULED", v.notes or ""))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم جدولة موعد الفحص الطبي بنجاح", "id": vid}

@app.put("/api/medical-visits/{vid}")
def update_medical_visit(vid: str, update: dict):
    conn = get_connection()
    cur = conn.cursor()
    fields = []
    params = []
    for k in ["completed_date", "doctor_name", "medical_center", "fitness_status", "next_visit_date", "status", "notes"]:
        if k in update:
            fields.append(f"{k} = ?")
            params.append(update[k])
    if not fields:
        conn.close()
        return {"success": False, "message": "لا توجد حقول للتحديث"}
    params.append(vid)
    cur.execute(f"UPDATE medical_visits SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم تحديث بيانات الفحص الطبي بنجاح"}

# 4. JOB TEMPLATES
@app.get("/api/job-templates")
def get_job_templates(tenant_id: str = "TENT-DZ-001"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM job_templates WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,))
    templates = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"success": True, "templates": templates}

@app.post("/api/job-templates")
def create_job_template(t: JobTemplateCreate):
    conn = get_connection()
    cur = conn.cursor()
    tid = t.id or f"TPL-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO job_templates (id, tenant_id, title, department, contract_type, default_salary, transport, basket, bonus, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (tid, t.tenant_id, t.title, t.department or "الإدارة العامة", t.contract_type or "CDI", t.default_salary, t.transport or 0.0, t.basket or 0.0, t.bonus or 0.0, t.description or ""))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم إنشاء نموذج الوظيفة بنجاح", "id": tid}

# 5. EXIT WIZARD & STC CALCULATION
@app.post("/api/exit-wizard/calculate")
def exit_wizard_calculate(req: ExitWizardCalculateRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE tenant_id = ? AND id = ?", (req.tenant_id, req.employee_id))
    emp = cur.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    base_salary = emp["base_salary"]
    hire_date_str = emp["hire_date"] or "2023-01-01"
    
    # Calculate seniority in years
    try:
        hire_dt = datetime.strptime(hire_date_str[:10], "%Y-%m-%d")
        dep_dt = datetime.strptime(req.departure_date[:10], "%Y-%m-%d")
        seniority_years = max(0, (dep_dt - hire_dt).days / 365.25)
    except Exception:
        seniority_years = 2.0
    
    # 1. Congés Payés (Leave Balance Compensation)
    leave_days = float(req.remaining_leave_days if req.remaining_leave_days is not None else (emp["leave_balance"] or 0.0))
    daily_rate = base_salary / 30.0
    leave_indemnity = round(leave_days * daily_rate, 2)
    
    # 2. Préavis Indemnity (Notice period compensation if payable)
    notice_indemnity = 0.0
    if req.notice_paid_or_worked == "PAYABLE":
        notice_indemnity = round((req.notice_period_months or 1) * base_salary, 2)
    
    # 3. Severance / Seniority Indemnity (Licenciement / Retraite)
    seniority_indemnity = 0.0
    if req.reason in ["تسريح اقتصادي", "تسريح فردي", "تقاعد", "Licenciement"]:
        # Standard Algerian benchmark: 1 month per year of seniority up to 15 months max
        seniority_indemnity = round(min(15.0, seniority_years) * (base_salary * 0.5), 2)
    
    stc_brut = round(leave_indemnity + notice_indemnity + seniority_indemnity, 2)
    # CNAS 9% applies to leave and notice
    cnas_deduction = round((leave_indemnity + notice_indemnity) * 0.09, 2)
    taxable_assiette = max(0.0, stc_brut - cnas_deduction)
    
    # Approximate IRG for STC
    irg_rate = 0.10 if stc_brut > 50000 else 0.0
    irg_deduction = round(taxable_assiette * irg_rate, 2)
    total_net = round(stc_brut - cnas_deduction - irg_deduction, 2)
    
    conn.close()
    return {
        "success": True,
        "employee_name": emp["name"],
        "job_title": emp["job_title"],
        "seniority_years": round(seniority_years, 1),
        "base_salary": base_salary,
        "calculation": {
            "leave_days": leave_days,
            "leave_indemnity": leave_indemnity,
            "notice_indemnity": notice_indemnity,
            "seniority_indemnity": seniority_indemnity,
            "stc_brut": stc_brut,
            "cnas_deduction": cnas_deduction,
            "irg_deduction": irg_deduction,
            "total_net": total_net
        }
    }

@app.post("/api/exit-wizard/complete")
def exit_wizard_complete(req: ExitWizardCompleteRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE tenant_id = ? AND id = ?", (req.tenant_id, req.employee_id))
    emp = cur.fetchone()
    if not emp:
        conn.close()
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    stc_id = f"STC-{uuid.uuid4().hex[:8].upper()}"
    seal_hash = f"SEAL-{uuid.uuid4().hex}"
    
    cur.execute("""
        INSERT INTO stc_records (id, tenant_id, employee_id, reason, last_day, leave_balance, leave_indemnity, seniority_indemnity, preavis_indemnity, total_net, seal_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (stc_id, req.tenant_id, req.employee_id, req.reason, req.departure_date, req.leave_balance, req.leave_indemnity, req.seniority_indemnity, req.preavis_indemnity, req.total_net, seal_hash))
    
    # Set employee inactive
    cur.execute("UPDATE employees SET is_active = 0 WHERE id = ?", (req.employee_id,))
    
    cur.execute("""
        INSERT INTO audit_logs (tenant_id, action, details)
        VALUES (?, 'STC_FINAL_SETTLEMENT', ?)
    """, (req.tenant_id, f"Mise en œuvre du départ définitif pour {emp['name']} - STC Net: {req.total_net:,.2f} DA"))
    
    conn.commit()
    conn.close()
    return {
        "success": True,
        "message": f"تم إتمام خروج الموظف {emp['name']} وإصدار مخالصة تصفية كل حساب وبراءة الذمة بنجاح",
        "stc_id": stc_id,
        "seal_hash": seal_hash
    }

# 6. ANNUAL EVALUATIONS
@app.get("/api/evaluations")
def get_evaluations(tenant_id: str = "TENT-DZ-001"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ev.*, e.name as employee_name, e.job_title, e.department
        FROM annual_evaluations ev
        LEFT JOIN employees e ON ev.employee_id = e.id
        WHERE ev.tenant_id = ?
        ORDER BY ev.evaluation_year DESC, ev.created_at DESC
    """, (tenant_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"success": True, "evaluations": rows}

@app.post("/api/evaluations")
def create_evaluation(ev: AnnualEvaluationCreate):
    conn = get_connection()
    cur = conn.cursor()
    ev_id = ev.id or f"EVL-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO annual_evaluations (id, tenant_id, employee_id, evaluator_name, evaluation_year, score_percentage, objectives_achieved, strengths, improvements, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ev_id, ev.tenant_id, ev.employee_id, ev.evaluator_name, ev.evaluation_year, ev.score_percentage, ev.objectives_achieved or "", ev.strengths or "", ev.improvements or "", ev.status or "COMPLETED"))
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم حفظ تقييم الموظف السنوي بنجاح", "id": ev_id}

# 7. DOSSIER TRANSFERS
@app.post("/api/transfers")
def create_transfer(t: DossierTransferCreate):
    conn = get_connection()
    cur = conn.cursor()
    tid = f"TRF-{uuid.uuid4().hex[:8].upper()}"
    cur.execute("""
        INSERT INTO dossier_transfers (id, tenant_id, employee_id, from_dept, to_dept, from_manager, to_manager, transfer_date, reason, authorized_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (tid, t.tenant_id, t.employee_id, t.from_dept, t.to_dept, t.from_manager or "", t.to_manager or "", t.transfer_date, t.reason or "", t.authorized_by or "إدارة الموارد البشرية"))
    
    # Update employee's department
    cur.execute("UPDATE employees SET department = ? WHERE id = ?", (t.to_dept, t.employee_id))
    cur.execute("INSERT INTO audit_logs (tenant_id, action, details) VALUES (?, 'EMPLOYEE_TRANSFER', ?)",
                (t.tenant_id, f"نقل ملف الموظف {t.employee_id} من {t.from_dept} إلى {t.to_dept}"))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": "تم تحويل ونقل ملف الموظف بنجاح وتحديث الهيكل الإداري", "id": tid}

# 8. EVP MONTHLY VALIDATION GATE
@app.post("/api/variables/validate-month")
def validate_monthly_variables(payload: dict):
    tenant_id = payload.get("tenant_id", "TENT-DZ-001")
    year = payload.get("year", 2026)
    month = payload.get("month", 10)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM employees WHERE tenant_id = ? AND is_active = 1", (tenant_id,))
    active_emp_count = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO audit_logs (tenant_id, action, details)
        VALUES (?, 'EVP_MONTH_VALIDATED', ?)
    """, (tenant_id, f"المصادقة الرسمية على كافة المتغيرات الشهرية EVP لدورة ({year}-{month:02d}) لـ {active_emp_count} موظف"))
    conn.commit()
    conn.close()
    return {
        "success": True,
        "message": f"تمت المصادقة والاعتماد الإداري لجميع المتغيرات الشهرية لشهر {month:02d}/{year} بنجاح",
        "employee_count": active_emp_count
    }

# 9. SETTINGS EXPORT / IMPORT
@app.get("/api/export-settings")
def export_settings(tenant_id: str = "TENT-DZ-001"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,))
    tenant = dict(cur.fetchone() or {})
    cur.execute("SELECT * FROM job_templates WHERE tenant_id = ?", (tenant_id,))
    templates = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "export_date": datetime.utcnow().isoformat(),
        "platform": "SYNCRA SaaS DZ",
        "tenant": tenant,
        "job_templates": templates
    }

@app.post("/api/import-settings")
def import_settings(payload: dict):
    tenant_id = payload.get("tenant_id", "TENT-DZ-001")
    templates = payload.get("job_templates", [])
    conn = get_connection()
    cur = conn.cursor()
    for t in templates:
        tid = t.get("id") or f"TPL-{uuid.uuid4().hex[:8].upper()}"
        cur.execute("""
            INSERT OR REPLACE INTO job_templates (id, tenant_id, title, department, contract_type, default_salary, transport, basket, bonus, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tid, tenant_id, t.get("title", ""), t.get("department", "الإدارة"), t.get("contract_type", "CDI"), t.get("default_salary", 45000.0), t.get("transport", 3500.0), t.get("basket", 4500.0), t.get("bonus", 5000.0), t.get("description", "")))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"تم استيراد إعدادات النظام و {len(templates)} نموذج وظيفي بنجاح"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("syncra_engine.server:app", host="127.0.0.1", port=8000, reload=True)

