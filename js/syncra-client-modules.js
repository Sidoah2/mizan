/**
 * SYNCRA Enterprise SaaS - Client Modules Suite
 * Implements functional requirements from syncra_md_files_1:
 * - Absences & Manager Approvals (Saisie et validation des congés)
 * - Hours & Overtime Timesheets (Saisie des heures, HS 50%, HS 100%, Nuit)
 * - Occupational Medical Visits (Médecine du travail et visites médicales)
 * - Reusable Job Templates & 1-Click Hire (Modèles collaborateurs)
 * - Annual Performance Evaluations (Entretiens annuels d'évaluation)
 * - Enterprise Import & Export Center (Salariés, Variables EVP, Paramètres)
 * - Guided Exit Wizard & STC Legal Settlements (Assistant de sortie)
 */

    // Current tenant identifier resolution (Multi-Tenant Isolation)
    function getActiveTenantId() {
        // 1. Check window.SilaeEngine if available
        if (window.SilaeEngine && typeof window.SilaeEngine.getTenantId === 'function') {
            const sid = window.SilaeEngine.getTenantId();
            if (sid && sid !== '__ADD_NEW_TENANT__') return sid;
        }
        // 2. Check the active select dropdown in the top bar
        const topSel = document.getElementById('silaeTopTenantSelect') || document.getElementById('companySelector');
        if (topSel && topSel.value && topSel.value !== '__ADD_NEW_TENANT__') {
            return topSel.value;
        }
        // 3. Check localStorage
        const stored = localStorage.getItem('syncra_active_tenant_id');
        if (stored && stored !== '__ADD_NEW_TENANT__') return stored;
        // 4. Check global variable
        if (window.currentTenantId && window.currentTenantId !== '__ADD_NEW_TENANT__') return window.currentTenantId;
        return '';
    }

    // Helper Toast / Notification
    function showNotification(msg, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `syncra-toast syncra-toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            left: 24px;
            z-index: 10000;
            padding: 14px 22px;
            background: ${type === 'success' ? '#16a34a' : type === 'error' ? '#dc2626' : '#2563eb'};
            color: white;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25);
            font-weight: 700;
            font-size: 0.92rem;
            display: flex;
            align-items: center;
            gap: 10px;
            direction: rtl;
            animation: slideUp 0.3s ease forwards;
        `;
        const icon = type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info';
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.4s ease';
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }

    // =========================================================================
    // 1. ABSENCES & APPROVAL WORKFLOW
    // =========================================================================
    async function loadAbsences(filterStatus = 'ALL') {
        const tenantId = getActiveTenantId();
        const tbody = document.getElementById('absencesTableBody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin text-primary"></i> جاري تحميل سجل الغيابات...</td></tr>';

        try {
            const url = `/api/absences?tenant_id=${encodeURIComponent(tenantId)}${filterStatus !== 'ALL' ? `&status=${filterStatus}` : ''}`;
            const res = await fetch(url);
            const data = await res.json();

            if (!data.success || !data.absences || data.absences.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 32px; color: var(--text-muted);"><i class="fa-regular fa-folder-open" style="font-size: 2rem; margin-bottom: 8px; display: block;"></i>لا توجد طلبات غياب مسجلة لهذا الحساب حالياً</td></tr>';
                updateAbsenceCounters(0, 0, 0, 0);
                return;
            }

            const absences = data.absences;
            let pendingCount = 0;
            let approvedCount = 0;
            let totalDays = 0;

            let html = '';
            absences.forEach(abs => {
                if (abs.status === 'PENDING') pendingCount++;
                if (abs.status === 'APPROVED') approvedCount++;
                totalDays += parseFloat(abs.days_count || 0);

                const statusBadge = getAbsenceStatusBadge(abs.status);
                const typeBadge = getAbsenceTypeBadge(abs.type);

                html += `
                    <tr>
                        <td>
                            <strong style="color: var(--text-primary); display: block;">${abs.employee_name || abs.employee_id}</strong>
                            <small style="color: var(--text-muted);">${abs.job_title || ''} • ${abs.department || ''}</small>
                        </td>
                        <td>${typeBadge}</td>
                        <td dir="ltr" style="font-family: var(--font-mono); font-size: 0.88rem;">${abs.start_date}</td>
                        <td dir="ltr" style="font-family: var(--font-mono); font-size: 0.88rem;">${abs.end_date}</td>
                        <td><strong style="color: var(--primary);">${abs.days_count}</strong> يوم</td>
                        <td><span style="font-size: 0.85rem; color: var(--text-secondary);">${abs.reason || '-'}</span></td>
                        <td>${statusBadge}</td>
                        <td>
                            <div style="display: flex; gap: 6px; align-items: center;">
                                ${abs.status === 'PENDING' ? `
                                    <button class="btn btn-sm btn-success" onclick="SyncraModules.approveAbsence('${abs.id}')" title="اعتماد فوري">
                                        <i class="fa-solid fa-check"></i> اعتماد
                                    </button>
                                    <button class="btn btn-sm btn-danger" onclick="SyncraModules.rejectAbsence('${abs.id}')" title="رفض">
                                        <i class="fa-solid fa-xmark"></i> رفض
                                    </button>
                                ` : ''}
                                ${abs.status === 'APPROVED' ? `
                                    <button class="btn btn-sm btn-secondary" onclick="SyncraModules.requestCancelAbsence('${abs.id}')" title="طلب إلغاء الغياب">
                                        <i class="fa-solid fa-rotate-left"></i> إلغاء
                                    </button>
                                ` : ''}
                                ${['PENDING', 'CANCEL_REQUESTED', 'REJECTED'].includes(abs.status) ? `
                                    <button class="btn btn-sm btn-danger" onclick="SyncraModules.deleteAbsence('${abs.id}')" title="حذف القيد">
                                        <i class="fa-solid fa-trash-can"></i>
                                    </button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
            updateAbsenceCounters(absences.length, pendingCount, approvedCount, totalDays);

        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger); padding: 20px;">خطأ في الاتصال: ${err.message}</td></tr>`;
        }
    }

    function updateAbsenceCounters(total, pending, approved, days) {
        const elTotal = document.getElementById('absCountTotal');
        const elPending = document.getElementById('absCountPending');
        const elApproved = document.getElementById('absCountApproved');
        const elDays = document.getElementById('absCountDays');
        if (elTotal) elTotal.innerText = total;
        if (elPending) elPending.innerText = pending;
        if (elApproved) elApproved.innerText = approved;
        if (elDays) elDays.innerText = days.toFixed(1);

        // Update nav badge
        const navBadge = document.getElementById('navAbsencesPendingBadge');
        if (navBadge) {
            navBadge.innerText = pending;
            navBadge.style.display = pending > 0 ? 'inline-block' : 'none';
        }
    }

    function getAbsenceTypeBadge(type) {
        const types = {
            'ANNUAL_LEAVE': { label: 'عطلة سنوية', bg: 'rgba(37, 99, 235, 0.12)', color: '#2563eb' },
            'SICK': { label: 'عطلة مرضية', bg: 'rgba(239, 68, 68, 0.12)', color: '#dc2626' },
            'MATERNITY': { label: 'عطلة أمومة', bg: 'rgba(236, 72, 153, 0.12)', color: '#db2777' },
            'FAMILY_EVENT': { label: 'مناسبة عائلية', bg: 'rgba(13, 148, 136, 0.12)', color: '#0d9488' },
            'UNPAID': { label: 'غياب غير مدفوع', bg: 'rgba(217, 119, 6, 0.12)', color: '#d97706' },
            'RECOVERY': { label: 'استرجاع ساعات', bg: 'rgba(99, 102, 241, 0.12)', color: '#4f46e5' }
        };
        const t = types[type] || { label: type || 'غياب', bg: 'rgba(100, 116, 139, 0.12)', color: '#475569' };
        return `<span style="background: ${t.bg}; color: ${t.color}; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 0.8rem;">${t.label}</span>`;
    }

    function getAbsenceStatusBadge(status) {
        if (status === 'APPROVED') {
            return '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> معتمد</span>';
        } else if (status === 'PENDING') {
            return '<span class="badge badge-warning"><i class="fa-solid fa-clock"></i> في الانتظار</span>';
        } else if (status === 'REJECTED') {
            return '<span class="badge badge-danger"><i class="fa-solid fa-ban"></i> مرفوض</span>';
        } else if (status === 'CANCEL_REQUESTED') {
            return '<span class="badge badge-info"><i class="fa-solid fa-arrow-rotate-left"></i> طلب إلغاء</span>';
        }
        return `<span class="badge">${status}</span>`;
    }

    function openNewAbsenceModal() {
        populateEmployeeSelectOptions('newAbsEmployeeSelect');
        const modal = document.getElementById('modalNewAbsence');
        if (modal) modal.style.display = 'flex';
    }

    function closeNewAbsenceModal() {
        const modal = document.getElementById('modalNewAbsence');
        if (modal) modal.style.display = 'none';
    }

    async function submitNewAbsence(e) {
        if (e) e.preventDefault();
        const tenantId = getActiveTenantId();
        const empId = document.getElementById('newAbsEmployeeSelect').value;
        const type = document.getElementById('newAbsTypeSelect').value;
        const start = document.getElementById('newAbsStartDate').value;
        const end = document.getElementById('newAbsEndDate').value;
        const days = parseFloat(document.getElementById('newAbsDaysCount').value || 1.0);
        const reason = document.getElementById('newAbsReason').value;

        if (!empId || !start || !end) {
            alert('يرجى ملء جميع الحقول الإلزامية');
            return;
        }

        try {
            const res = await fetch('/api/absences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    employee_id: empId,
                    type: type,
                    start_date: start,
                    end_date: end,
                    days_count: days,
                    reason: reason
                })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                closeNewAbsenceModal();
                loadAbsences();
            } else {
                alert(data.message || 'خطأ أثناء تسجيل الغياب');
            }
        } catch (err) {
            alert('فشل الاتصال بالخادم: ' + err.message);
        }
    }

    async function approveAbsence(absId) {
        if (!confirm('هل أنت متأكد من اعتماد طلب الغياب هذا؟')) return;
        try {
            const res = await fetch(`/api/absences/${absId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manager_name: 'مسؤول الموارد البشرية' })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                loadAbsences();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function rejectAbsence(absId) {
        if (!confirm('هل أنت متأكد من رفض طلب الغياب؟')) return;
        try {
            const res = await fetch(`/api/absences/${absId}/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manager_name: 'مسؤول الموارد البشرية' })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message, 'error');
                loadAbsences();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function requestCancelAbsence(absId) {
        if (!confirm('تقديم طلب لإلغاء هذا الغياب المعتمد مسبقاً؟')) return;
        try {
            const res = await fetch(`/api/absences/${absId}/request-cancel`, { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message, 'info');
                loadAbsences();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function deleteAbsence(absId) {
        if (!confirm('حذف هذا القيد نهائياً من السجلات؟')) return;
        try {
            const res = await fetch(`/api/absences/${absId}`, { method: 'DELETE' });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                loadAbsences();
            } else {
                alert(data.detail || 'تعذر الحذف');
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function bulkApproveAllPending() {
        const tenantId = getActiveTenantId();
        try {
            const res = await fetch(`/api/absences?tenant_id=${encodeURIComponent(tenantId)}&status=PENDING`);
            const data = await res.json();
            if (!data.success || !data.absences || data.absences.length === 0) {
                alert('لا توجد طلبات معلقة للاعتماد');
                return;
            }
            const ids = data.absences.map(a => a.id);
            if (!confirm(`هل أنت متأكد من الاعتماد الجماعي لـ ${ids.length} طلب غياب؟`)) return;

            const resBulk = await fetch('/api/absences/bulk-approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: ids, manager_name: 'المدير العام' })
            });
            const resData = await resBulk.json();
            if (resData.success) {
                showNotification(resData.message);
                loadAbsences();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    // (Sections 2, 3, 4 removed: Hours, Medical Visits, Job Templates)
    async function loadHoursGrid() { return; }
    function recalculateRowOvertime() { return; }
    async function saveSingleEmployeeHours() { return; }
    async function saveAllHours() { return; }
    function downloadHoursTemplateCSV() { return; }
    async function loadMedicalVisits() { return; }
    function openNewMedicalModal() { return; }
    function closeNewMedicalModal() { return; }
    async function submitNewMedicalVisit() { return; }
    async function markVisitCompleted() { return; }
    async function loadJobTemplates() { return; }
    function applyJobTemplate() { return; }

    // =========================================================================
    // 5. GUIDED EXIT WIZARD & STC (SOLDE DE TOUT COMPTE)
    // =========================================================================
    async function triggerExitWizardCalculate() {
        const tenantId = getActiveTenantId();
        const empId = document.getElementById('wizardEmpSelect')?.value;
        const reason = document.getElementById('wizardReasonSelect')?.value || 'استقالة';
        const date = document.getElementById('wizardDate')?.value || new Date().toISOString().split('T')[0];
        const noticeMonths = parseInt(document.getElementById('wizardNoticeMonths')?.value || 1);
        const noticeStatus = document.getElementById('wizardNoticeStatus')?.value || 'WORKED';
        const leaveDays = parseFloat(document.getElementById('wizardLeaveDays')?.value || 0.0);

        if (!empId) {
            alert('يرجى اختيار الأجير المغادر');
            return;
        }

        try {
            const res = await fetch('/api/exit-wizard/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    employee_id: empId,
                    reason: reason,
                    departure_date: date,
                    notice_period_months: noticeMonths,
                    notice_paid_or_worked: noticeStatus,
                    remaining_leave_days: leaveDays
                })
            });
            const data = await res.json();
            if (data.success) {
                const c = data.calculation;
                document.getElementById('wzdLeaveIndemnity').innerText = c.leave_indemnity.toLocaleString() + ' دج';
                document.getElementById('wzdNoticeIndemnity').innerText = c.notice_indemnity.toLocaleString() + ' دج';
                document.getElementById('wzdSeniorityIndemnity').innerText = c.seniority_indemnity.toLocaleString() + ' دج';
                document.getElementById('wzdStcBrut').innerText = c.stc_brut.toLocaleString() + ' دج';
                document.getElementById('wzdCnasDeduction').innerText = '-' + c.cnas_deduction.toLocaleString() + ' دج';
                document.getElementById('wzdIrgDeduction').innerText = '-' + c.irg_deduction.toLocaleString() + ' دج';
                document.getElementById('wzdTotalNet').innerText = c.total_net.toLocaleString() + ' دج';

                window._currentWizardCalculation = {
                    tenant_id: tenantId,
                    employee_id: empId,
                    reason: reason,
                    departure_date: date,
                    leave_balance: c.leave_days,
                    leave_indemnity: c.leave_indemnity,
                    seniority_indemnity: c.seniority_indemnity,
                    preavis_indemnity: c.notice_indemnity,
                    total_net: c.total_net
                };

                document.getElementById('wizardStep3Box').style.display = 'block';
                showNotification('تم احتساب مستحقات تصفية الحساب STC وفق القانون 90-11 بنجاح');
            } else {
                alert(data.detail || 'فشل الاحتساب');
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function completeExitWizardFinal() {
        if (!window._currentWizardCalculation) {
            alert('يرجى احتساب المستحقات أولاً');
            return;
        }
        if (!confirm('هل أنت متأكد من الختم النهائي للمخالصة وإصدار شهادة العمل؟ سيتم إلغاء تفعيل حساب الموظف.')) return;

        try {
            const res = await fetch('/api/exit-wizard/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(window._currentWizardCalculation)
            });
            const data = await res.json();
            if (data.success) {
                alert(`✅ ${data.message}\nرقم المخالصة: ${data.stc_id}\nالبصمة الرقمية: ${data.seal_hash}`);
                showNotification('تم إصدار المخالصة وبراءة الذمة بنجاح');
                // Refresh views
                if (typeof loadEmployees === 'function') loadEmployees();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    // (Section 6 removed: Annual Evaluations)
    async function loadEvaluations() { return; }

    // =========================================================================
    // 7. IMPORT / EXPORT OPERATIONS & EVP VALIDATION
    // =========================================================================
    async function validateEVPAndCloseGate() {
        const tenantId = getActiveTenantId();
        if (!confirm('المصادقة الرسمية على كافة المتغيرات الشهرية (EVP) وقفل مصفوفة الإدخال لهذه الدورة؟')) return;

        try {
            const res = await fetch('/api/variables/validate-month', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tenant_id: tenantId, year: 2026, month: 10 })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                const badge = document.getElementById('evpValidationBadge');
                if (badge) {
                    badge.className = 'badge badge-success';
                    badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> تم الاعتماد الإداري والقفل';
                }
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function exportSystemSettings() {
        const tenantId = getActiveTenantId();
        try {
            const res = await fetch(`/api/export-settings?tenant_id=${encodeURIComponent(tenantId)}`);
            const data = await res.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `SYNCRA_Parametres_${tenantId}_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            showNotification('تم تصدير ملف الإعدادات بنجاح');
        } catch (err) {
            alert('خطأ في التصدير: ' + err.message);
        }
    }

    function triggerImportSettingsFile(event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async function (e) {
            try {
                const json = JSON.parse(e.target.result);
                const tenantId = getActiveTenantId();
                json.tenant_id = tenantId;
                const res = await fetch('/api/import-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(json)
                });
                const data = await res.json();
                if (data.success) {
                    showNotification(data.message);
                    loadJobTemplates();
                }
            } catch (err) {
                alert('ملف غير صالح: ' + err.message);
            }
        };
        reader.readAsText(file);
    }

    // Helper to populate select dropdowns
    async function populateEmployeeSelectOptions(selectId) {
        const select = document.getElementById(selectId);
        if (!select) return;
        const tenantId = getActiveTenantId();
        try {
            const res = await fetch(`/api/employees?tenant_id=${encodeURIComponent(tenantId)}`);
            const data = await res.json();
            if (data.success && data.employees) {
                select.innerHTML = data.employees.map(e => `<option value="${e.id}">${e.name} (${e.job_title})</option>`).join('');
            }
        } catch (e) {
            console.error('Failed to populate employees:', e);
        }
    }

    // Initialize all listeners and views
    function init() {
        console.log('SYNCRA Client Modules Suite Initialized.');
    }

    return {
        init,
        loadAbsences,
        openNewAbsenceModal,
        closeNewAbsenceModal,
        submitNewAbsence,
        approveAbsence,
        rejectAbsence,
        requestCancelAbsence,
        deleteAbsence,
        bulkApproveAllPending,
        loadHoursGrid,
        recalculateRowOvertime,
        saveSingleEmployeeHours,
        saveAllHours,
        downloadHoursTemplateCSV,
        loadMedicalVisits,
        openNewMedicalModal,
        closeNewMedicalModal,
        submitNewMedicalVisit,
        markVisitCompleted,
        loadJobTemplates,
        applyJobTemplate,
        triggerExitWizardCalculate,
        completeExitWizardFinal,
        loadEvaluations,
        validateEVPAndCloseGate,
        exportSystemSettings,
        triggerImportSettingsFile
    };
})();
