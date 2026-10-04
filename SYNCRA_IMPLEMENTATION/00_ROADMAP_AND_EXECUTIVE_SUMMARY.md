# SYNCRA — Roadmap & Executive Summary (خطة التنفيذ وخارطة الطريق)

> **اسم المشروع الجديد:** **SYNCRA** (سابقاً MIZAN)  
> **تاريخ التحديث:** أكتوبر 2026  
> **المرجعية:** ملف التأطير الفني لمحرك الرواتب وتوجيهات العميل الصريحة.

---

## 1. التوجيه الأساسي وميثاق العمل (The Prime Directive)

وفقاً للتوجيه المباشر في بريد العميل:
> **"الفصل الصارم بين البنية التقنية (Technical Engine) والنواة القانونية (Legal Core)."**

محرك **SYNCRA** ليس مجرد تطبيق لحساب المرتبات؛ بل هو **محرك حساب حتمي (Deterministic Engine)، ثنائي التوقيت (Bitemporal)، ومحصن ضد التعديل بأثر رجعي (Immutable Snapshots)**.

---

## 2. مصفوفة الصلاحيات الفورية (Green Light vs. Red Light)

| النطاق | الحالة | التوجيه الملزم |
| :--- | :---: | :--- |
| **البنية التحتية التقنية (Technical Infrastructure)** | 🟢 **ضوء أخضر فوري** | البدء الفوري في بناء دورة الحياة، خوارزمية التجزئة، بوابات الأمان، ونظام الاختبارات. |
| **دورة حياة الملفات وعدم التغيير (Lifecycle & Immutability)** | 🟢 **ضوء أخضر فوري** | تفعيل التجميد التلقائي عند `EN_CALCUL`، والختم الجنائي النهائي عند `CLOTURE` مع منع التعديل برمجياً. |
| **مفتاح تساوي القوة (Idempotency Key & Hashing)** | 🟢 **ضوء أخضر فوري** | بناء خوارزمية Hashing (`SHA-256`) للمدخلات والمخرجات لضمان التطابق البايتي للأرشيف والوثائق. |
| **بوابات التحقق الأربع (The 4 Validation Gates)** | 🟢 **ضوء أخضر فوري** | برمجة معايير الفحص الأربعة كبوابات تقييم صارمة تمنع تنفيذ أي حساب غير مستوفٍ للشروط. |
| **بيئة الاختبارات المؤتمتة (Automated Test Harness)** | 🟢 **ضوء أخضر فوري** | بناء بيئة اختبار تعتمد على قواعد بصيغة `JSON Declarative AST` لاختبار السيناريوهات السلبية والإيجابية. |
| **معادلات الرواتب والضرائب (IRG, SS, STC, Rubrics)** | 🔴 **ضوء أحمر صارم** | **يُمنع منعاً باتاً برمجة أو تفعيل أي معادلة حسابية (L1-L18)** حتى صدور الاعتماد القانوني الرسمي (N1). |
| **تخمين القواعد الناقصة (Heuristics / Assumptions)** | 🔴 **ضوء أحمر صارم** | **ممنوع نهائياً.** لا تفترض سياسة تقريب، ولا نصاً قانونياً، ولا ترجمة مصطلح مفقود. |

---

## 3. القاعدة الذهبية للتصميم (The Golden Design Rule)

> ⚠️ **"لا تفترض أي شيء (Never Assume). غياب أي قاعدة يعني التوقف الفوري (Fail-Fast) وإصدار خطأ صريح."**

إذا حدث أي مما يلي:
1. غياب قاعدة التقريب (`Rounding Policy Missing`).
2. غياب ترجمة لأحد الحقول في قاموس اللغات الثلاث (العربية، الفرنسية، الإنجليزية).
3. رصد تعارض إداري أو تنظيمي (مثل تضارب قرارات ANEM أو انتهاء صلاحيتها).
4. عدم اعتماد مصدر القاعدة القانونية من الجريدة الرسمية باللغة العربية (`N1 Pending`).

**يجب على محرك SYNCRA أن يتوقف فوراً ويرفض إتمام الحساب، مع إرجاع كود تشخيصي موثق ومفصل (Explicit Diagnostic Error)، ويُمنع أي إجراء بديل صامت (Silent Fallback).**

---

## 4. مراحل التنفيذ المتكاملة (Implementation Phases)

