# SYNCRA — سجل التتبع والتنفيذ والمنجزات (Execution Trace & Deliverables)

> **التاريخ:** 01 أكتوبر 2026  
> **الإصدار:** v1.0.0-core  
> **حالة المشروع:** تم بناء النواة التقنية، بيئة الاختبارات، وتطبيق الويب التفاعلي بالكامل وفق التوجيه الصريح للعميل.

---

## 1. تفكيك ميثاق العمل وقرارات التسمية (Rebranding & Charter)

1. **اعتماد اسم التطبيق الجديد:** تم تغيير وتثبيت الاسم رسمياً إلى **SYNCRA** (نظام سينكرا لهندسة الأجور الجزائرية) في جميع الملفات والشاشات ووثائق التنفيذ.
2. **الالتزام بالفصل الصارم (The Prime Directive):**
   - ✅ **فصل تام:** النواة التقنية (Technical Engine) مستقلة تماماً عن النواة القانونية (Legal Core).
   - 🟢 **ما تم تنفيذه (الضوء الأخضر):** دورة الحياة الثلاثية، الختم الجنائي، ثنائية التوقيت، مفتاح تساوي القوة، بوابات التحقق الأربع، ومحاكي الـ JSON AST.
   - 🔴 **ما تم احترامه وتجميده (الضوء الأحمر):** لم يتم تشفير أي معادلة رواتب صلبة (IRG، SS، STC)؛ وتم إدراج عناصر المصفوفة الـ 14 بحالتها المعلقة `BLOQUE` أو `CIBLE_CONDITIONNELLE` مع قيد `implementation_autorisee = false`.
   - ⚖️ **القاعدة الذهبية (Fail-Fast):** تم التحقق عملياً وبرمجياً من أن أي نقص في سياسة تقريب، أو غياب ترجمة، أو تعارض تنظيمي يؤدي إلى التوقف الفوري ورفض الحساب دون أي fallback صامت.

---

## 2. المنظومة التفاعلية والموقع الإلكتروني (Interactive Trilingual Web Portal)

