-- =====================================================================
-- MIZAN (ميزان) - Core Database Schema
-- Platform: Supabase / PostgreSQL (Self-hostable on VPS)
-- Compliance: Algerian Data Sovereignty (Loi 18-07 / Loi 25-11)
-- =====================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "vector";         -- For Legal RAG Vector Search (pgvector)

-- 2. Enumerated Types (Enums)
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('ADMIN', 'HR', 'ACCOUNTANT', 'EMPLOYEE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE payroll_status AS ENUM ('DRAFT', 'VALIDATED', 'PAID', 'CANCELLED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE rubric_type AS ENUM ('GAIN', 'RETENUE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE ocr_status AS ENUM ('PENDING_REVIEW', 'APPROVED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =====================================================================
-- 3. Core Enterprise & Multi-Tenancy Tables
-- =====================================================================

-- Tenants (الشركات / المؤسسات)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    trade_register_number VARCHAR(100), -- السجل التجاري (RC)
    nif VARCHAR(50),                     -- رقم التعريف الجبائي (NIF)
    nis VARCHAR(50),                     -- رقم التعريف الإحصائي (NIS)
    cnas_employer_number VARCHAR(50),    -- رقم الانخراط في الضمان الاجتماعي
    address TEXT,
    commune VARCHAR(100),
    wilaya VARCHAR(100),
    postal_code VARCHAR(10),
    bank_name VARCHAR(100),
    bank_rib VARCHAR(30),                -- الحساب البنكي ومفتاح التحقق
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Application Users (مستخدمو المنصة وربطهم بالأدوار والشركات)
CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY, -- References auth.users(id) in Supabase
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'EMPLOYEE',
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Employees (الموظفون)
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    matricule VARCHAR(50) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    first_name_ar VARCHAR(100),
    last_name_ar VARCHAR(100),
    nss VARCHAR(30),                     -- رقم الضمان الاجتماعي (NSS)
    birth_date DATE NOT NULL,
    hiring_date DATE NOT NULL,
    termination_date DATE,
    department VARCHAR(100),
    job_title VARCHAR(150),
    contract_type VARCHAR(20) DEFAULT 'CDI' NOT NULL, -- CDI, CDD, etc.
    base_salary NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    family_status VARCHAR(20) DEFAULT 'SINGLE',       -- SINGLE, MARRIED, DIVORCED, WIDOWED
    children_count INT DEFAULT 0,
    bank_rib VARCHAR(30),
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL,
    UNIQUE (tenant_id, matricule)
);

-- =====================================================================
-- 4. Payroll Engine Tables (محرك حساب الرواتب)
-- =====================================================================

-- Payroll Rubrics (عناصر الراتب: المنح، التعويضات والاقتطاعات)
CREATE TABLE IF NOT EXISTS payroll_rubrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE, -- NULL means global system rubric
    code VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    type rubric_type NOT NULL,
    is_cotisable_cnas BOOLEAN DEFAULT true NOT NULL, -- خاضع للضمان الاجتماعي
    is_taxable_irg BOOLEAN DEFAULT true NOT NULL,     -- خاضع للضريبة على الدخل
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Payroll Runs (دورات وحملات معالجة الرواتب الشهرية)
CREATE TABLE IF NOT EXISTS payroll_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    year INT NOT NULL CHECK (year >= 2020),
    status payroll_status NOT NULL DEFAULT 'DRAFT',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_brut NUMERIC(15, 2) DEFAULT 0.00,
    total_cnas_employee NUMERIC(15, 2) DEFAULT 0.00,
    total_cnas_employer NUMERIC(15, 2) DEFAULT 0.00,
    total_irg NUMERIC(15, 2) DEFAULT 0.00,
    total_net NUMERIC(15, 2) DEFAULT 0.00,
    created_by UUID REFERENCES app_users(id),
    validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL,
    UNIQUE (tenant_id, month, year)
);

-- Payslips (كشوف الرواتب الفردية)
CREATE TABLE IF NOT EXISTS payslips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    payroll_run_id UUID NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    base_salary NUMERIC(12, 2) NOT NULL,
    brut_salary NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cnas_employee NUMERIC(12, 2) NOT NULL DEFAULT 0.00,  -- 9% حصة الأجير
    cnas_employer NUMERIC(12, 2) NOT NULL DEFAULT 0.00,  -- 26% حصة صاحب العمل
    taxable_irg NUMERIC(12, 2) NOT NULL DEFAULT 0.00,    -- وعاء الضريبة IRG
    irg_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,     -- مبلغ الضريبة المستقطع
    net_salary NUMERIC(12, 2) NOT NULL DEFAULT 0.00,     -- الصافي للدفع
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Payslip Lines (أسطر كشف الراتب بالتفصيل)
CREATE TABLE IF NOT EXISTS payslip_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payslip_id UUID NOT NULL REFERENCES payslips(id) ON DELETE CASCADE,
    rubric_id UUID REFERENCES payroll_rubrics(id),
    code VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    type rubric_type NOT NULL,
    base_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    rate NUMERIC(6, 3),                                 -- النسبة المئوية إن وجدت
    amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Solde de Tout Compte (STC - تسوية نهاية الخدمة)
