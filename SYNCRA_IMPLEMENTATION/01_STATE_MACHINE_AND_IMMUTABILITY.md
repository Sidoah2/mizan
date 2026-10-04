# SYNCRA — دورة حياة الملفات وعدم قابليتها للتغيير (State Machine & Immutability)

> **المبدأ الهندسي:** لا يجوز في أي حال من الأحوال تعديل البيانات المالية بعد حسابها، ويُمنع الحذف أو التعديل في نفس السجل (No In-Place Overwrites).

---

## 1. نموذج الحالات الثلاثي (The 3-State Lifecycle)

```
        ┌─────────────┐
        │   SAISIE    │ ◄── (إدخال وتعديل البيانات)
        └──────┬──────┘
               │
               ▼  [تجميد المدخلات وتوليد Manifest Hash]
        ┌─────────────┐
        │  EN_CALCUL  │ ◄── (مجمدة للحساب والتدقيق)
        └──────┬──────┘
               │
               ├─────────────────────────┐
               ▼                         ▼
         [إلغاء وتصحيح]           [ختم نهائي معتمد]
               │                         │
               ▼                         ▼
        ┌─────────────┐           ┌─────────────┐
        │   SAISIE    │           │   CLOTURE   │ ◄── (مختومة جنائياً - للقراءة فقط)
        │ (دورة جديدة)│           └─────────────┘
        └─────────────┘
```

### تفاصيل الحالات:
1. **`SAISIE` (الإدخال):**
   - المرحلة المفتوحة لتسجيل المتغيرات، ساعات العمل، الغيابات، وحركات الموظف.
   - لا يوجد فيها `snapshot` نهائي.

2. **`EN_CALCUL` (التجميد للحساب):**
   - بمجرد الضغط على "حساب الراتب"، يتم تجميد جميع المدخلات في وثيقة بيان `Manifest`.
   - يتم حساب بصمة التجزئة (`manifest_hash = SHA256(canonical_inputs)`).
   - تُمنع أي تعديلات على المدخلات المرتبطة بهذه الدورة.
   - إذا رغب المستخدم في التعديل: **لا يتم تعديل السجل الحالي**، بل يتم الرجوع الصريح إلى `SAISIE` لإنشاء محاولة جديدة (`attempt_id` جديد) وبصمة جديدة.

3. **`CLOTURE` (الختم النهائي):**
   - بعد التحقق وموافقة مسؤول الرواتب، يُختم الـ `Snapshot` نهائياً.
   - يصبح الملف في وضع **القراءة فقط (Read-Only)** نهائياً وإلى الأبد.
   - لا يمكن لأي مستخدم أو مشرف (حتى Database Administrator) تعديل أي رقم فيه.

---

## 2. آليات الحماية الجنائية على مستوى قاعدة البيانات (SQL Guards)

### أ. منع تعديل الـ Snapshot المغلق قطيعاً:
```sql
CREATE OR REPLACE FUNCTION prevent_closed_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF old.state = 'CLOTURE' THEN
    RAISE EXCEPTION 'SYNCRA_SECURITY_VIOLATION: Snapshot clôturé: toute mutation est strictement interdite.';
  END IF;
  RETURN new;
END;
$$;

CREATE TRIGGER trg_prevent_closed_snapshot_update
BEFORE UPDATE OR DELETE ON snapshot
FOR EACH ROW
EXECUTE FUNCTION prevent_closed_snapshot_mutation();
```

### ب. منع إغلاق الدورة دون وجود Snapshot صالح:
```sql
CREATE OR REPLACE FUNCTION prevent_invalid_cycle_close()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_exists boolean;
BEGIN
  IF new.state = 'CLOTURE' AND old.state <> 'CLOTURE' THEN
    SELECT EXISTS (
      SELECT 1 FROM snapshot s
      WHERE s.cycle_id = new.cycle_id
        AND s.state = 'CLOTURE'
    ) INTO v_exists;

    IF NOT v_exists THEN
      RAISE EXCEPTION 'SYNCRA_INTEGRITY_VIOLATION: Clôture interdite: aucun snapshot clôturé associé.';
    END IF;
  END IF;
  RETURN new;
END;
$$;

CREATE TRIGGER trg_prevent_invalid_cycle_close
BEFORE UPDATE ON payroll_cycle
FOR EACH ROW
EXECUTE FUNCTION prevent_invalid_cycle_close();
```

---

## 3. هندسة ثنائية التوقيت (Bitemporality Architecture)

لحماية التدرج التاريخي للأجور واللوائح دون فقدان السجلات السابقة، يتم تطبيق التوقيت المزدوج على جدول `bitemporal_value`:

| البعد الزمني | الحقول | المعنى والهدف |
| :--- | :--- | :--- |
| **زمن الفاعلية المهنية (Valid Time)** | `valid_from` , `valid_to` | الفترة الزمنية التي يسري فيها الأجر أو النسبة قانوناً (مثلاً: ساري من 01-01-2024). |
| **زمن المعاملة النظامية (Transaction Time)** | `tx_from` , `tx_to` | اللحظة الدقيقة التي سُجلت فيها البيانات في النظام بواسطة المستخدم أو المشغل. |

### قاعدة التعديل ثنائي التوقيت:
عند تصحيح راتب قديم بأثر رجعي:
1. لا نقوم بأمر `UPDATE` لمسح القيمة القديمة.
2. نضبط `tx_to = NOW()` للقيد السابق لإنهاء صلاحيته في قاعدة البيانات.
3. نُدخل سجلاً جديداً بقيمة `tx_from = NOW()` و `tx_to = NULL` مع الاحتفاظ بفترة الفاعلية `valid_from / valid_to`.
4. بهذه الطريقة يمكن إعادة تشغيل أي حساب في أي تاريخ سابق بدقة بايتية مطلقة.

---

## 4. الفرق بين الـ Manifest والـ Snapshot

- **الـ `Manifest` (بيان المدخلات):**
  - كائن JSON قياسي يضم: هوية الموظف، أيام العمل، نسب الأقدمية، البدلات المصرح بها، والحالة العائلية في تاريخ الحساب.
  - يحمل بصمة فريدة `manifest_hash`.

- **الـ `Snapshot` (لقطة النتائج):**
  - كائن JSON يحفظ المخرجات النهائية لكل بند: اشتراكات، اقتطاعات، صافي الدفع، ومساهمات صاحب العمل.
  - مرتبط مباشرة بالـ `manifest_id`، ولا يمكن إنشاؤه بدونه.
  - يحمل بصمة فريدة `snapshot_hash`.

---

## 5. تتبع محاولات الحساب (Audit Trail & Diagnostic Logging)

- كل محاولة حساب تولد سجلاً في `calc_attempt`:
  - `attempt_id`: UUID فريد.
  - `engine_version`: رقم إصدار المحرك بدقة (مثلاً: `v1.0.0-core`).
  - `status`: حالة المحاولة (`SUCCESS` أو `FAILED`).
  - `diagnostics_json`: التفاصيل الكاملة لأي خطأ أو توقف صريح (Fail-Fast).
- تفريغ مسار تنفيذ القواعد في `rule_execution_trace`:
  - تسجيل المدخلات والمخرجات لكل قاعدة تم تقييمها للتدقيق القانوني ومراجعة مفتشي الضرائب والضمان الاجتماعي.
