import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "syncra_saas.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 10000;")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Tenants (المؤسسات المستأجرة)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        legal_form TEXT DEFAULT 'SARL',
        rc TEXT DEFAULT '',
        nif TEXT DEFAULT '',
        nis TEXT DEFAULT '',
        cnas_adherent TEXT DEFAULT '',
        address TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Users (المستخدمون)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        username TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT DEFAULT 'ADMIN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )
    """)

    # Employees (العمال)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        nss TEXT NOT NULL,
        job_title TEXT NOT NULL,
        department TEXT DEFAULT 'الإدارة',
        contract_type TEXT DEFAULT 'CDI',
        hire_date TEXT DEFAULT '2023-01-01',
        base_salary REAL NOT NULL DEFAULT 40000.0,
        seniority_allowance REAL DEFAULT 0.0,
        bonus REAL DEFAULT 0.0,
        transport_allowance REAL DEFAULT 3000.0,
        basket_allowance REAL DEFAULT 4000.0,
        mission_expense REAL DEFAULT 0.0,
        deduction_absence REAL DEFAULT 0.0,
        leave_balance REAL DEFAULT 30.0,
        bank_name TEXT DEFAULT 'BEA',
        rib TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )
    """)

    # Payroll Cycles (دورات الأجور والأختام المشفرة Bitemporal)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payroll_cycles (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        month INTEGER NOT NULL,
        year INTEGER NOT NULL,
        status TEXT DEFAULT 'SAISIE',
        manifest_hash TEXT,
        total_brut REAL DEFAULT 0.0,
        total_cnas_sal REAL DEFAULT 0.0,
        total_cnas_pat REAL DEFAULT 0.0,
        total_irg REAL DEFAULT 0.0,
        total_net REAL DEFAULT 0.0,
        closed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )
    """)

    # STC Final Settlement Records (مخالصات تصفية كل حساب وبراءة الذمة)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stc_records (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        reason TEXT,
        last_day TEXT,
        leave_balance REAL DEFAULT 0.0,
        leave_indemnity REAL DEFAULT 0.0,
        seniority_indemnity REAL DEFAULT 0.0,
        preavis_indemnity REAL DEFAULT 0.0,
        total_net REAL DEFAULT 0.0,
        seal_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # Medical Leaves (العطل المرضية والشواهد الطبية معالجة بـ OCR)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medical_leaves (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT,
        filename TEXT NOT NULL,
        nss_detected TEXT,
        doctor_name TEXT,
        start_date TEXT,
        duration_days INTEGER DEFAULT 0,
        end_date TEXT,
        motif TEXT DEFAULT 'عطلة مرضية عادية',
        raw_text TEXT,
        deduction_amount REAL DEFAULT 0.0,
        cnas_covered INTEGER DEFAULT 0,
        status TEXT DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # Audit Logs (سجلات التدقيق الأمني والعمليات)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tenant_id TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )
    """)

    # Per-employee / per-month payroll status (Silae BPA matrix)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_period_status (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        status TEXT DEFAULT 'SAISIE',
        gross REAL,
        cnas_employee REAL,
        irg REAL,
        net REAL,
        calculated_at TIMESTAMP,
        closed_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tenant_id, employee_id, year, month),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )
    """)

    # Per-employee / per-month variable payroll elements (EVP - Éléments Variables de Paie)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_monthly_variables (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        heures_supp_50 REAL DEFAULT 0.0,
        heures_supp_100 REAL DEFAULT 0.0,
        absence_days REAL DEFAULT 0.0,
        prime_rendement REAL DEFAULT 0.0,
        bonus REAL DEFAULT 0.0,
        transport_allowance REAL DEFAULT 0.0,
        basket_allowance REAL DEFAULT 0.0,
        mission_expense REAL DEFAULT 0.0,
        acompte REAL DEFAULT 0.0,
        note TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tenant_id, employee_id, year, month),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # Legal Corpus (المتن القانوني والتشريعي للذكاء الاصطناعي RAG)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS legal_articles (
        id TEXT PRIMARY KEY,
        law_code TEXT NOT NULL,
        article_num TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        official_text_ar TEXT NOT NULL,
        official_text_fr TEXT NOT NULL,
        practical_implication TEXT NOT NULL,
        keywords TEXT NOT NULL
    )
    """)

    # Seed Default Tenant if empty
    cursor.execute("SELECT COUNT(*) FROM tenants")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO tenants (id, name, legal_form, rc, nif, nis, cnas_adherent, address, phone, email)
        VALUES (
            'TENT-DZ-001',
            'مؤسسة النور للخدمات والتقنية',
            'SARL',
            '16/00-0987654B22',
            '002216098765432',
            '002216010012345',
            '9876543210',
            'حي الأعمال، باب الزوار، الجزائر العاصمة',
            '023 85 41 20',
            'contact@el-nour-dz.com'
        )
        """)

        # Seed Employees
        employees = [
            ('EMP-001', 'TENT-DZ-001', 'أحمد بن علي', '189169900124', 'مهندس برمجيات رئيسي', 'تطوير البرمجيات', 'CDI', '2021-03-15', 85000.0, 5000.0, 6000.0),
            ('EMP-002', 'TENT-DZ-001', 'سميرة قدور', '292168800452', 'مسؤولة الموارد البشرية', 'الموارد البشرية', 'CDI', '2020-09-01', 65000.0, 4000.0, 5000.0),
            ('EMP-003', 'TENT-DZ-001', 'كريم مزيان', '195167700789', 'محاسب أجور وتسيير', 'المالية والمحاسبة', 'CDI', '2022-01-10', 58000.0, 4000.0, 5000.0),
            ('EMP-004', 'TENT-DZ-001', 'فاطمة الزهراء رحماني', '297166600321', 'أخصائية تسويق رقمي', 'التسويق', 'CDD', '2023-06-01', 48000.0, 3500.0, 4500.0),
            ('EMP-005', 'TENT-DZ-001', 'ياسين بلحاج', '198165500987', 'تقني دعم شبكات', 'الدعم الفني', 'ANEM_CTA', '2023-11-15', 38000.0, 3000.0, 4000.0),
        ]
        cursor.executemany("""
        INSERT INTO employees (id, tenant_id, name, nss, job_title, department, contract_type, hire_date, base_salary, transport_allowance, basket_allowance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, employees)

    # Seed Legal Corpus
    seed_legal_corpus(cursor)

    conn.commit()
    conn.close()

    migrate_db()

