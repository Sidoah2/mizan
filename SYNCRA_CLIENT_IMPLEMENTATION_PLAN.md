# خطة التنفيذ الفنية الشاملة: تحويل ملفات العميل (syncra_md_files_1) إلى نظام SaaS متكامل جاهز للإنتاج والنشر على Render

## 1. الملخص التنفيذي ونطاق العمل (Executive Summary & Scope)

أرسل العميل حزمة متكاملة من 28 ملف توثيقي (`syncra_md_files_1`) تفصل مسارات العمل والوظائف التشغيلية لنظام **SYNCRA** لإدارة الموارد البشرية والأجور وفق المعايير السحابية المؤسسية (SaaS) وبما يطابق ممارسات بيئة العمل الجزائرية (قانون العمل 90-11، الضمان الاجتماعي CNAS، والضريبة على الدخل IRG).

تنقسم وثائق العميل الـ 28 إلى **10 وحدات وظيفية متكاملة**:

| الرقم | الوحدة الوظيفية | الملفات المرجعية في `syncra_md_files_1` | نطاق التنفيذ في SYNCRA SaaS |
|---|---|---|---|
| **1** | **إدارة وتسجيل الغيابات واعتمادها** (Absence Management & Workflow) | `Syncra_ar_absences_working.md`<br>`Syncra_ar_manager_absence_approval_working.md` | - تقويم الغيابات التفاعلي<br>- تسجيل فردي وجماعي مع أسباب الغياب الرسمية<br>- مسار اعتماد المديرين (N+1 / N+2)، الاعتماد السريع، والاعتماد الجماعي<br>- معالجة طلبات الإلغاء والحذف قبل الإغلاق |
| **2** | **تسجيل واستيراد ساعات العمل** (Hours Entry & Timesheets) | `Syncra_ar_hours_entry_working.md` | - إدخال الساعات العادية وساعات العمل الإضافية (HS 50%, HS 100%)<br>- ساعات الليل وساعات الاستدعاء/العطل<br>- استيراد وتصدير الساعات عبر ملفات Excel/CSV |
| **3** | **المتغيرات الشهرية للأجر واعتمادها** (Variable Pay & EVP Validation) | `Syncra_ar_variable_pay_working.md`<br>`Syncra_ar_import_variable_data_working.md`<br>`Syncra_ar_variable_validation_working.md` | - شبكة إدخال جماعية وفردية للعلاوات والمكافآت والسلف<br>- استيراد المتغيرات من Excel مع فحص المطابقة وإلغاء الدفعة<br>- دورة المصادقة والاعتماد الشهري قبل إغلاق الدورة |
| **4** | **متابعة طب العمل والزيارات الطبية** (Occupational Medical Visits) | `Syncra_ar_medical_visits_working.md` | - سجل الزيارات الطبية (فحص التوظيف، فحص دوري، فحص استئناف العمل)<br>- تتبع الأهلية الطبية وتنبيهات انتهاء الصلاحية والتجديد<br>- ربطها مع رخص الغياب والشواهد الطبية مع OCR |
| **5** | **مساعد إنهاء الخدمة وتصفية الحساب** (Exit Wizard & Departure) | `Ge_ar_working.md`<br>`De_ar_working.md` | - معالج خروج الموظف خطوة بخطوة (استقالة، تسريح، نهاية عقد، تقاعد)<br>- حساب فترات الإخطار ورصيد العطل وحساب STC آلياً<br>- إصدار شهادة العمل، مخالصة كل حساب، وشهادة انتساب CNAS |
| **6** | **نماذج ومهام الوظائف وإعدادات الموظفين** (Staff Templates & Employee Setup) | `Cre_ar_working.md`<br>`Parame_ar_working.md`<br>`Pre_ar_working.md`<br>`FAQ_Admin_collaborateurs_ar_working.md` | - قوالب الوظائف الجاهزة (كادر، مهندس، تقني، إداري، عامل)<br>- شاشات التهيئة الموسعة لملف الموظف والبيانات العائلية والبنكية<br>- مصفوفة الصلاحيات والأدوار (Admin, HR, Manager, Employee) |
| **7** | **محرك الاستيراد والتصدير المؤسسي** (Enterprise Import/Export) | `Importer_des_informations_Salarie_ar_working.md`<br>`Importer_des_informations_Socie_ar_working.md`<br>`Importer_Exporter_des_parame_ar_working.md` | - استيراد الموظفين من ملفات Excel وتنزيل النموذج القياسي<br>- استيراد بيانات الشركات وتحديثها<br>- تصدير واستيراد إعدادات النظام ونسخها الاحتياطية |
| **8** | **نقل وتوزيع ملفات الموظفين** (Employee Dossier Transfer) | `Transfe_ar_working.md` | - نقل الموظف بين الفروع أو الأقسام أو المديرين مع سجل تتبع كامل (Audit Trail) |
| **9** | **المتغيرات الديناميكية والمقابلات السنوية** (Evaluation Reviews & Dynamic Fields) | `document_ar_working.md`<br>`Utiliser_les_variables_du_questionnaire_salarie_ar_working.md` | - سجل المقابلات والتقييم السنوي للموظفين وحفظ النتائج<br>- حقول استبيانات مخصصة لملفات الموظفين |
| **10** | **بوابة الموظف والتأمين المتقدم** (Self-Service Portal & Security) | `Syncra_ar_documents_mobile_working.md`<br>`Syncra_ar_e_payroll_working.md`<br>`Syncra_ar_dark_mode_working.md`<br>`Se_connecter_avec_authentification_externe_ou_OTP_mySilae_ar_working.md` | - تحميل قسائم الأجر الإلكترونية والشهادات الإدارية<br>- الوضع الداكن (Dark Mode) المعتمد<br>- التحقق الثنائي OTP وتأمين الجلسات السحابية |

