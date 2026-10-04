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
    emp_id = emp.id or f"EMP-{uuid.uuid4().hex[:6].upper()}"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("syncra_engine.server:app", host="127.0.0.1", port=8000, reload=True)
