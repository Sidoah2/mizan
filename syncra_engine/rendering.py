"""
SYNCRA Engine - Rendering Module & Article 86 Compliance
=========================================================
Implements:
1. Canonical Envelope serialization and idempotent request hashing (request_key_sha256).
2. Monolingual payslip generation conforming strictly to Article 86 of Law 90-11:
   - Explicit named itemization of every wage element (base salary, bonuses, allowances, deductions).
   - Strict isolation of expense reimbursements (frais de mission/transport) so they are not merged into social/tax bases.
3. Fail-fast label checking against data_label_catalog (BLOCAGE_LIBELLE_MANQUANT).
4. Deterministic rendering seal (binary_sha256).
"""

import hashlib
import json
from decimal import Decimal
from typing import Dict, Any, List, Optional
from syncra_engine.diagnostic_errors import SyncraValidationError, SyncraIdempotencyError
from syncra_engine.idempotency import SyncraCanonicalSerializer

# Standard trilingual label catalog for statutory payslips
STATUTORY_LABEL_CATALOG = {
    "BASE_SALARY": {"ar": "الراتب الأساسي", "fr": "Salaire de base", "en": "Base Salary"},
    "BONUS_PERFORMANCE": {"ar": "منحة المردودية", "fr": "Prime de rendement", "en": "Performance Bonus"},
    "BONUS_SENIORITY": {"ar": "منحة الأقدمية", "fr": "Prime d'ancienneté", "en": "Seniority Bonus"},
    "EXPENSE_REIMBURSEMENT_MISSION": {"ar": "تعويض مصاريف المهمة", "fr": "Indemnité de frais de mission", "en": "Mission Expense Reimbursement"},
    "EXPENSE_REIMBURSEMENT_TRANSPORT": {"ar": "تعويض مصاريف التنقل", "fr": "Indemnité de transport", "en": "Transport Expense Reimbursement"},
    "COTISATION_SS_SALARIALE": {"ar": "اشتراك الضمان الاجتماعي (أجير 9%)", "fr": "Cotisation Sécurité Sociale (Salariale 9%)", "en": "Social Security Contribution (Employee 9%)"},
    "COTISATION_SS_PATRONALE": {"ar": "اشتراك الضمان الاجتماعي (صاحب عمل 25%)", "fr": "Cotisation Sécurité Sociale (Patronale 25%)", "en": "Social Security Contribution (Employer 25%)"},
    "OEUVRES_SOCIALES": {"ar": "الخدمات الاجتماعية (0.5%)", "fr": "Œuvres Sociales (0.5%)", "en": "Social Works (0.5%)"},
    "RETENUE_IRG": {"ar": "الضريبة على الدخل الإجمالي (IRG)", "fr": "Retenue IRG", "en": "IRG Tax Withholding"},
    "NET_A_PAYER": {"ar": "صافي الدفع النهائي", "fr": "Net à payer", "en": "Net Payable"},
    "SALAIRE_BRUT": {"ar": "الأجر الخام الخاضع", "fr": "Salaire brut imposable", "en": "Gross Taxable Salary"},
    "ASSIETTE_SS": {"ar": "وعاء اشتراك الضمان الاجتماعي", "fr": "Assiette cotisations Sécurité Sociale", "en": "Social Security Contribution Base"},
    "ASSIETTE_IRG": {"ar": "وعاء الضريبة على الدخل", "fr": "Assiette fiscale IRG", "en": "IRG Tax Base"},
    "TOTAL_GAINS": {"ar": "مجموع الاستحقاقات", "fr": "Total des gains", "en": "Total Earnings"},
    "TOTAL_RETENUES": {"ar": "مجموع الاقتطاعات", "fr": "Total des retenues", "en": "Total Deductions"},
}

# Standard certified font manifest hashes
FONT_MANIFEST_REGISTRY = {
    "ar": {
        "primary_font": "Amiri-Regular.ttf",
        "font_manifest_hash": "sha256-amiri-v0.12-arabic-standard-seal-8f4b2"
    },
    "fr": {
        "primary_font": "Marianne-Regular.otf",
        "font_manifest_hash": "sha256-marianne-v2.1-latin-standard-seal-3c1a9"
    }
}