---

## 2. البنية البرمجية وقاعدة البيانات (Database Schema Extensions)

سنقوم بتوسيع قاعدة البيانات SQLite السحابية (`syncra_saas.db`) عبر دوال ترقية تلقائية (Migration Engine) دون الإخلال بالبيانات الحالية:

1. **جدول `absences` (سجل الغيابات والإجازات)**:
   - `id`, `tenant_id`, `employee_id`, `type`, `start_date`, `end_date`, `days_count`, `reason`, `document_url`, `status` (`PENDING`, `APPROVED`, `REJECTED`, `CANCEL_REQUESTED`, `CANCELLED`), `manager_id`, `approved_at`, `notes`.
2. **جدول `employee_hours` (ساعات العمل وتفاصيل الدوام)**:
   - `id`, `tenant_id`, `employee_id`, `year`, `month`, `regular_hours`, `hs_50`, `hs_100`, `night_hours`, `holiday_hours`, `notes`, `created_at`.
3. **جدول `medical_visits` (سجل زيارات طب العمل)**:
   - `id`, `tenant_id`, `employee_id`, `visit_type`, `scheduled_date`, `completed_date`, `doctor_name`, `medical_center`, `fitness_status`, `next_visit_date`, `document_url`, `status`, `notes`.
4. **جدول `job_templates` (قوالب الوظائف الجاهزة)**:
   - `id`, `tenant_id`, `title`, `department`, `contract_type`, `default_salary`, `transport`, `basket`, `bonus`, `cnas_rate`, `irg_category`.
5. **جدول `annual_evaluations` (المقابلات والتقييمات السنوية)**:
   - `id`, `tenant_id`, `employee_id`, `evaluator_id`, `evaluation_year`, `score_percentage`, `objectives_achieved`, `strengths`, `improvements`, `status`, `created_at`.
6. **جدول `dossier_transfers` (سجل حركات ونقل الموظفين)**:
   - `id`, `tenant_id`, `employee_id`, `from_dept`, `to_dept`, `from_manager`, `to_manager`, `transfer_date`, `reason`, `authorized_by`.

---

## 3. واجهات برمجة التطبيقات (FastAPI Backend Endpoints)

إضافة مسارات RESTful موثقة في `syncra_engine/server.py` مع عزل المستأجرين (Tenant Isolation):

