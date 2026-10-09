/**
 * ==========================================================================
 * SILAE MATRIX CONTEXT MENU (right-click on a bubble or table cell)
 * Module: js/silae-context-menu.js
 * 
 * Only wires genuine features that really exist in the codebase:
 *   - Accéder au bulletin (viewEmployeePayslip)
 *   - Imprimer le bulletin (print)
 *   - Calculer le bulletin (/api/matrix/calculate)
 *   - Clôturer le bulletin (/api/matrix/close)
 *   - Rouvrir le bulletin (/api/matrix/reopen)
 *   - Ordre de virement (openBankTransferModal)
 *   - Déclaration CNAS (openCnasReportModal)
 *   - Déclaration annuelle DAS (openDasModal)
 *   - État IRG G50 (openIrgReportModal)
 *   - Attestation de travail et de salaire ATS (openAtsModal)
 *   - Supprimer le salarié (deleteEmployee)
 * ==========================================================================
 */
(function (window) {
    'use strict';

    const L = {
        fr: {
            bulletin: 'Bulletin de paie',
            access: 'Accéder au bulletin',
            view: 'Voir le bulletin',
            print: 'Imprimer le bulletin',
            calc: (n) => n > 1 ? `Calculer ${n} bulletins` : 'Calculer le bulletin',
            close: (n) => n > 1 ? `Clôturer ${n} bulletins (Valider)` : 'Clôturer le bulletin (Valider)',
            reopen: (n) => n > 1 ? `Rouvrir ${n} bulletins (Saisie)` : 'Rouvrir le bulletin (Saisie)',
            del: 'Supprimer le salarié',
            recap: 'Journal de paie & Récapitulatifs',
            bank: 'Ordre de virement bancaire',
            cnas: 'Déclaration sociale (CNAS)',
            das: 'Déclaration annuelle (DAS)',
            irg: 'État IRG (G50)',
            ats: 'Attestation de travail et de salaire (ATS)',
            variables: 'Saisie des variables du mois (EVP)',
            selected: (n) => `${n} bulletins sélectionnés`,
            confirmDelete: 'Supprimer définitivement ce salarié ?'
        },
        ar: {
            bulletin: 'كشف الراتب',
            access: 'الولوج إلى كشف الراتب (Accéder)',
            view: 'عرض كشف الراتب (Voir)',
            print: 'طباعة كشف الراتب',
            calc: (n) => n > 1 ? `حساب ${n} كشوف` : 'حساب كشف الراتب',
            close: (n) => n > 1 ? `اعتماد وإغلاق ${n} كشوف` : 'اعتماد وإغلاق كشف الراتب',
            reopen: (n) => n > 1 ? `إعادة فتح ${n} كشوف` : 'إعادة فتح كشف الراتب (Saisie)',
            del: 'حذف الأجير',
            recap: 'دفتر الأجور والملخصات الرسمية',
            bank: 'أمر التحويل البنكي',
            cnas: 'التصريح الاجتماعي (CNAS)',
            das: 'التصريح السنوي بالأجور (DAS)',
            irg: 'كشف الضريبة على الدخل (IRG G50)',
            ats: 'شهادة العمل والأجر (ATS)',
            variables: 'إدخال المتغيرات الشهرية (EVP)',
            selected: (n) => `${n} كشوف محددة`,
            confirmDelete: 'هل تريد حذف هذا الأجير نهائياً؟'
        }
    };

    const CALC_OK = ['A_CALCULER', 'EN_COURS', 'EN_CALCUL'];

    const E = () => window.SilaeEngine;
    const lbl = () => L[E().getLocale()] || L.fr;
    const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    function closeMenu() {
        const m = document.querySelector('.silae-context-menu');
        if (m) m.remove();
    }

    function guard(fn, name) {
        return () => {
            if (typeof window[name] === 'function') fn();
            else E().toast(`${name}: indisponible`, 'error');
        };
    }

    function buildItems(cells) {
        const l = lbl();
        const n = cells.length;
        const single = n === 1;
        const calcCells = cells.filter((c) => CALC_OK.includes(c.status));

        const items = [];
        if (single) {
            items.push({
                icon: 'fa-arrow-up-right-from-square',
                text: l.access,
                disabled: false,
                run: guard(() => window.viewEmployeePayslip(cells[0].emp, cells[0].period), 'viewEmployeePayslip')
            });
            items.push({
                icon: 'fa-pen-to-square',
                text: l.variables,
                disabled: false,
                run: guard(() => window.openVariablesModal(cells[0].emp, cells[0].period), 'openVariablesModal')
            });
            items.push({
                icon: 'fa-file-invoice',
                text: l.view,
                disabled: false,
                run: guard(() => window.viewEmployeePayslip(cells[0].emp, cells[0].period), 'viewEmployeePayslip')
            });
            items.push({
                icon: 'fa-print',
                text: l.print,
                disabled: false,
                run: guard(() => {
                    window.viewEmployeePayslip(cells[0].emp, cells[0].period);
                    setTimeout(() => window.print(), 500);
                }, 'viewEmployeePayslip')
            });
            items.push({ sep: true });
        }
        items.push({
            icon: 'fa-calculator',
            text: l.calc(calcCells.length || n),
            disabled: !calcCells.length,
            run: () => E().runAction('calculate', calcCells)
        });
        items.push({
            icon: 'fa-lock',
            text: l.close(calcCells.length || n),
            disabled: !calcCells.length,
            run: () => E().runAction('close', calcCells)
        });
        items.push({ sep: true });
        items.push({ header: l.recap });
        items.push({
            icon: 'fa-book-bookmark',
            text: (E().getLocale() === 'ar' ? 'دفتر الأجور الشامل (Journal de Paie)' : 'Journal de paie (État préparatoire)'),
            run: guard(() => (window.openJournalPaieScreen ? window.openJournalPaieScreen(cells[0] ? cells[0].period : null, cells[0] ? cells[0].emp : null) : null), 'openJournalPaieScreen')
        });
        items.push({
            icon: 'fa-money-bill-transfer',
            text: l.bank,
            run: guard(() => (window.openVirementScreen ? window.openVirementScreen(cells[0] ? cells[0].period : null, cells[0] ? cells[0].emp : null) : window.openBankTransferModal()), 'openVirementScreen')
        });
        items.push({
            icon: 'fa-building-shield',
            text: l.cnas,
            run: guard(() => (window.openCnasScreen ? window.openCnasScreen(cells[0] ? cells[0].period : null, cells[0] ? cells[0].emp : null) : window.openCnasReportModal()), 'openCnasScreen')
        });
        items.push({
            icon: 'fa-table-list',
            text: l.das,
            run: guard(() => (window.openDasScreen ? window.openDasScreen(cells[0] ? cells[0].period : null, cells[0] ? cells[0].emp : null) : window.openDasModal()), 'openDasScreen')
        });
        items.push({
            icon: 'fa-percent',
            text: l.irg,
            run: guard(() => (window.openIrgScreen ? window.openIrgScreen(cells[0] ? cells[0].period : null, cells[0] ? cells[0].emp : null) : window.openIrgReportModal()), 'openIrgScreen')
        });
        if (single) {
            items.push({
                icon: 'fa-file-signature',
                text: l.ats,
                run: guard(() => (window.openAtsScreen ? window.openAtsScreen(cells[0].emp) : window.openAtsModal()), 'openAtsScreen')
            });
            items.push({ sep: true });
            items.push({
                icon: 'fa-user-xmark',
                text: l.del,
                danger: true,
                run: guard(() => window.deleteEmployee(cells[0].emp), 'deleteEmployee')
            });
        }
        return items;
    }

    function openMenu(x, y, cells) {
        closeMenu();
        const l = lbl();
        const eng = E();
        const first = cells[0];
        const empObj = (eng.getEmployee && eng.getEmployee(first.emp)) ||
                       (window.employees && window.employees.find((e) => e.id === first.emp));
        const empName = empObj ? ` · ${empObj.name}` : '';
        const title = cells.length === 1
            ? `${first.emp}${empName} (${first.period.slice(5)}/${first.period.slice(0, 4)})`
            : l.selected(cells.length);

        const menu = document.createElement('div');
        menu.className = 'silae-context-menu';
        menu.innerHTML = `<div class="ctx-title">${esc(title)}</div>`;

        buildItems(cells).forEach((it) => {
            if (it.sep) {
                menu.insertAdjacentHTML('beforeend', '<div class="ctx-sep"></div>');
                return;
            }
            if (it.header) {
                menu.insertAdjacentHTML('beforeend', `<div class="ctx-header">${esc(it.header)}</div>`);
                return;
            }
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `ctx-item${it.disabled ? ' disabled' : ''}${it.danger ? ' danger' : ''}`;
            btn.innerHTML = `<i class="fa-solid ${it.icon}"></i><span>${esc(it.text)}</span>`;
            if (!it.disabled) {
                btn.addEventListener('click', () => {
                    if (it.danger && !confirm(l.confirmDelete)) return;
                    closeMenu();
                    it.run();
                });
            }
            menu.appendChild(btn);
        });

        document.body.appendChild(menu);
        const r = menu.getBoundingClientRect();
        menu.style.left = `${Math.max(6, Math.min(x, window.innerWidth - r.width - 8))}px`;
        menu.style.top = `${Math.max(6, Math.min(y, window.innerHeight - r.height - 8))}px`;
        menu.classList.toggle('rtl', eng.getLocale() === 'ar');
    }

    document.addEventListener('contextmenu', (e) => {
        const dot = e.target.closest('.silae-dot[data-emp]') ||
                    (e.target.closest('td') ? e.target.closest('td').querySelector('.silae-dot[data-emp]') : null);
        if (!dot) return;
        e.preventDefault();
        e.stopPropagation();
        if (!dot.dataset.emp) { closeMenu(); return; }
        E().selectCellForMenu(dot.dataset.emp, dot.dataset.period);
        openMenu(e.clientX, e.clientY, E().getSelection());
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.silae-context-menu')) closeMenu();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMenu();
    });
    window.addEventListener('scroll', closeMenu, true);
    window.addEventListener('resize', closeMenu);
})(window);