### 🔹 المرحلة 0: حماية القائم وضبط البيئة (Environment & Baseline)
- حصر الإصدارات، والتحقق من عزل المستأجرين (Multi-Tenancy).
- إعداد بيئة اختبارات معزولة بالكامل تعمل ببيانات اصطناعية (Synthetic Data).
- توثيق الفوارق وعدم المساس بأي بيئة إنتاجية.

### 🔹 المرحلة 1: بناء الأسس التقنية (Technical Core Foundation) — [نبدأ بها الآن]
- تنفيذ نموذج الحالات الثلاثي: `SAISIE` ➔ `EN_CALCUL` ➔ `CLOTURE`.
- تفعيل المحفزات الصارمة في قاعدة البيانات لمنع تعديل السجلات بعد غلقها.
- بناء جداول القيم ثنائية التوقيت (Bitemporality): زمن الفاعلية القانونية (`valid_from/to`) وزمن المعاملة النظامية (`tx_from/to`).
- إنشاء سجل المحاولات (`calc_attempt`) والتتبع التفصيلي لكل عقدة (`rule_execution_trace`).

### 🔹 المرحلة 2: محرك الرموز والتجريد واختبارات JSON (AST & JSON Engine) — [نبدأ بها الآن]
- بناء مترجم/مفسر القواعد المجردة (AST Engine) للتعامل مع قواعد JSON دون كتابة كود معادلات صلب.
- بناء شجرة الاعتماديات (Dependency DAG) لكشف الحلقات المغلقة (Circular Dependencies).
- إدراج مصفوفة الحسابات الـ 14 بحالتها المعلقة (`BLOQUE` / `CIBLE_CONDITIONNELLE`) مع `implementation_autorisee = false`.

### 🔹 المرحلة 3: بوابات التحقق وتساوي القوة والإخراج (Gates, Idempotency & Rendering) — [نبدأ بها الآن]
- تطبيق خوارزمية مفتاح تساوي القوة (`request_key_sha256`) وتطابق البايتات (`binary_sha256`).
- برمجة بوابات التحقق الأربع (Gate 1 إلى Gate 4).
- بناء عازل البيانات الشخصية (PII Filter) لمنع خروج أي PII إلى طوابير الرسائل (MQ Outbox).
- بناء محرك القوالب أحادية اللغة (Monolingual Renders) مع التحقق من سلامة الخطوط وعلامات التجزئة.

### 🔹 المرحلة 4: ربط النواة القانونية المعتمدة (Legal Core Integration) — [موقوفة حتى الضوء الأخضر N1]
- عند استلام الاعتماد القانوني الرسمي للمصادر N1، يتم حقن القواعد عبر الـ AST المعتمد دون تغيير سطر واحد في البنية التحتية.

---

## 5. محتويات هذا المجلد (Folder Structure)

1. [00_ROADMAP_AND_EXECUTIVE_SUMMARY.md](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/00_ROADMAP_AND_EXECUTIVE_SUMMARY.md): الملخص التنفيذي وتوجيهات العميل وخارطة الطريق.
2. [01_STATE_MACHINE_AND_IMMUTABILITY.md](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/01_STATE_MACHINE_AND_IMMUTABILITY.md): دورة الحياة الثلاثية، التجميد، الختم الجنائي، وثنائية التوقيت.
3. [02_IDEMPOTENCY_AND_RENDER_ARTIFACTS.md](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/02_IDEMPOTENCY_AND_RENDER_ARTIFACTS.md): خوارزمية مفتاح تساوي القوة، وثبات الهوية الثنائية للمخرجات.
4. [03_SECURITY_AND_THE_FOUR_VALIDATION_GATES.md](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/03_SECURITY_AND_THE_FOUR_VALIDATION_GATES.md): بوابات التحقق الأربع، العزل الصارم، وحماية PII.
5. [04_CALCULATION_MATRIX_AND_RULE_REGISTRY.md](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/04_CALCULATION_MATRIX_AND_RULE_REGISTRY.md): مصفوفة الحسابات الـ 14 ونموذج سجل القواعد بصيغة AST.
6. [05_WHAT_WE_CAN_START_NOW.md](file:///c:/projects_flutter/mizan/SYNCRA_IMPLEMENTATION/05_WHAT_WE_CAN_START_NOW.md): قائمة المهام العملية الجاهزة للتنفيذ الفوري خطوة بخطوة.