- **مسارات الغيابات والاعتمادات**:
  - `GET /api/absences?tenant_id=...`
  - `POST /api/absences` (تسجيل غياب فردي أو جماعي)
  - `POST /api/absences/{id}/approve` (اعتماد المدير)
  - `POST /api/absences/{id}/reject`
  - `POST /api/absences/bulk-approve` (الاعتماد الجماعي)
  - `POST /api/absences/{id}/request-cancel` (طلب إلغاء غياب معتمد)
  - `DELETE /api/absences/{id}` (حذف غياب معلق قبل الإغلاق)
- **مسارات ساعات العمل**:
  - `GET /api/hours?tenant_id=...&month=...&year=...`
  - `POST /api/hours`
  - `POST /api/hours/import-excel` (استيراد ملف ساعات العمل)
- **مسارات المتغيرات والمصادقة**:
  - `POST /api/variables/import-excel` (استيراد جماعي للمتغيرات)
  - `POST /api/variables/validate-month` (مصادقة المتغيرات وقفل مصفوفة الإدخال)
- **مسارات طب العمل**:
  - `GET /api/medical-visits?tenant_id=...`
  - `POST /api/medical-visits`
  - `PUT /api/medical-visits/{id}`
- **مسارات نماذج الوظائف**:
  - `GET /api/job-templates?tenant_id=...`
  - `POST /api/job-templates`
- **مسارات مساعد إنهاء الخدمة ومخالصة STC**:
  - `POST /api/exit-wizard/calculate`
  - `POST /api/exit-wizard/complete`
- **مسارات المقابلات السنوية والنقل**:
  - `GET /api/evaluations?tenant_id=...`
  - `POST /api/evaluations`
  - `POST /api/transfers`

---

## 4. واجهة المستخدم السحابية (Enterprise SaaS UI Integration)

تحديث `index.html` وتضمين المكونات الجديدة بدقة فائقة وجماليات حديثة (SaaS-grade UX):

1. **الشريط الجانبي (Sidebar Navigation)**:
   - إضافة أقسام منظمة:
     - 📅 **إدارة الحضور والغيابات** (Absences & Congés) + شارة الطلبات المعلقة.
     - ⏱️ **ساعات الدوام والإضافي** (Saisie des Heures).
     - 🩺 **طب العمل والزيارات الطبية** (Médecine du Travail).
     - 🚪 **مساعد مغادرة الموظف (Exit Wizard)**.
     - 📋 **قوالب الوظائف والمقابلات** (Modèles & Évaluations).
     - 📥 **بوابة الاستيراد والتصدير** (Centre Import/Export).
2. **شاشات العرض التفاعلية (Views)**:
   - شاشة الغيابات مع إمكانية الفلترة بالتقويم، التقديم، والموافقة السريعة للمدير.
   - شاشة الساعات مع جدول تفاعلي وإمكانية تحميل ملف إكسل نموذجي.
   - شاشة طب العمل مع بطاقات تنبيهات للمواعيد القادمة وحالة الأهلية الطبية.
   - معالج خروج الموظف بخطوات مرئية تفاعلية (Stepper Wizard: بيانات الخروج -> المستحقات -> التوقيع الإلكتروني -> طباعة المستندات).
   - نافذة الاستيراد والتصدير الذكية مع دعم السحب والإفلات وتنزيل النماذج الجاهزة.
3. **التأمين والوضع الداكن**:
   - مراجعة زر التبديل السلس للوضع الداكن (Dark Mode) وربطه بجميع الجداول والشاشات الجديدة.
   - دعم التحقق OTP والشاشات الآمنة.

---

## 5. خطة الفحص والنشر على Render (Verification & Deployment Plan)

1. **فحص خادم FastAPI والـ Node Proxy محلياً**:
   - اختبار جميع المسارات والتحقق من صحة ردود الـ JSON وعزل المؤسسات.
   - اختبار تشغيل الخادم عبر `node server.js` والتأكد من نجاح الـ Reverse Proxy.
2. **فحص الـ Docker Container والبيئة السحابية**:
   - اختبار استجابة `GET /api/health` وخلو السجلات من أي أخطاء.
3. **الدفع إلى مستودع GitHub**:
   - إعداد Commit منظم وشامل يشمل كافة الميزات الجديدة.
   - عمل `git push` إلى الفرع الرئيسي لإطلاق الـ Auto-Deploy على منصة **Render** بنجاح.
