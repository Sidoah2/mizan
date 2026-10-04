# SYNCRA — مفتاح تساوي القوة وثبات الهوية الثنائية للمخرجات (Idempotency & Render Artifacts)

> **المبدأ الهندسي:** إذا قمت بإرسال نفس المدخلات لنفس الدورة 1000 مرة، يجب أن يُنتج محرك SYNCRA ملفات PDF وبيانات متطابقة بايتياً (Bit-by-Bit Identical)، وبنفس البصمة الرقمية `SHA-256`.

---

## 1. خوارزمية مفتاح تساوي القوة (Idempotency Key Algorithm)

تعتمد خوارزمية `request_key_sha256` على التوليد المنضبط التالي:

```
request_key_sha256 = SHA256(
    dossier_id + ":" +
    snapshot_id + ":" +
    document_type + ":" +
    lang + ":" +
    template_id + ":" +
    template_version + ":" +
    policy_id + ":" +
    engine_version + ":" +
    font_manifest_hash
)
```

### شروط التسلسل القياسي (Canonical Serialization):
1. **الترتيب الصارم للمفاتيح (Key Sorting):** ترتيب جميع عناصر الـ JSON هجائياً قبل حساب البصمة.
2. **منع الأعداد العشرية العائمة (`float`):** استخدام المبالغ بالسنتيم كأعداد صحيحة (`BigInt`) أو سلاسل نصية بدقة محددة (`Fixed-point Decimals` مثل `100000.00`).
3. **توحيد الترميز:** إلزامية استخدام `UTF-8` حصراً، وتوحيد المسافات البيضاء.

---

## 2. جدول أرشيف المخرجات الثنائية (`render_artifact`)

يتم توثيق كل مستند مُنتج (مثل كشف الراتب، تصريح CNAS، جدول G50) في جدول `render_artifact`:

```sql
CREATE TABLE render_artifact (
  artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dossier_id UUID NOT NULL REFERENCES dossier(dossier_id),
  snapshot_id UUID NOT NULL REFERENCES snapshot(snapshot_id),
  document_type TEXT NOT NULL,                -- e.g., 'PAYSLIP', 'CNAS_DECLARATION'
  lang TEXT NOT NULL CHECK (lang IN ('ar','fr','en')),
  template_id TEXT NOT NULL,
  template_version TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  font_manifest_hash TEXT NOT NULL,
  request_key_sha256 TEXT NOT NULL,           -- مفتاح تساوي القوة الفريد
  binary_sha256 TEXT NOT NULL,                -- بصمة الملف الثنائي المولد (PDF/Doc)
  storage_uri TEXT,                           -- المسار الآمن في التخزين المشفر
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (request_key_sha256)
);
```

### القواعد الصارمة لهذا الجدول:
1. **قيد التفرد (`UNIQUE request_key_sha256`):**
   - إذا تم طلب توليد نفس المستند مرة أخرى، يعيد المحرك فوراً المستند المخزن سابقاً دون إعادة رندرة (Zero Waste / Exact Idempotence).
2. **التحقق من التطابق البايتي:**
   - في بيئة الاختبارات، إذا أُعيد توليد الملف واختلفت بصمة `binary_sha256`، يُعتبر ذلك خطأ فادحاً (Visual or Binary Regression) ويتم إيقاف النشر.

---

## 3. معايير إخراج الوثائق (Document Rendering Principles)

وفقاً للقرارات التسعة المعتمدة في ملف التأطير:

1. **الوثائق أحادية اللغة (Monolingual Documents):**
   - كل وثيقة رسمية قانونية تُولد **بلغة واحدة كاملة** فقط (`ar` أو `fr` أو `en`).
   - لا يجوز خلط اللغات في المستند الرسمي الواحد (تجنب التداخل النصي والتشويه البصري).
2. **فصل المرفقات التفسيرية عن الكشف الرسمي:**
   - كشف الراتب القانوني (`Bulletin Réglementaire`) يُصدر منفرداً ونظيفاً.
   - إذا رغب المشرف في شروحات الحساب، تُصدر في وثيقة ملحقة منفصلة (`Annexe Explicative`).
3. **تجميد الخطوط (Font Manifest):**
   - الخطوط المستخدمة في توليد ملفات PDF (مثل خطوط الطباعة العربية الرسمية Cairo / Amiri) تُحفظ بأرقام إصداراتها وبصمة `font_manifest_hash`.
   - لا يُعتمد على خطوط النظام الافتراضية لمنع أي إزاحة في أماكن الأرقام أو النصوص.
