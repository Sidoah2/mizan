/**
 * ==========================================================================
 * SILAE MATRIX ENGINE — BPA "État d'avancement" (Multi-Year Grids Layout)
 * Module: js/silae-matrix.js
 * 
 * Features:
 *   - Year range filter (e.g. 2024 to 2026 -> 3 grids, one per year)
 *   - EACH grid ALWAYS displays all 12 months (01 through 12)
 *   - 100% backend driven: GET/POST /api/matrix (SQLite)
 *   - Right-click context menu (js/silae-context-menu.js)
 *   - Fast interactive painter palette, multi-selection, CSV export
 *   - Full Arabic (RTL) & French (LTR) locale support
 * ==========================================================================
 */
(function (window) {
    'use strict';

    // ------------------------------ Dictionary ------------------------------
    const I18N = {
        fr: {
            navBpa: "État d'avancement (BPA)",
            navSalaries: "Salariés",
            navAddSalarie: "+ Nouveau Salarié",
            navRag: "Conseil Juridique (RAG)",
            navOcr: "Congés & Maladie (OCR)",
            navAbsences: "Absences & Congés",
            navStc: "Solde Tout Compte (STC)",
            navImportExport: "Centre Import / Export",
            navSettings: "Paramètres",
            topAddTenant: "+ Nouvelle Entreprise",
            userRoleExpert: "Expert Paie",
            backToMatrix: "Retour à la matrice (BPA)",
            matrixTitle: "État d'avancement (BPA)",
            legendTitle: "LÉGENDE DES STATUTS :",
            legendAll: "Tous les statuts",
            legendCloture: "Clôturé (Validé)",
            legendEnCalcul: "Calculé (à valider)",
            legendEnCours: "En cours (Saisie)",
            legendACalculer: "À calculer (Retard)",
            legendFutur: "Futur (Non démarré)",
            painterTitle: "Pinceau",
            colName: "Tâches / Salariés",
            taskSection: "Tâches Générales",
            empSection: "Salariés du dossier (Base réelle SQLite)",
            tasksBulletins: "Bulletins de Paie",
            tasksVirements: "Virements Bancaires",
            tasksDeclarations: "Déclarations Sociales (CNAS)",
            btnCalculerMois: "Calculer Mois",
            btnExporter: "Exporter CSV",
            btnJournalPaie: "Livre de Paie",
            searchPlaceholder: "Filtrer salarié ou matricule...",
            rangeFrom: "Du",
            rangeTo: "Au",
            presetCurrentYear: "2026",
            preset2Years: "2025 - 2026",
            preset3Years: "2024 - 2026",
            exerciceTitle: (y) => `Exercice ${y} — Année Complète (12 Mois)`,
            exerciceBadge: "12 Mois (01 — 12)",
            taskSectionYear: (y) => `Tâches Générales (${y})`,
            empSectionYear: (y) => `Salariés du dossier — Base réelle SQLite (${y})`,
            statutClotureLabel: "🟢 Clôturé / Validé",
            statutEnCalculLabel: "🟠 Calculé (à valider)",
            statutEnCoursLabel: "🔵 En cours (saisie)",
            statutACalculerLabel: "🔴 À calculer (en retard)",
            statutFuturLabel: "⚪ Futur (non démarré)",
            statutNoneLabel: "Avant embauche",
            noEmployees: "Aucun salarié actif dans ce dossier.",
            noMatch: "Aucun salarié ne correspond à la recherche.",
            loadError: "Impossible de charger la matrice depuis le serveur.",
            confirmBatch: "Calculer tous les bulletins du mois",
            doneChanged: "cellule(s) mise(s) à jour",
            doneSkipped: "ignorée(s)",
            invalidRange: "Plage d'années invalide.",

            // Employees view
            salariesTitle: "Dossier Salariés & Contrats",
            salariesSub: "Gestion des salariés, salaire de base, primes et coordonnées bancaires (SQLite).",
            searchEmpPlaceholder: "Rechercher par nom, matricule ou poste...",
            kpiTotalEmp: "Total Salariés Enregistrés",
            kpiCdi: "Contrats CDI",
            kpiCdd: "Autres Contrats (CDD / ANEM)",
            kpiBaseMass: "Masse Salariale Base",
            thMatricule: "Matricule",
            thNom: "Nom & Prénom",
            thPoste: "Poste & Dép.",
            thContrat: "Type Contrat",
            thSalaireBase: "Salaire de Base",
            thIep: "Prime IEP",
            thBanque: "Banque / RIP",
            thStatut: "Statut",
            thActions: "Actions",
            addEmpTitle: "Fiche Nouveau Salarié",
            addEmpSub: "Fiche salarié, contrat de travail, salaire de base et coordonnées bancaires (SQLite).",
            btnSaveEmp: "Enregistrer le Salarié",
            ragTitle: "Conseil Juridique & Réglementaire (IA)",
            ocrTitle: "Gestion des Congés & Arrêts Maladie (OCR)",
            stcTitle: "Solde Tout Compte (STC)",
            absencesTitle: "Absences & Congés (Gestion & Validation)",
            importExportTitle: "Centre Import / Export",
            settingsTitle: "Paramètres & Configuration"
        },
        ar: {
            navBpa: "حالة التقدم (BPA)",
            navSalaries: "ملف الأجراء",
            navAddSalarie: "+ إضافة ملف أجير",
            navRag: "المستشار القانوني (RAG)",
            navOcr: "العطل والشواهد (OCR)",
            navAbsences: "الغيابات والاعتمادات",
            navStc: "مخالصة نهاية الخدمة (STC)",
            navImportExport: "مركز الاستيراد والتصدير",
            navSettings: "الإعدادات",
            topAddTenant: "+ مؤسسة جديدة",
            userRoleExpert: "خبير الأجور",
            backToMatrix: "العودة لحالة التقدم (BPA)",
            matrixTitle: "حالة التقدم (BPA)",
            legendTitle: "دليل وحالات التقدم :",
            legendAll: "جميع الحالات",
            legendCloture: "معتمد (مغلق)",
            legendEnCalcul: "محسوب (بانتظار الاعتماد)",
            legendEnCours: "قيد المعالجة (إدخال)",
            legendACalculer: "قيد الحساب (متأخر)",
            legendFutur: "مستقبلي (لم يبدأ)",
            painterTitle: "التعيين السريع",
            colName: "المهام / الأجراء",
            taskSection: "المهام العامة للدورة",
            empSection: "أجراء المؤسسة (قاعدة البيانات الحقيقية)",
            tasksBulletins: "كشوف المرتبات",
            tasksVirements: "التحويلات البنكية",
            tasksDeclarations: "التصريحات الاجتماعية (CNAS)",
            btnCalculerMois: "حساب الشهر",
            btnExporter: "تصدير CSV",
            btnJournalPaie: "دفتر الأجور (Journal)",
            searchPlaceholder: "بحث عن أجير أو رقم وظيفي...",
            rangeFrom: "من",
            rangeTo: "إلى",
            presetCurrentYear: "2026",
            preset2Years: "2025 - 2026",
            preset3Years: "2024 - 2026",
            exerciceTitle: (y) => `السنة المالية ${y} — السنة كاملة (12 شهراً)`,
            exerciceBadge: "12 شهراً (01 — 12)",
            taskSectionYear: (y) => `المهام العامة للدورة (${y})`,
            empSectionYear: (y) => `أجراء المؤسسة — قاعدة بيانات حقيقية (${y})`,
            statutClotureLabel: "🟢 معتمد ومغلق",
            statutEnCalculLabel: "🟠 محسوب (بانتظار الاعتماد)",
            statutEnCoursLabel: "🔵 قيد المعالجة",
            statutACalculerLabel: "🔴 قيد الحساب (متأخر)",
            statutFuturLabel: "⚪ مستقبلي (لم يبدأ)",
            statutNoneLabel: "قبل التوظيف",
            noEmployees: "لا يوجد أجراء نشطون في هذا الملف.",
            noMatch: "لا يوجد أجير مطابق للبحث.",
            loadError: "تعذر تحميل المصفوفة من الخادم.",
            confirmBatch: "حساب جميع كشوف شهر",
            doneChanged: "خانة تم تحديثها",
            doneSkipped: "تم تجاوزها",
            invalidRange: "نطاق السنوات غير صالح.",

            // Employees view
            salariesTitle: "ملف الأجراء وعقود العمل",
            salariesSub: "إدارة وتسيير ملفات الأجراء، الأجر القاعدي، المنح، والحسابات البنكية (SQLite).",
            searchEmpPlaceholder: "البحث بالاسم، المعرف، أو المنصب...",
            kpiTotalEmp: "إجمالي الأجراء المسجلين",
            kpiCdi: "عقود غير محددة المدة (CDI)",
            kpiCdd: "عقود أخرى (CDD / ANEM)",
            kpiBaseMass: "كتلة الأجر القاعدي الشهرية",
            thMatricule: "المعرف",
            thNom: "الاسم واللقب",
            thPoste: "الوظيفة والقسم",
            thContrat: "نوع العقد",
            thSalaireBase: "الراتب الأساسي",
            thIep: "منحة الأقدمية IEP",
            thBanque: "الحساب البنكي / RIP",
            thStatut: "الحالة",
            thActions: "إجراءات",
            addEmpTitle: "تسجيل ملف أجير جديد",
            addEmpSub: "بطاقة تعريف الأجير، شروط العقد، الأجر القاعدي والتوطين البنكي (SQLite).",
            btnSaveEmp: "حفظ وتثبيت الأجير",
            ragTitle: "المستشار القانوني والرقابي (الذكاء الاصطناعي التشريعي)",
            ocrTitle: "إدارة الشواهد الطبية والعطل المرضية (OCR)",
            stcTitle: "مخالصة وتصفية نهاية الخدمة (STC)",
            absencesTitle: "تسجيل واعتماد الغيابات والإجازات (Absences & Congés)",
            importExportTitle: "مركز الاستيراد والتصدير والمصادقة (Centre Import / Export)",
            settingsTitle: "الإعدادات العامة والتكوين (Paramètres)"
        }
    };

    const MONTH_FR = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
    const MONTH_AR = ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];

    // -------------------------------- State ---------------------------------
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const nowPeriod = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;

    function loadSavedYears() {
        try {
            const y = JSON.parse(localStorage.getItem('syncra_matrix_years') || 'null');
            if (y && Number.isInteger(y.from) && Number.isInteger(y.to) && y.from <= y.to) return y;
        } catch (e) { /* ignore */ }
        // Default to 2024 to 2026 (3 grids of 12 months)
        return { from: 2024, to: 2026 };
    }

    const S = {
        locale: localStorage.getItem('syncra_lang') || 'fr',
        tenantId: localStorage.getItem('syncra_active_tenant_id') || '',
        tenants: [],
        years: loadSavedYears(),
        data: null,           // response of GET /api/matrix
        error: null,
        filter: 'ALL',
        painter: null,
        query: '',
        selection: new Set(), // "empId|YYYY-MM"
        anchor: null,
        busy: false
    };

    const t = (k) => {
        const dict = I18N[S.locale] || I18N.fr;
        return dict[k] != null ? dict[k] : k;
    };
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const key = (emp, per) => `${emp}|${per}`;
    const monthName = (per) => (S.locale === 'ar' ? MONTH_AR : MONTH_FR)[parseInt(per.slice(5), 10) - 1];

    // ------------------------------ Locale / i18n ----------------------------
    function applyLocaleDirection() {
        document.documentElement.lang = S.locale;
        document.documentElement.dir = (S.locale === 'ar') ? 'rtl' : 'ltr';
        document.querySelectorAll('.locale-btn').forEach((b) =>
            b.classList.toggle('active', b.getAttribute('data-locale') === S.locale));
        document.querySelectorAll('.lang-choice-btn').forEach((b) =>
            b.classList.toggle('active', b.getAttribute('data-lang-val') === S.locale));
        const sel = document.getElementById('payslipLangSelect');
        if (sel) sel.value = (S.locale === 'fr') ? 'fr' : 'ar';
    }

    function translateStatic() {
        document.querySelectorAll('[data-i18n]').forEach((el) => {
            const k = el.getAttribute('data-i18n');
            const v = t(k);
            if (typeof v === 'string') {
                if (el.children.length === 0) {
                    el.textContent = v;
                } else {
                    el.innerText = v;
                }
            }
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
            const k = el.getAttribute('data-i18n-placeholder');
            const v = t(k);
            if (typeof v === 'string') el.placeholder = v;
        });
        document.querySelectorAll('[data-i18n-title]').forEach((el) => {
            const k = el.getAttribute('data-i18n-title');
            const v = t(k);
            if (typeof v === 'string') el.title = v;
        });
        const search = document.getElementById('silaeSearchEmpInput');
        if (search) search.placeholder = t('searchPlaceholder');
        updateCalcButton();
    }

    function setLocale(lang) {
        S.locale = lang;
        localStorage.setItem('syncra_lang', lang);
        applyLocaleDirection();
        translateStatic();
        renderAll();
        if (typeof window.renderEmployeesTable === 'function') {
            window.renderEmployeesTable();
        }
        if (typeof window.renderActivePayslip === 'function') {
            window.renderActivePayslip();
        }
    }

    // ------------------------------ Backend access ---------------------------
    async function api(path, opts) {
        const resp = await fetch(path, opts);
        if (!resp.ok) {
            let detail = `HTTP ${resp.status}`;
            try { const j = await resp.json(); detail = j.detail || detail; } catch (e) { /* ignore */ }
            throw new Error(detail);
        }
        return resp.json();
    }

    async function loadTenants() {
        try {
            let userEmail = '';
            try {
                const s = JSON.parse(localStorage.getItem('syncra_user_session') || sessionStorage.getItem('syncra_user_session') || 'null');
                if (s && s.email) userEmail = s.email;
            } catch (err) { }
            const url = userEmail ? `/api/tenants?email=${encodeURIComponent(userEmail)}` : '/api/tenants';
            const data = await api(url);
            if (Array.isArray(data)) {
                S.tenants = data;
                if (!data.some((x) => x.id === S.tenantId)) {
                    S.tenantId = data.length ? data[0].id : '';
                    localStorage.setItem('syncra_active_tenant_id', S.tenantId);
                }
            }
        } catch (e) {
            console.warn('Silae: /api/tenants failed', e);
        }
        const sel = document.getElementById('silaeTopTenantSelect');
        if (sel) {
            const addLabel = (S.locale === 'ar') ? '➕ إضافة مؤسسة جديدة...' : '➕ Nouvelle entreprise...';
            sel.innerHTML = S.tenants.map((x) =>
                `<option value="${esc(x.id)}" ${x.id === S.tenantId ? 'selected' : ''}>${esc(x.name)} (${esc(x.id)})</option>`).join('') +
                `<option value="__ADD_NEW_TENANT__" style="color:#0284c7;font-weight:700;">${addLabel}</option>`;
        }
    }

    async function refresh() {
        if (!S.tenantId) { S.data = null; renderAll(); return; }
        try {
            const fromStr = `${S.years.from}-01`;
            const toStr = `${S.years.to}-12`;
            const qs = new URLSearchParams({ tenant_id: S.tenantId, from: fromStr, to: toStr });
            S.data = await api(`/api/matrix?${qs}`);
            S.error = null;
        } catch (e) {
            S.data = null;
            S.error = e.message;
        }
        // drop selections that no longer exist
        const valid = new Set();
        (S.data ? S.data.employees : []).forEach((emp) => (S.data.periods || []).forEach((p) => valid.add(key(emp.id, p))));
        S.selection = new Set([...S.selection].filter((k) => valid.has(k)));
        renderAll();
    }

    async function switchTenant(id) {
        if (id === '__ADD_NEW_TENANT__') {
            const sel = document.getElementById('silaeTopTenantSelect');
            if (sel) sel.value = S.tenantId;
            if (typeof window.openAddCompanyModal === 'function') {
                window.openAddCompanyModal();
            }
            return;
        }
        S.tenantId = id;
        S.selection.clear();
        S.anchor = null;
        localStorage.setItem('syncra_active_tenant_id', id);
        if (typeof window.handleTenantSelectionChange === 'function') {
            try { await window.handleTenantSelectionChange(id); } catch (e) { console.warn(e); }
        }
        await refresh();
    }

    // ---------------------------- Year Range Filter --------------------------
    function setYearRange() {
        const f = document.getElementById('silaeYearFrom');
        const to = document.getElementById('silaeYearTo');
        if (!f || !to) return;
        let fy = parseInt(f.value, 10);
        let ty = parseInt(to.value, 10);
        if (isNaN(fy) || isNaN(ty)) return;
        if (fy > ty) {
            ty = fy;
            to.value = ty;
        }
        applyYearRange(fy, ty);
    }

    function applyYearRange(fy, ty) {
        S.years = { from: fy, to: ty };
        localStorage.setItem('syncra_matrix_years', JSON.stringify(S.years));
        syncYearInputs();
        refresh();
    }

    function presetYears(count) {
        const curY = now.getFullYear(); // 2026
        if (count === 1) applyYearRange(curY, curY);
        else if (count === 2) applyYearRange(curY - 1, curY);
        else if (count === 3) applyYearRange(curY - 2, curY);
    }

    function syncYearInputs() {
        const f = document.getElementById('silaeYearFrom');
        const to = document.getElementById('silaeYearTo');
        if (f) f.value = S.years.from;
        if (to) to.value = S.years.to;
        document.querySelectorAll('.preset-yr-btn').forEach((btn) => {
            const p = parseInt(btn.dataset.preset, 10);
            const curY = now.getFullYear();
            let active = false;
            if (p === 1 && S.years.from === curY && S.years.to === curY) active = true;
            else if (p === 2 && S.years.from === (curY - 1) && S.years.to === curY) active = true;
            else if (p === 3 && S.years.from === (curY - 2) && S.years.to === curY) active = true;
            btn.classList.toggle('active', active);
        });
    }

    function getYearList() {
        const list = [];
        for (let y = S.years.from; y <= S.years.to; y++) {
            list.push(y);
        }
        return list;
    }

    // -------------------------------- Rendering ------------------------------
    const CLS = {
        CLOTURE: 'status-cloture',
        EN_CALCUL: 'status-encalcul',
        EN_COURS: 'status-encours',
        A_CALCULER: 'status-acalculer',
        FUTUR: 'status-futur'
    };
    const LABEL = {
        CLOTURE: 'statutClotureLabel',
        EN_CALCUL: 'statutEnCalculLabel',
        EN_COURS: 'statutEnCoursLabel',
        A_CALCULER: 'statutACalculerLabel',
        FUTUR: 'statutFuturLabel',
        NONE: 'statutNoneLabel'
    };

    function visibleEmployees() {
        if (!S.data || !S.data.employees) return [];
        const q = S.query.toLowerCase().trim();
        return S.data.employees.filter((e) => !q ||
            String(e.name).toLowerCase().includes(q) || String(e.id).toLowerCase().includes(q) ||
            String(e.job_title || '').toLowerCase().includes(q));
    }

    function dotHtml(type, id, per, cell, label) {
        const st = (cell && cell.status) || 'FUTUR';
        if (st === 'NONE') return '<td><span class="silae-dot-none" title="' + esc(t('statutNoneLabel')) + '">–</span></td>';
        const dim = S.filter !== 'ALL' && S.filter !== st ? 'dimmed' : (S.filter === st ? 'highlighted' : '');
        const sel = type === 'employee' && S.selection.has(key(id, per)) ? 'selected' : '';
        const net = (cell && cell.net != null) ? ` — Net: ${Number(cell.net).toLocaleString()} DZD` : '';
        const attrs = type === 'employee' ? `data-emp="${esc(id)}" data-period="${per}"` : `data-task="${esc(id)}" data-period="${per}"`;
        return `<td><span class="silae-dot ${CLS[st] || 'status-futur'} ${dim} ${sel}" ${attrs}
                title="${esc(label)} — ${per.slice(5)} (${monthName(per)} ${per.slice(0, 4)}): ${esc(t(LABEL[st]))}${net}"></span></td>`;
    }

    function renderYearCard(year) {
        const cur = S.data ? S.data.current : nowPeriod;
        const months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        const periods = months.map((m) => `${year}-${pad(m)}`);

        // 12 month columns header (01..12 ALWAYS)
        const thCols = periods.map((p) => {
            const isCur = (p === cur);
            const mNum = p.slice(5);
            const mName = monthName(p);
            return `<th class="col-m ${isCur ? 'current-m' : ''}" data-period="${p}" style="cursor:pointer;" title="${esc(mName)} ${year}">${mNum}${isCur ? ' ▼' : ''}</th>`;
        }).join('');

        // Employee rows for this year (Real SQLite Records)
        const emps = visibleEmployees();
        let empHtml = '';
        if (!emps.length) {
            empHtml = `<tr><td colspan="13" style="padding:24px;color:#64748b;text-align:center">${esc(S.data && S.data.employees.length ? t('noMatch') : t('noEmployees'))}</td></tr>`;
        } else {
            empHtml = emps.map((e) => {
                const salary = e.base_salary ? ` | ${Number(e.base_salary).toLocaleString()} DZD` : '';
                const dots = periods.map((p) => {
                    const cell = (e.cells && e.cells[p]) || { status: 'FUTUR' };
                    return dotHtml('employee', e.id, p, cell, e.name);
                }).join('');
                return `<tr data-emp-row="${esc(e.id)}">
                    <td class="cell-name">
                        <span class="silae-matricule-tag">${esc(e.id)}</span><strong>${esc(e.name)}</strong>
                        <span style="font-size:.72rem;color:#64748b;margin-inline-start:6px">(${esc(e.job_title || '')}${salary})</span>
                    </td>
                    ${dots}
                </tr>`;
            }).join('');
        }

        const yearLabel = (typeof t('exerciceTitle') === 'function') ? t('exerciceTitle')(year) : `Exercice ${year} — (12 Mois)`;

        return `
        <div class="silae-year-grid-card" data-year="${year}">
            <div class="silae-year-grid-header">
                <div class="year-grid-title">
                    <i class="fa-solid fa-calendar-days text-primary"></i>
                    <span>${esc(yearLabel)}</span>
                </div>
                <div class="year-grid-badge">
                    <i class="fa-solid fa-clock-rotate-left"></i> <span>${esc(t('exerciceBadge'))}</span>
                </div>
            </div>
            <div class="silae-matrix-scroll-wrap">
                <table class="silae-bpa-table ${S.filter !== 'ALL' ? 'filter-active' : ''}" dir="ltr">
                    <thead>
                        <tr>
                            <th class="col-name" style="text-align:left">${esc(t('colName'))}</th>
                            ${thCols}
                        </tr>
                    </thead>
                    <tbody>
                        ${empHtml}
                    </tbody>
                </table>
            </div>
        </div>`;
    }

    function renderBody() {
        const container = document.getElementById('silaeYearGridsContainer');
        if (!container) return;

        if (!S.data) {
            container.innerHTML = `<div class="silae-year-grid-card" style="padding:36px;color:#b91c1c;text-align:center;font-weight:700">
                <i class="fa-solid fa-triangle-exclamation" style="font-size:1.5rem;margin-bottom:8px"></i><br>
                ${esc(t('loadError'))}${S.error ? ' — ' + esc(S.error) : ''}
            </div>`;
            return;
        }

        const years = getYearList();
        container.innerHTML = years.map((y) => renderYearCard(y)).join('');
        container.classList.toggle('filter-active', S.filter !== 'ALL');
        container.classList.toggle('painting', !!S.painter);
        refreshSelectionStyles();
    }

    function renderLegend() {
        const c = { CLOTURE: 0, EN_CALCUL: 0, EN_COURS: 0, A_CALCULER: 0, FUTUR: 0 };
        if (S.data && S.data.employees) {
            S.data.employees.forEach((e) => Object.values(e.cells || {}).forEach((cell) => {
                if (cell && c[cell.status] != null) c[cell.status]++;
            }));
        }
        const total = Object.values(c).reduce((a, b) => a + b, 0);
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        set('silaeCountAll', total);
        set('silaeCountCloture', c.CLOTURE);
        set('silaeCountEnCalcul', c.EN_CALCUL);
        set('silaeCountEnCours', c.EN_COURS);
        set('silaeCountACalculer', c.A_CALCULER);
        set('silaeCountFutur', c.FUTUR);
        document.querySelectorAll('.legend-filter-btn').forEach((b) =>
            b.classList.toggle('active', b.getAttribute('data-status') === S.filter));
    }

    function updateCalcButton() {
        const span = document.querySelector('[data-i18n="btnCalculerMois"]');
        const p = batchPeriod();
        if (span) span.textContent = `${t('btnCalculerMois')} ${p ? p.slice(5) : ''}`.trim();
    }

    function updateMatrixKpiBar(targetPeriod) {
        const p = targetPeriod || batchPeriod() || (S.data && S.data.current) || nowPeriod;
        const emps = (S.data && S.data.employees) || [];

        let cdiCount = 0, cddCount = 0;
        let totGross = 0, totCnas = 0, totIrg = 0, totNet = 0;

        emps.forEach((e) => {
            const ct = (e.contract_type || 'CDI').toUpperCase();
            if (ct.includes('CDD')) cddCount++; else cdiCount++;

            const cell = (e.cells && e.cells[p]) || null;
            if (cell && cell.gross != null) {
                const g = Number(cell.gross) || 0;
                const ce = Number(cell.cnas_employee) || (g * 0.09);
                const cp = g * 0.25; // CNAS patronale 25%
                totGross += g;
                totCnas += (ce + cp);
                totIrg += Number(cell.irg) || 0;
                totNet += Number(cell.net) || 0;
            } else {
                const b = Number(e.base_salary) || 0;
                const ce = b * 0.09;
                const cp = b * 0.25;
                const irg = (typeof window.calculateAlgerianIRG === 'function') ? window.calculateAlgerianIRG(Math.max(0, b - ce)) : 0;
                const net = Math.max(0, b - ce - irg);
                totGross += b;
                totCnas += (ce + cp);
                totIrg += irg;
                totNet += net;
            }
        });

        const fmt = (n) => (n || 0).toLocaleString(S.locale === 'ar' ? 'ar-DZ' : 'fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' DZD';
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

        const empLabel = (S.locale === 'ar') ? `${emps.length} أجراء` : `${emps.length} Salariés`;
        const contractsLabel = (S.locale === 'ar') ? `(${cdiCount} دائم / ${cddCount} مؤقت)` : `(${cdiCount} CDI / ${cddCount} CDD)`;
        const mName = p ? monthName(p) : '';
        const yNum = p ? p.slice(0, 4) : '';
        const cycleLabel = (S.locale === 'ar') ? `دورة: ${mName} ${yNum}` : `Période: ${mName} ${yNum}`;

        setEl('kpiActiveEmployees', empLabel);
        setEl('kpiContractsDetail', contractsLabel);
        setEl('kpiTotalGross', fmt(totGross));
        setEl('kpiGrossSub', cycleLabel);
        setEl('kpiTotalCnas', fmt(totCnas));
        setEl('kpiTotalIrg', fmt(totIrg));
        setEl('kpiTotalNet', fmt(totNet));
    }

    function renderAll() {
        syncYearInputs();
        renderBody();
        renderLegend();
        updateCalcButton();
        updateMatrixKpiBar();
    }

    function refreshSelectionStyles() {
        document.querySelectorAll('.silae-dot[data-emp]').forEach((d) =>
            d.classList.toggle('selected', S.selection.has(key(d.dataset.emp, d.dataset.period))));
    }

    // ------------------------------- Selection -------------------------------
    function getCell(emp, per) {
        const e = S.data && S.data.employees && S.data.employees.find((x) => x.id === emp);
        return e ? (e.cells[per] || null) : null;
    }

    function getSelection() {
        return [...S.selection].map((k) => {
            const [emp, per] = k.split('|');
            const cell = getCell(emp, per);
            return { emp, period: per, status: cell ? cell.status : 'NONE' };
        });
    }

    function rangeSelect(a, b) {
        if (!S.data || !S.data.periods) return;
        const emps = visibleEmployees().map((e) => e.id);
        const per = S.data.periods;
        const [r1, r2] = [emps.indexOf(a.emp), emps.indexOf(b.emp)].sort((x, y) => x - y);
        const [c1, c2] = [per.indexOf(a.period), per.indexOf(b.period)].sort((x, y) => x - y);
        if (r1 === -1 || r2 === -1 || c1 === -1 || c2 === -1) return;
        S.selection = new Set();
        for (let r = r1; r <= r2; r++) {
            for (let c = c1; c <= c2; c++) {
                const cell = getCell(emps[r], per[c]);
                if (cell && cell.status !== 'NONE') S.selection.add(key(emps[r], per[c]));
            }
        }
    }

    function selectCellForMenu(emp, per) {
        if (!S.selection.has(key(emp, per))) {
            S.selection = new Set([key(emp, per)]);
            S.anchor = { emp, period: per };
            refreshSelectionStyles();
        }
    }

    function onContainerClick(e) {
        const th = e.target.closest('th.col-m[data-period]');
        if (th) {
            updateMatrixKpiBar(th.dataset.period);
            return;
        }
        const d = e.target.closest('.silae-dot[data-emp], .silae-dot[data-task]');
        if (!d) return;
        const emp = d.dataset.emp, per = d.dataset.period;
        if (per) updateMatrixKpiBar(per);
        if (!emp) return;
        if (S.painter) {
            const cells = S.selection.has(key(emp, per)) ? getSelection() : [{ emp, period: per }];
            paint(cells, S.painter);
            return;
        }
        if (e.shiftKey && S.anchor) rangeSelect(S.anchor, { emp, period: per });
        else if (e.ctrlKey || e.metaKey) {
            const k = key(emp, per);
            if (S.selection.has(k)) S.selection.delete(k); else S.selection.add(k);
            S.anchor = { emp, period: per };
        } else {
            S.selection = new Set([key(emp, per)]);
            S.anchor = { emp, period: per };
        }
        refreshSelectionStyles();
    }

    function onContainerDblClick(e) {
        const d = e.target.closest('.silae-dot[data-emp]');
        if (d && typeof window.viewEmployeePayslip === 'function') {
            window.viewEmployeePayslip(d.dataset.emp, d.dataset.period);
        }
    }

    // ------------------------------ Write actions ----------------------------
    function toast(msg, kind) {
        let el = document.getElementById('silaeToast');
        if (!el) { el = document.createElement('div'); el.id = 'silaeToast'; document.body.appendChild(el); }
        el.className = `silae-toast ${kind || 'ok'} show`;
        el.textContent = msg;
        clearTimeout(el._t);
        el._t = setTimeout(() => el.classList.remove('show'), 3800);
    }

    async function runAction(kind, cells, status) {
        if (!cells || !cells.length || S.busy) return null;
        S.busy = true;
        try {
            const byPeriod = {};
            cells.forEach((c) => { (byPeriod[c.period] = byPeriod[c.period] || new Set()).add(c.emp); });
            const results = await Promise.all(Object.entries(byPeriod).map(([period, emps]) =>
                api(`/api/matrix/${kind}`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id: S.tenantId, employee_ids: [...emps], periods: [period], status: status || null })
                })));
            const changed = results.reduce((n, r) => n + r.changed.length, 0);
            const skipped = results.flatMap((r) => r.skipped);
            await refresh();
            let msg = `${changed} ${t('doneChanged')}`;
            if (skipped.length) msg += ` · ${skipped.length} ${t('doneSkipped')} (${skipped[0].reason})`;
            toast(msg, changed ? 'ok' : 'error');
            return { changed, skipped };
        } catch (e) {
            toast(e.message, 'error');
            return null;
        } finally {
            S.busy = false;
        }
    }

    function paint(cells, status) {
        if (status === 'EN_CALCUL') return runAction('calculate', cells);
        if (status === 'CLOTURE') return runAction('close', cells);
        toast('إعادة فتح كشوف المرتبات غير مسموحة نهائياً / Réouverture strictement interdite', 'error');
        return null;
    }

    function batchPeriod() {
        if (!S.data || !S.data.periods || !S.data.periods.length) return null;
        const cur = S.data.current;
        if (S.data.periods.includes(cur)) return cur;
        const past = S.data.periods.filter((p) => p <= cur);
        return past.length ? past[past.length - 1] : null;
    }

    async function batchRecalculateMonth() {
        const p = batchPeriod();
        if (!p || !S.data || !S.data.employees) return;
        if (!confirm(`${t('confirmBatch')} ${p.slice(5)}/${p.slice(0, 4)} ?`)) return;
        await runAction('calculate', S.data.employees.map((e) => ({ emp: e.id, period: p })));
    }

    function exportCsv() {
        if (!S.data || !S.data.periods || !S.data.employees) return;
        const q = (v) => `"${String(v == null ? '' : v).replace(/"/g, '""')}"`;
        let csv = ['Matricule', 'Nom', 'Emploi', 'Salaire_Base', ...S.data.periods].map(q).join(',') + '\n';
        S.data.employees.forEach((e) => {
            csv += [e.id, e.name, e.job_title, e.base_salary, ...S.data.periods.map((p) => (e.cells[p] || {}).status)].map(q).join(',') + '\n';
        });
        const url = URL.createObjectURL(new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = `SYNCRA_Etat_Avancement_${S.tenantId}_${S.years.from}_${S.years.to}.csv`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
    }

    function filterStatus(st) {
        S.filter = (S.filter === st) ? 'ALL' : st;
        renderBody();
        renderLegend();
    }

    function setPainterStatus(st) {
        S.painter = S.painter === st ? null : st;
        document.querySelectorAll('.painter-btn').forEach((b) =>
            b.classList.toggle('active', b.getAttribute('data-paint-status') === S.painter));
        const container = document.getElementById('silaeYearGridsContainer');
        if (container) container.classList.toggle('painting', !!S.painter);
    }

    // --------------------------------- Init ----------------------------------
    let wired = false;
    async function init() {
        applyLocaleDirection();
        translateStatic();
        syncYearInputs();
        if (!wired) {
            wired = true;
            const container = document.getElementById('silaeYearGridsContainer');
            if (container) {
                container.addEventListener('click', onContainerClick);
                container.addEventListener('dblclick', onContainerDblClick);
            }
            document.addEventListener('click', (e) => {
                if (!e.target.closest('#silaeYearGridsContainer') &&
                    !e.target.closest('.silae-context-menu') &&
                    !e.target.closest('.silae-matrix-legend-toolbar') &&
                    !e.target.closest('.silae-matrix-header-bar') &&
                    S.selection.size) {
                    S.selection.clear();
                    refreshSelectionStyles();
                }
            });
        }
        await loadTenants();
        await refresh();
    }

    window.SilaeEngine = {
        init, setLocale, switchTenant, loadTenants, filterStatus, setPainterStatus, setYearRange, presetYears,
        batchRecalculateMonth, exportCsv, refresh, runAction, toast, getSelection, getCell,
        selectCellForMenu, t, searchEmployees: (q) => { S.query = q || ''; renderBody(); },
        updateMatrixKpiBar,
        getLocale: () => S.locale, getPeriods: () => (S.data ? S.data.periods : []),
        getTenantId: () => S.tenantId,
        getEmployee: (id) => (S.data && S.data.employees && S.data.employees.find((e) => e.id === id)) || null,
        getEmployees: () => (S.data && S.data.employees) || []
    };

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else setTimeout(init, 200);
})(window);