CREATE TABLE IF NOT EXISTS final_settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE RESTRICT,
    termination_date DATE NOT NULL,
    notice_period_compensation NUMERIC(12, 2) DEFAULT 0.00, -- تعويض مهلة الإخطار
    paid_leave_compensation NUMERIC(12, 2) DEFAULT 0.00,    -- تعويض العطل غير المستهلكة
    severance_pay NUMERIC(12, 2) DEFAULT 0.00,              -- تعويض التسريح (معفى صراحة من وعاء IRG)
    total_stc_net NUMERIC(12, 2) NOT NULL,
    calculation_breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- =====================================================================
-- 5. Algerian Legal Reference Tables (الجداول القانونية المرجعية)
-- =====================================================================

-- Legal Rates (النسب القانونية الرسمية مع إدارة الإصدارات)
CREATE TABLE IF NOT EXISTS legal_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(255) NOT NULL,
    rate_percent NUMERIC(5, 2) NOT NULL,
    payer VARCHAR(20) NOT NULL, -- 'EMPLOYEE', 'EMPLOYER', 'SELF_EMPLOYED'
    effective_from DATE NOT NULL,
    effective_to DATE,
    legal_source TEXT
);

-- IRG Brackets (جدول شرائح الضريبة على الدخل الإجمالي)
CREATE TABLE IF NOT EXISTS irg_brackets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    min_amount NUMERIC(12, 2) NOT NULL,
    max_amount NUMERIC(12, 2), -- NULL for the open upper bracket
    rate_percent NUMERIC(5, 2) NOT NULL,
    fixed_deduction NUMERIC(12, 2) DEFAULT 0.00,
    effective_from DATE NOT NULL,
    effective_to DATE,
    legal_source TEXT
);

-- IRG Exemption & Abatement Rules (قواعد الإعفاء والتخفيض لـ IRG)
CREATE TABLE IF NOT EXISTS irg_abatement_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    min_taxable NUMERIC(12, 2) NOT NULL,
    max_taxable NUMERIC(12, 2) NOT NULL,
    abatement_percent NUMERIC(5, 2) DEFAULT 40.00,
    min_abatement NUMERIC(12, 2) DEFAULT 1000.00,
    max_abatement NUMERIC(12, 2) DEFAULT 1500.00,
    effective_from DATE NOT NULL,
    effective_to DATE
);

-- =====================================================================
-- 6. AI & RAG Subsystem Tables (نظام المساعد القانوني والـ OCR)
-- =====================================================================

-- Legal Source Documents (الجرائد الرسمية والنصوص التشريعية)
CREATE TABLE IF NOT EXISTS legal_source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    official_journal_number VARCHAR(50), -- رقم الجريدة الرسمية (JORA)
    publication_date DATE,
    document_type VARCHAR(50),          -- 'CODE_TRAVAIL', 'DECRET', 'LOI', 'ARRETE'
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Legal Chunks with Vector Embeddings (المقاطع القانونية للبحث الدلالي RAG)
CREATE TABLE IF NOT EXISTS legal_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES legal_source_documents(id) ON DELETE CASCADE,
    article_number VARCHAR(50),         -- رقم المادة القانونية (مثل المادة 80 مكرر)
    content TEXT NOT NULL,              -- نص المادة
    embedding vector(1024),             -- المتجه الدلالي BGE-M3 (أو 1536 حسب النموذج)
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- OCR Extraction Jobs (استخراج بيانات الإجازات الطبية والمصاريف)
CREATE TABLE IF NOT EXISTS ocr_extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_id UUID REFERENCES employees(id),
    file_path TEXT NOT NULL,
    status ocr_status DEFAULT 'PENDING_REVIEW' NOT NULL,
    extracted_data JSONB,
    reviewed_by UUID REFERENCES app_users(id),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- Payroll Anomalies (كشف الشذوذ الحسابي والإحصائي)
CREATE TABLE IF NOT EXISTS payroll_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    payroll_run_id UUID NOT NULL REFERENCES payroll_runs(id) ON DELETE CASCADE,
    employee_id UUID NOT NULL REFERENCES employees(id),
    rule_code VARCHAR(50) NOT NULL,     -- e.g., 'NET_DIFF_OVER_30', 'ZERO_CNAS'
    severity VARCHAR(20) DEFAULT 'WARNING',
    description TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT false NOT NULL,
    resolved_by UUID REFERENCES app_users(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT timezone('utc', now()) NOT NULL
);

-- =====================================================================
-- 7. Row Level Security (RLS) - حماية وعزل البيانات لكل شركة
-- =====================================================================

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE payslips ENABLE ROW LEVEL SECURITY;
ALTER TABLE payslip_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_extraction_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_anomalies ENABLE ROW LEVEL SECURITY;

-- Base Tenant Isolation Policy (Only access data of the user's tenant)
CREATE POLICY tenant_isolation_employees ON employees
    FOR ALL USING (
        tenant_id = (SELECT tenant_id FROM app_users WHERE id = auth.uid())
    );

CREATE POLICY tenant_isolation_payroll_runs ON payroll_runs
    FOR ALL USING (
        tenant_id = (SELECT tenant_id FROM app_users WHERE id = auth.uid())
    );

CREATE POLICY tenant_isolation_payslips ON payslips
    FOR ALL USING (
        tenant_id = (SELECT tenant_id FROM app_users WHERE id = auth.uid())
    );
