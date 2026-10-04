-- =====================================================================
-- MIZAN (ميزان) - Confirmed Algerian Legal Rates Seed
-- =====================================================================

INSERT INTO legal_rates (code, label, rate_percent, payer, effective_from, legal_source)
VALUES 
    ('CNAS_EMP', 'حصة العامل في الضمان الاجتماعي (Cotisation CNAS Salarié)', 9.00, 'EMPLOYEE', '1995-01-01', 'Loi n° 83-11 relative aux assurances sociales'),
    ('CNAS_PAT', 'حصة صاحب العمل في الضمان الاجتماعي (Cotisation CNAS Patronale)', 26.00, 'EMPLOYER', '1995-01-01', 'Loi n° 83-11 relative aux assurances sociales'),
    ('CASNOS', 'اشتراك الصندوق الوطني للضمان الاجتماعي لغير الأجراء', 15.00, 'SELF_EMPLOYED', '2015-01-01', 'Décret exécutif n° 15-289')
ON CONFLICT (code) DO NOTHING;

-- Exemption threshold for IRG (حد الإعفاء الضريبي - 30,000 دج شهرياً)
INSERT INTO irg_abatement_rules (min_taxable, max_taxable, abatement_percent, min_abatement, max_abatement, effective_from)
VALUES 
    (30000.01, 35000.00, 40.00, 1000.00, 1500.00, '2022-01-01')
ON CONFLICT DO NOTHING;