class SyncraRenderingEngine:
    """
    Renders official monolingual payslips and accounting artifacts
    guaranteeing bit-for-bit repeatability and strict statutory compliance.
    """
    ENGINE_VERSION = "2026.10-syncra-v0.2"
    TEMPLATE_VERSION = "1.0.0-art86"

    def __init__(self, custom_label_catalog: Optional[Dict[str, Dict[str, str]]] = None):
        self.catalog = dict(STATUTORY_LABEL_CATALOG)
        if custom_label_catalog:
            self.catalog.update(custom_label_catalog)

    def generate_canonical_request_key(
        self,
        dossier_id: str,
        snapshot_id: str,
        document_type: str,
        lang: str,
        template_id: str,
        policy_id: str,
    ) -> str:
        """
        Computes the canonical SHA-256 request key for render idempotency:
        request_key = sha256(canonical_json({
            dossier_id, snapshot_id, document_type, lang,
            template_id, template_version, policy_id,
            engine_version, font_manifest_hash
        }))
        """
        if lang not in FONT_MANIFEST_REGISTRY:
            raise SyncraValidationError(
                f"Unsupported language code '{lang}'. Supported: {list(FONT_MANIFEST_REGISTRY.keys())}"
            )

        font_manifest_hash = FONT_MANIFEST_REGISTRY[lang]["font_manifest_hash"]

        canonical_payload = {
            "dossier_id": dossier_id,
            "document_type": document_type,
            "engine_version": self.ENGINE_VERSION,
            "font_manifest_hash": font_manifest_hash,
            "lang": lang,
            "policy_id": policy_id,
            "snapshot_id": snapshot_id,
            "template_id": template_id,
            "template_version": self.TEMPLATE_VERSION,
        }

        canonical_bytes = SyncraCanonicalSerializer.serialize(canonical_payload)
        return hashlib.sha256(canonical_bytes).hexdigest()

    def translate_rubrique(self, rubric_code: str, lang: str) -> str:
        """
        Resolves rubric translation from the label catalog.
        Fails fast if the label is missing in the target language.
        """
        if rubric_code not in self.catalog:
            raise SyncraValidationError(
                f"BLOCAGE_LIBELLE_MANQUANT: Rubric code '{rubric_code}' is not registered in data_label_catalog."
            )
        translations = self.catalog[rubric_code]
        if lang not in translations or not translations[lang]:
            raise SyncraValidationError(
                f"BLOCAGE_LIBELLE_MANQUANT: Translation for rubric '{rubric_code}' in language '{lang}' is missing."
            )
        return translations[lang]

    def render_monolingual_payslip(
        self,
        dossier_id: str,
        snapshot_id: str,
        employee_synthetic_id: str,
        period: str,
        lang: str,
        items: List[Dict[str, Any]],
        template_id: str = "TPL_BULLETIN_PAIE_STANDARD",
        policy_id: str = "POLICY_ROUNDING_HALF_UP_2DP",
    ) -> Dict[str, Any]:
        """
        Renders a certified monolingual payslip conforming to Article 86 of Law 90-11:
        1. Explicitly items each salary element.
        2. Strictly segregates expense reimbursements from taxable/social bases.
        3. Fails fast if any label is missing in the chosen language.
        4. Produces deterministic binary_sha256.
        """
        if lang not in ("ar", "fr"):
            raise SyncraValidationError(
                f"Monolingual rendering requires 'ar' or 'fr', received '{lang}'."
            )

        # 1. Compute request_key_sha256
        request_key = self.generate_canonical_request_key(
            dossier_id=dossier_id,
            snapshot_id=snapshot_id,
            document_type="BULLETIN_DE_PAIE",
            lang=lang,
            template_id=template_id,
            policy_id=policy_id,
        )

        # 2. Categorize items according to Art. 86
        gains_items = []
        deductions_items = []
        expense_reimbursements = []

        total_gains = Decimal("0.00")
        total_deductions = Decimal("0.00")
        total_expenses = Decimal("0.00")

        for itm in items:
            code = itm["code"]
            raw_amount = Decimal(str(itm["amount"]))
            label = self.translate_rubrique(code, lang)
            item_type = itm.get("type", "GAIN")

            entry = {
                "code": code,
                "label": label,
                "amount": f"{raw_amount:.2f}",
                "unit": itm.get("unit", "DZD"),
                "quantity": str(itm.get("quantity", "1.00")),
                "base": str(itm.get("base", raw_amount)),
            }

            if item_type == "EXPENSE_REIMBURSEMENT":
                # Art. 86 exception: Reimbursement of expenses must NOT be merged with earnings/bases
                expense_reimbursements.append(entry)
                total_expenses += raw_amount
            elif item_type == "DEDUCTION":
                deductions_items.append(entry)
                total_deductions += raw_amount
            else:
                gains_items.append(entry)
                total_gains += raw_amount

        net_salary = total_gains - total_deductions + total_expenses

        # 3. Assemble monolingual document model
        doc_model = {
            "header": {
                "dossier_id": dossier_id,
                "snapshot_id": snapshot_id,
                "employee_id": employee_synthetic_id,
                "period": period,
                "lang": lang,
                "document_title": "كشف الراتب والتحصيص الدوري (المادة 86)" if lang == "ar" else "Bulletin de Paie Périodique (Art. 86)",
                "statutory_reference": "القانون 90-11 المادة 86 / Loi 90-11 Art. 86",
                "request_key_sha256": request_key,
                "engine_version": self.ENGINE_VERSION,
            },
            "remuneration_elements": {
                "gains": gains_items,
                "total_gains": f"{total_gains:.2f}",
            },
            "deductions_elements": {
                "deductions": deductions_items,
                "total_deductions": f"{total_deductions:.2f}",
            },
            "expense_reimbursements_isolated": {
                "expenses": expense_reimbursements,
                "total_expenses": f"{total_expenses:.2f}",
                "isolation_note": (
                    "تطبيقاً للمادة 86 من القانون 90-11، تم استثناء تعويضات المصاريف وفصلها تماماً عن وعاء الأجر الخاضع."
                    if lang == "ar"
                    else "En application de l'art. 86 de la loi 90-11, les remboursements de frais sont strictement exclus de l'assiette cotisable/imposable."
                )
            },
            "summary": {
                "net_a_payer": f"{net_salary:.2f}",
                "currency": "DZD",
            }
        }

        # 4. Generate deterministic canonical representation & binary seal
        canonical_content = SyncraCanonicalSerializer.serialize(doc_model)
        binary_sha256 = hashlib.sha256(canonical_content).hexdigest()

        return {
            "request_key_sha256": request_key,
            "binary_sha256": binary_sha256,
            "lang": lang,
            "document_model": doc_model,
            "canonical_bytes_len": len(canonical_content),
            "status": "RENDER_SEALED"
        }