تم بناء وتحديث الصفحة الرئيسية للمشروع في [`index.html`](file:///c:/projects_flutter/mizan/index.html) بمواصفات تصميم فائقة الجودة:

- **الوضع الليلي والنهاري (Light & Dark Mode):**
  - زر تبديل سلس في شريط التنقل العلوي مع حفظ الحالة في `localStorage`.
  - لوحة ألوان عصرية تعتمد على تدرجات HSL العميقة (`Slate-900` للوضع الليلي و `Slate-50` للوضع النهاري).
- **الدعم الثلاثي الكامل للغات (Trilingual Localization):**
  - **العربية (`ar`):** واجهة كاملة بنظام اتجاه اليمين `dir="rtl"` وخط `Cairo`.
  - **الفرنسية (`fr`):** واجهة كاملة بنظام اتجاه اليسار `dir="ltr"` وخط `Outfit`.
  - **الإنجليزية (`en`):** واجهة كاملة بنظام اتجاه اليسار `dir="ltr"` وخط `Outfit`.
  - قاموس نصوص شامل ومفصل دون استخدام نصوص تجريبية.
- **أدوات المحاكاة التفاعلية وشاشات الدليل المدمجة في الموقع:**
  1. **شاشة الدليل الإرشادي التفاعلي (How to Use from Zero to End):** شاشة منبثقة تفاعلية تشرح الخطوات الست لاستخدام واختبار المنصة من الصفر حتى النهاية مع أزرار انتقال وتوجيه آلي لكل قسم، ومترجمة بالكامل للغات الثلاث.
  2. **محاكي مفتاح تساوي القوة (Idempotency Hasher):** تجزئة قياسية Canonical JSON وتوليد بصمة `SHA-256` للمستندات فورياً.
  3. **محاكي دورة الحياة (3-State Stepper):** معاينة الانتقال من `SAISIE` إلى `EN_CALCUL` ثم `CLOTURE`، ومحاكاة إحباط تعديل كشف مغلق عبر مشغلات SQL.
  4. **كتالوج الرفض الصريح (Fail-Fast Playground):** فحص سيناريوهات غياب التقريب، نقص الترجمة، تعارض ANEM، وتسريب PII.
  5. **مستكشف مصفوفة الحسابات الـ 14:** جدول ديناميكي تفاعلي يبين حالة كل عنصر من الـ 14 عنصراً وسبب تعليقه والصيغة المرشحة.

---

## 3. المنجزات على مستوى قاعدة البيانات (Database Infrastructure)

تم إنشاء ملف الترحيل الفني الكامل:
- [`supabase/migrations/20261001000001_syncra_engine_core.sql`](file:///c:/projects_flutter/mizan/supabase/migrations/20261001000001_syncra_engine_core.sql)

### محتويات الترحيل:
1. `cycle_state` (`SAISIE`, `EN_CALCUL`, `CLOTURE`).
2. `rule_status` (`BLOQUE`, `CIBLE_CONDITIONNELLE`, `VALIDE_HORS_PRODUCTION`, ...).
3. جدول الملفات المستقلة متعددة المستأجرين `dossier`.
4. جدول دورات الرواتب `payroll_cycle` المحمي بقيود الفترات الزمنية.
5. جدول القيم ثنائية التوقيت `bitemporal_value` لتسجيل زمن الفاعلية (`valid_from/to`) وزمن المعاملة (`tx_from/to`).
6. سجل القواعد `rule_registry` ومخطط الاعتماديات `rule_dependency`.
7. جداول التجميد `manifest` (المدخلات) و `snapshot` (المخرجات) مع قيود تفرد البصمات.
8. جداول التدقيق الجنائي `calc_attempt` و `rule_execution_trace`.
9. قاموس اللغات الثلاث `data_label_catalog` (`ar`, `fr`, `en`).
10. سجل المخرجات الثنائية `render_artifact` المرتبط بمفتاح تساوي القوة الفريد.
11. جدول طوابير الرسائل الخالي من PII `mq_outbox`.
12. مشغل الحماية الجنائية لمنع تعديل السجلات المغلقة: `prevent_closed_snapshot_mutation`.
13. مشغل منع إغلاق الدورة دون Snapshot معتمد: `prevent_invalid_cycle_close`.
14. العرض الآمن للقواعد المعتمدة: `v_rules_executable`.
15. حقن بنود مصفوفة الحسابات الـ 14 المعلقة وتخزين الصيغ المرشحة غير النشطة `rule_formula_candidate`.

---

## 4. المنجزات على مستوى كود المحرك البرمجي (Engine Modules)

تم بناء النواة البرمجية الكاملة في مجلد [`syncra_engine/`](file:///c:/projects_flutter/mizan/syncra_engine/):

1. **[`syncra_engine/diagnostic_errors.py`](file:///c:/projects_flutter/mizan/syncra_engine/diagnostic_errors.py):**
   - هيكل استثناءات وأخطاء تشخيصية واضحة وموحدة تطبق مبدأ التوقف الصريح (Fail-Fast).
2. **[`syncra_engine/idempotency.py`](file:///c:/projects_flutter/mizan/syncra_engine/idempotency.py):**
   - التسلسل القياسي Canonical JSON للأرقام والمفاتيح دون مشاكل الفاصلة العائمة (No Float Drifts).
   - توليد مفتاح تساوي القوة `compute_render_idempotency_key` بصيغة `SHA-256`.
   - توليد بصمات `manifest_hash` و `snapshot_hash`.
3. **[`syncra_engine/lifecycle.py`](file:///c:/projects_flutter/mizan/syncra_engine/lifecycle.py):**
   - محرك حالات دورة الرواتب: `SAISIE` ➔ `EN_CALCUL` ➔ `CLOTURE`.
   - منع تعديل الـ Snapshot بعد ختمه جنائياً (`update_results` يطلق استثناء أمني).
   - التراجع الآمن `rollback_to_saisie` دون مسح المحاولات السابقة.
4. **[`syncra_engine/gates.py`](file:///c:/projects_flutter/mizan/syncra_engine/gates.py):**
   - **Gate 1:** فحص الاعتماد القانوني بالنص العربي للجريدة الرسمية N1 وسريان التاريخ.
   - **Gate 2:** التحقق الصارم من العزل ومنع الوصول العابر بين الملفات مع تطبيق RBAC.
   - **Gate 3:** فحص طابور الرسائل وحظر أي تسريب لحقول PII (`nss`, `employee_name`)، وفحص اكتمال اللغات الثلاث.
   - **Gate 4:** التحقق من مطابقة البصمة البايتية لبيانات الاختبارات الذهبية.
   - **القاعدة الذهبية:** فحص إلزامية سياسة التقريب وفحص سلامة وصلاحية قرارات ANEM.

---

## 5. نتائج تشغيل حزمة الاختبارات الآلية (Test Runner Execution)

تم تشغيل حزمة الاختبارات الآلية عبر الأمر:
```bash
python -m syncra_engine.test_runner
```

### سجل المخرجات الفعلي:
```text
======================================================================
🚀 STARTING SYNCRA AUTOMATED ENGINE TESTS & VALIDATION GATES
======================================================================
✔ TEST 1 PASSED: Idempotency Key Determinism Verified (53541ecef59823c0...)
✔ TEST 2 PASSED: 3-State Lifecycle Verified (SAISIE -> EN_CALCUL -> CLOTURE)
✔ TEST 3 PASSED: Mutating closed snapshot correctly blocked -> [SYNCRA_SECURITY_VIOLATION]
✔ TEST 4 PASSED: Gate 1 correctly blocked unapproved rule -> [SYNCRA_ERR_UNAUTHORIZED_RULE_EXECUTION]
✔ TEST 5 PASSED: Gate 2 correctly rejected cross-dossier access -> [SYNCRA_ERR_CROSS_DOSSIER_ACCESS]
✔ TEST 6 PASSED: Gate 3 caught PII leak in MQ payload -> [SYNCRA_ERR_PII_LEAK_IN_MQ]
✔ TEST 7 PASSED: Gate 3 halted on missing translation -> [SYNCRA_ERR_LABEL_MISSING_TRANSLATION]
✔ TEST 8 PASSED: Golden Rule halted on missing rounding policy -> [SYNCRA_ERR_ROUNDING_POLICY_MISSING]
✔ TEST 9 PASSED: Golden Rule halted on expired ANEM decision -> [SYNCRA_ERR_REGULATORY_CONFLICT_ANEM]
======================================================================
🏁 TEST SUMMARY: 9 PASSED, 0 FAILED (TOTAL 9)
======================================================================
```

---

## 6. الدليل المرجعي للملفات المنشأة في المشروع

| المسار | نوع الملف | الغرض والوظيفة |
| :--- | :---: | :--- |
| [`index.html`](file:///c:/projects_flutter/mizan/index.html) | HTML/CSS/JS | بوابة الويب التفاعلية لـ SYNCRA تدعم Light/Dark mode ولغات AR/FR/EN ومحاكيات النظام. |
| [`supabase/migrations/20261001000001_syncra_engine_core.sql`](file:///c:/projects_flutter/mizan/supabase/migrations/20261001000001_syncra_engine_core.sql) | SQL Migration | ترحيل قاعدة البيانات لجميع الجداول الـ 12 والمشغلات الجنائية وسجل القواعد N1. |
| [`syncra_engine/diagnostic_errors.py`](file:///c:/projects_flutter/mizan/syncra_engine/diagnostic_errors.py) | Python Code | كلاسات الاستثناءات التشخيصية للقاعدة الذهبية (Fail-Fast). |
| [`syncra_engine/idempotency.py`](file:///c:/projects_flutter/mizan/syncra_engine/idempotency.py) | Python Code | خوارزمية مفتاح تساوي القوة والتسلسل القياسي وبصمة SHA-256. |
| [`syncra_engine/lifecycle.py`](file:///c:/projects_flutter/mizan/syncra_engine/lifecycle.py) | Python Code | نموذج دورة الحياة الثلاثي وتجميد وحماية الـ Snapshots. |
| [`syncra_engine/gates.py`](file:///c:/projects_flutter/mizan/syncra_engine/gates.py) | Python Code | محرك بوابات التحقق الأربع وحظر PII واكتمال اللغات. |
| [`syncra_engine/test_runner.py`](file:///c:/projects_flutter/mizan/syncra_engine/test_runner.py) | Python Code | حزمة الاختبارات الآلية الشاملة (9 اختبارات إيجابية وسلبية ناجحة). |
| [`SYNCRA_IMPLEMENTATION/`](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/) | Documentation | مجلد التوثيق المعماري الكامل (00 إلى 06). |