def migrate_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_monthly_variables (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        heures_supp_50 REAL DEFAULT 0.0,
        heures_supp_100 REAL DEFAULT 0.0,
        absence_days REAL DEFAULT 0.0,
        prime_rendement REAL DEFAULT 0.0,
        bonus REAL DEFAULT 0.0,
        transport_allowance REAL DEFAULT 0.0,
        basket_allowance REAL DEFAULT 0.0,
        mission_expense REAL DEFAULT 0.0,
        acompte REAL DEFAULT 0.0,
        note TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tenant_id, employee_id, year, month),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)
    cursor.execute("PRAGMA table_info(employees)")
    columns = [row[1] for row in cursor.fetchall()]
    new_cols = [
        ("seniority_allowance", "REAL DEFAULT 0.0"),
        ("bonus", "REAL DEFAULT 0.0"),
        ("mission_expense", "REAL DEFAULT 0.0"),
        ("deduction_absence", "REAL DEFAULT 0.0"),
        ("leave_balance", "REAL DEFAULT 30.0"),
        ("bank_name", "TEXT DEFAULT 'BEA'"),
        ("rib", "TEXT DEFAULT ''"),
    ]
    for col_name, col_type in new_cols:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")

    # Ensure sample employees have rich data
    cursor.execute("UPDATE employees SET seniority_allowance = 5000.0, bonus = 6000.0, bank_name = 'BEA', rib = '002 00012 0123456789 45' WHERE id = 'EMP-001' AND (rib IS NULL OR rib = '')")
    cursor.execute("UPDATE employees SET seniority_allowance = 4000.0, bonus = 5000.0, bank_name = 'BNA', rib = '001 00045 0987654321 23' WHERE id = 'EMP-002' AND (rib IS NULL OR rib = '')")
    cursor.execute("UPDATE employees SET seniority_allowance = 3000.0, bonus = 4000.0, bank_name = 'CPA', rib = '004 00078 0456123789 67' WHERE id = 'EMP-003' AND (rib IS NULL OR rib = '')")
    cursor.execute("UPDATE employees SET seniority_allowance = 2000.0, bonus = 3000.0, bank_name = 'BDL', rib = '005 00023 0789456123 89' WHERE id = 'EMP-004' AND (rib IS NULL OR rib = '')")
    cursor.execute("UPDATE employees SET seniority_allowance = 1000.0, bonus = 2000.0, bank_name = 'BADR', rib = '003 00089 0159753486 12' WHERE id = 'EMP-005' AND (rib IS NULL OR rib = '')")

    # Seed Tenant 2 (Company B) for Real Multi-Tenant SaaS Isolation demonstration
    cursor.execute("SELECT COUNT(*) FROM tenants WHERE id = 'TENT-DZ-002'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO tenants (id, name, legal_form, rc, nif, nis, cnas_adherent, address, phone, email)
        VALUES (
            'TENT-DZ-002',
            'شركة الأطلس للصناعات والحلول الرقمية',
            'SPA',
            '16/00-1122334A23',
            '002316112233445',
            '002316020054321',
            '8765432109',
            'المنطقة الصناعية، الرويبة، الجزائر العاصمة',
            '023 88 12 34',
            'contact@atlas-solutions-dz.com'
        )
        """)

        tenant2_employees = [
            ('EMP-006', 'TENT-DZ-002', 'أسماء بلقاسم', '294165500112', 'مديرة التدقيق والجودة', 'إدارة الجودة', 'CDI', '2022-04-01', 92000.0, 6000.0, 7000.0, 4000.0, 5000.0, 'BEA', '002 00088 0123456789 99'),
            ('EMP-007', 'TENT-DZ-002', 'عمر حيدوسي', '188164400778', 'مدير المبيعات والتسويق', 'التجارة والتسويق', 'CDI', '2021-08-15', 78000.0, 5000.0, 6000.0, 3500.0, 4500.0, 'BNA', '001 00099 0987654321 77'),
            ('EMP-008', 'TENT-DZ-002', 'خالد زروقي', '196163300991', 'مهندس صيانة صناعية', 'الإنتاج والصيانة', 'CDD', '2023-09-01', 52000.0, 2000.0, 3000.0, 3000.0, 4000.0, 'CPA', '004 00033 0456123789 55')
        ]
        cursor.executemany("""
        INSERT INTO employees (id, tenant_id, name, nss, job_title, department, contract_type, hire_date, base_salary, seniority_allowance, bonus, transport_allowance, basket_allowance, bank_name, rib)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tenant2_employees)

    # -------------------------------------------------------------
    # NEW CLIENT MODULES: TABLES & SCHEMAS (syncra_md_files_1)
    # -------------------------------------------------------------
    # 1. Absences & Leave Management (سجل الغيابات والإجازات ومسار الاعتماد)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS absences (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        days_count REAL NOT NULL DEFAULT 1.0,
        reason TEXT DEFAULT '',
        document_url TEXT DEFAULT '',
        status TEXT DEFAULT 'PENDING',
        approved_by TEXT DEFAULT '',
        approved_at TIMESTAMP,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # 2. Hours & Overtime Entry (ساعات العمل العادية والإضافية)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_hours (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        regular_hours REAL DEFAULT 173.33,
        hs_50 REAL DEFAULT 0.0,
        hs_100 REAL DEFAULT 0.0,
        night_hours REAL DEFAULT 0.0,
        holiday_hours REAL DEFAULT 0.0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(tenant_id, employee_id, year, month),
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # 3. Occupational Medical Visits (طب العمل ومتابعة الفحوصات الطبية)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medical_visits (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        visit_type TEXT NOT NULL,
        scheduled_date TEXT NOT NULL,
        completed_date TEXT DEFAULT '',
        doctor_name TEXT DEFAULT '',
        medical_center TEXT DEFAULT '',
        fitness_status TEXT DEFAULT 'APTE',
        next_visit_date TEXT DEFAULT '',
        status TEXT DEFAULT 'SCHEDULED',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # 4. Job Templates (قوالب الوظائف الجاهزة للتوظيف السريع)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_templates (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        title TEXT NOT NULL,
        department TEXT DEFAULT 'الإدارة العامة',
        contract_type TEXT DEFAULT 'CDI',
        default_salary REAL DEFAULT 45000.0,
        transport REAL DEFAULT 3500.0,
        basket REAL DEFAULT 4500.0,
        bonus REAL DEFAULT 5000.0,
        description TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id)
    )
    """)

    # 5. Annual Evaluations (المقابلات والتقييمات السنوية)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS annual_evaluations (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        evaluator_name TEXT NOT NULL,
        evaluation_year INTEGER NOT NULL,
        score_percentage INTEGER DEFAULT 85,
        objectives_achieved TEXT DEFAULT '',
        strengths TEXT DEFAULT '',
        improvements TEXT DEFAULT '',
        status TEXT DEFAULT 'COMPLETED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)

    # 6. Dossier Transfers (سجل حركات ونقل الموظفين بين الأقسام والفروع)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dossier_transfers (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        from_dept TEXT NOT NULL,
        to_dept TEXT NOT NULL,
        from_manager TEXT DEFAULT '',
        to_manager TEXT DEFAULT '',
        transfer_date TEXT NOT NULL,
        reason TEXT DEFAULT '',
        authorized_by TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)



    conn.commit()
    conn.close()

def seed_legal_corpus(cursor):
    cursor.execute("SELECT COUNT(*) FROM legal_articles")
    if cursor.fetchone()[0] > 0:
        return

    articles = [
        (
            'LEG-9011-08',
            'Loi 90-11',
            'المادة 8',
            'عقد العمل غير محدد المدة (CDI)',
            'عقود العمل',
            'يُبرم عقد العمل لمدة غير محددة كأصل عام في تشريع العمل الجزائري. ولا يمكن إبرامه لمدة محددة إلا في الحالات المنصوص عليها صراحة في المادة 12 من هذا القانون.',
            'Le contrat de travail est conclu pour une durée indéterminée. Il ne peut être conclu pour une durée déterminée que dans les cas expressément prévus à l\'article 12.',
            'جميع عقود العمل تعتبر عقوداً دائمة CDI ما لم يثبت صاحب العمل توفر أحد شروط المادة 12، وإلا يُعاد تكييف العقد تلقائياً أمام مفتشية العمل والقضاء.',
            'عقد عمل, CDI, عقد غير محدد المدة, توظيف, إبرام العقد'
        ),
        (
            'LEG-9011-12',
            'Loi 90-11',
            'المادة 12',
            'الحالات الاستثنائية لعقد العمل محدد المدة (CDD)',
            'عقود العمل',
            'يمكن إبرام عقد العمل لمدّة محدودة بالتوقيت الكامل أو الجزئي في الحالات التالية حصراً: 1- عندما يُوظف العامل لتنفيذ عمل مرتبط بعقود أشغال أو خدمات غير متجددة، 2- استخلاف عامل مثبت تغيّب مؤقتاً، 3- عند تزايد العمل الموسمي أو المؤقت، 4- في النشاطات ذات الطابع المؤقت.',
            'Le contrat de travail peut être conclu pour une durée déterminée dans les cas suivants: 1. Réalisation d\'un ouvrage ou prestation non renouvelable, 2. Remplacement d\'un travailleur temporairement absent, 3. Surcroît extraordinaire de travail, 4. Activités à caractère saisonnier.',
            'يُشترط بيان سبب التحديد بدقة وتاريخ نهايته، وإلا يُعتبر باطلاً ويتحول لعقد دائم CDI.',
            'CDD, عقد محدد المدة, استخلاف, أشغال موسمية, استثناء'
        ),
        (
            'LEG-9011-18',
            'Loi 90-11',
            'المادتان 18 و19',
            'فترة التجربة وإنهاؤها',
            'فترة التجربة',
            'لا يمكن أن تتجاوز فترة التجربة ستة (6) أشهر كحد أقصى، ويمكن رفعها إلى اثني عشر (12) شهراً لمناصب العمل ذات التأهيل العالي. يجوز لأي من الطرفين إنهاء علاقة العمل خلال فترة التجربة دون إشعار مسبق ودون تعويض.',
            'La période d\'essai ne peut excéder six (6) mois. Elle peut être portée à douze (12) mois pour les postes de haute qualification. Durant cette période, la relation de travail peut être résiliée à tout moment sans préavis ni indemnité.',
            'لا يستحق العامل تعويض إنهاء الخدمة أو مهلة إخطار عند إنهاء العقد أثناء فترة التجربة، ويُكتفى بدفع أجر الأيام الفعلية المنجزة ومستحقات العطلة السنوية المكتسبة.',
            'فترة التجربة, اختبار, إنهاء التجربة, إخطار مسبق, تعويض'
        ),
        (
            'LEG-9011-31',
            'Loi 90-11',
            'المادة 31',
            'المدة القانونية الأسبوعية للعمل',
            'ساعات العمل',
            'تحدد المدة القانونية للعمل بأربعين (40) ساعة في الأسبوع في ظروف العمل العادية، وتوزع على خمسة (5) أيام عمل على الأقل. ويُعتبر كل وقت عمل يُنجز بعد هذا الحساب ساعات إضافية تخضع للتعويض القانوني.',
            'La durée légale de travail est fixée à quarante (40) heures par semaine dans les conditions normales de travail, réparties sur au moins cinq (5) jours ouvrables.',
            'المعدل المعياري للأجر الساعي يحسب على أساس 173.33 ساعة شهرياً (40 ساعة × 52 أسبوعاً ÷ 12 شهراً).',
            'ساعات العمل, 40 ساعة, المدة القانونية, الأسبوع, 173.33'
        ),
        (
            'LEG-9011-32',
            'Loi 90-11',
            'المادة 32',
            'الساعات الإضافية ونسب الزيادة الإلزامية',
            'ساعات العمل',
            'لا يجوز اللجوء إلى الساعات الإضافية إلا استثناء وبحد أقصى لا يتجاوز 20% من المدة القانونية (أي 8 ساعات أسبوعياً). وتمنح الساعات الإضافية الحق في زيادة في الأجر لا تقل بأي حال عن 50% من الأجر الساعي العادي.',
            'Le recours aux heures supplémentaires ne doit pas dépasser 20% de la durée légale. Elles donnent droit à une majoration d\'au moins 50% du salaire horaire normal.',
            'حساب الساعات الإضافية: أجر الساعة الإضافية = (الراتب الأساسي ÷ 173.33) × 1.50 كحد أدنى. أي تجاوز لـ 20% يعرض المؤسسة لمخالفة من مفتشية العمل.',
            'ساعات إضافية, زيادة 50%, العمل الإضافي, تضخيم الأجر, 20%'
        ),
        (
            'LEG-9011-39',
            'Loi 90-11',
            'المواد 39 إلى 44',
            'العطلة السنوية المدفوعة الأجر وقواعد حسابها',
            'العطل والغيابات',
            'لكل عامل الحق في عطلة سنوية مدفوعة الأجر يمنحها إياه المستخدم بمعدل يومين ونصف (2.5) يوم في الشهر من العمل الفعلي دون أن تتجاوز المدة الإجمالية ثلاثين (30) يوماً تقويمياً عن سنة العمل الواحدة (من 1 جويلية إلى 30 جوان). تحسب منحة العطلة إما على أساس قاعدة 1/12 من مجموع الأجور المحصلة أو الأجر المعتاد أيهما أكثر فائدة للعامل.',
            'Le travailleur a droit à un congé annuel payé à raison de 2.5 jours par mois de travail effectif sans excéder 30 jours calendaires par an. L\'indemnité de congé est calculée au 1/12ème des rémunérations ou maintien du salaire.',
            'يستحق العامل 30 يوماً بعد إتمام 12 شهراً. رصيد العطلة غير المستهلكة عند مغادرة المؤسسة يُصرف إلزامياً ضمن مخالصة الرصيد النهائي (STC) كتعويض مالي.',
            'عطلة سنوية, 30 يوم, 2.5 يوم شهريا, بدل عطلة, 1/12'
        ),
        (
            'LEG-9011-73',
            'Loi 90-11',
            'المادة 73',
            'الخطأ الجسيم والتسريح التأديبي بدون تعويض',
            'إنهاء الخدمة',
            'يتم التسريح التأديبي دون مهلة إشعار ودون تعويض في حالة ارتكاب العامل خطأ جسيماً، ولا سيما: 1- رفض تنفيذ التعليمات المرتبطة بالتزاماته المهنية دون عذر مشروع، 2- إفشاء أسرار مهنية، 3- تعاطي الكحول أو المخدرات في مكان العمل، 4- ارتكاب أعمال عنف، 5- سرقة أو إتلاف ممتلكات المؤسسة عمداً.',
            'Le licenciement pour faute grave intervient sans préavis ni indemnité en cas de refus d\'exécution, divulgation de secrets, état d\'ébriété, violences ou vol au sein de l\'organisme employeur.',
            'في حال ارتكاب خطأ جسيم مثبت بالمسطرة التأديبية المنصوص عليها في المادتين 73-1 و73-2، يُحرم العامل من تعويض التسريح والإخطار المسبق، ولا يُصرف له إلا مستحقات العطلة غير المستهلكة وأيام العمل المنجزة في STC.',
            'خطأ جسيم, تسريح تأديبي, مادة 73, طرد, بدون تعويض, سرقة, عنف'
        ),
        (
            'LEG-9011-86',
            'Loi 90-11',
            'المادة 86',
            'مخالصة الحساب النهائي (STC) وبراءة الذمة',
            'الأجور ومخالصة الرصيد',
            'عند انتهاء علاقة العمل لأي سبب كان، يُسلم للمستخدم وصل تصفية كل حساب (Reçu pour solde de tout compte). ويحق للعامل الطعن في المبالغ المبيّنة فيه خلال مدة قانونية. يتضمن الوصل تفصيلاً دقيقاً لكافة مستحقات العامل: راتب الأيام الأخيرة، تعويض العطل غير المستهلكة، ومكافأة نهاية الخدمة إن وجدت.',
            'A l\'expiration de la relation de travail, l\'employeur délivre un reçu pour solde de tout compte détaillant l\'ensemble des sommes dues au titre des salaires, congés payés et indemnités légales ou conventionnelles.',
            'المادة 86 تلزم المؤسسة بالحساب الرياضي المدقق لكل عنصر من عناصر STC: راتب الفترة الأخيرة + تعويض الأقدمية (إن وجد) + تعويض العطل السنوية المكتسبة، مخصوماً منها اشتراك CNAS والضريبة IRG.',
            'STC, مخالصة, رصيد الحساب, مادة 86, براءة ذمة, نهاية الخدمة'
        ),
        (
            'LEG-8311-14',
            'Loi 83-11',
            'المواد 14 إلى 24',
            'التأمين عن المرض والتعويضات اليومية (CNAS)',
            'الضمان الاجتماعي',
            'يستفيد المؤمن له اجتماعياً من تعويضات يومية عن العطلة المرضية المبررة قانوناً: تمنح بنسبة 50% من الأجر اليومي المنصب ابتداءً من اليوم الأول إلى اليوم الخامس عشر، وترتفع إلى 100% ابتداءً من اليوم السادس عشر أو في حالات الاستشفاء أو الأمراض المزمنة المعترف بها.',
            'L\'indemnité journalière de maladie est égale à 50% du salaire journalier du 1er au 15ème jour, et à 100% à partir du 16ème jour ou en cas d\'hospitalisation et affection de longue durée.',
            'المؤسسة تخصم كامل أيام الغياب المرضي من راتب العامل، بينما تتولى CNAS تعويض العامل مباشرة أو عن طريق آلية الدفع بالحلول (Tiers-payant) إذا وُجدت اتفاقية.',
            'عطلة مرضية, CNAS, ضمان اجتماعي, تعويض 50%, تعويض 100%, مرض'
        ),
        (
            'LEG-8311-17',
            'Loi 83-11',
            'المادة 17',
            'أجل إيداع الشهادة الطبية (48 ساعة)',
            'الضمان الاجتماعي',
            'يجب على العامل إرسال الإشعار بالتوقف عن العمل والشهادة الطبية إلى هيئة الضمان الاجتماعي وإلى صاحب العمل في أجل أقصاه ثمان وأربعون (48) ساعة، ما عدا في حالات القوة القاهرة المثبتة. وإلا تسقط حقوقه في التعويض اليومي من طرف الصندوق.',
            'L\'assuré doit adresser l\'avis d\'arrêt de travail à la caisse de sécurité sociale et à l\'employeur dans un délai de quarante-huit (48) heures, sauf cas de force majeure.',
            'إذا تأخر العامل في تقديم الشهادة الطبية عن 48 ساعة، يحق للمستخدم تسجيل الغياب كغياب غير مبرر (Absence irrégulière) قد يستوجب عقوبة إنذار وخصم من الراتب.',
            '48 ساعة, إشعار التوقف, أجل الشهادة, غياب غير مبرر, CNAS'
        ),
        (
            'LEG-LF2022-31',
            'Loi de Finances 2022',
            'المادتان 31 و32',
            'السلم الضريبي التدريجي للضريبة على الدخل الإجمالي (IRG 2022)',
            'الضرائب والأجور',
            'تُحسب الضريبة على الدخل الإجمالي (IRG) صنف الرواتب والأجور وفق سلم تصاعدي بعد خصم اشتراك الضمان الاجتماعي (9%): من 0 إلى 20.000 دج: معفى 0%، من 20.001 إلى 40.000 دج: 23%، من 40.001 إلى 80.000 دج: 27%، من 80.001 إلى 160.000 دج: 30%، وما فوق 160.000 دج: 35%. مع تطبيق تخفيض عام بنسبة 40% (بين 1.000 دج و1.500 دج)، وإعفاء تام للأجور الخاضعة التي لا تتجاوز 30.000 دج شهرياً.',
            'Barème progressif IRG 2022 : Tranche 0-20k (0%), 20k-40k (23%), 40k-80k (27%), 80k-160k (30%), >160k (35%). Abattement 40% (min 1000, max 1500 DA). Exonération totale pour salaires imposables <= 30.000 DA.',
            'الرواتب الإجمالية الخاضعة للضريبة الأقل من أو تساوي 30,000 دج تستفيد من إعفاء كلي 100% من IRG. والرواتب بين 30,001 و35,000 دج تستفيد من معادلة تخفيض إضافية مدرجة رسمياً بالمادة 32.',
            'IRG, ضريبة الدخل, قانون المالية 2022, سلم تدريجي, إعفاء 30000, خصم 9%'
        )
    ]

    cursor.executemany("""
    INSERT INTO legal_articles (id, law_code, article_num, title, category, official_text_ar, official_text_fr, practical_implication, keywords)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, articles)

if __name__ == "__main__":
    init_db()
    print("SYNCRA SaaS Database Initialized Successfully!")
