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

window.SyncraModules = (function () {
    // Current tenant identifier from session or default
    function getActiveTenantId() {
        if (window.currentTenantId) return window.currentTenantId;
        const tenantSelect = document.getElementById('topTenantSelect');
        if (tenantSelect && tenantSelect.value) return tenantSelect.value;
        return 'TENT-DZ-40492-629';
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

    // =========================================================================
    // 2. HOURS & OVERTIME ENTRY
    // =========================================================================
    async function loadHoursGrid() {
        const tenantId = getActiveTenantId();
        const year = parseInt(document.getElementById('hoursYearSelect')?.value || 2026);
        const month = parseInt(document.getElementById('hoursMonthSelect')?.value || 10);
        const tbody = document.getElementById('hoursTableBody');
        if (!tbody) return;

        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin text-primary"></i> جاري تحميل ساعات العمل...</td></tr>';

        try {
            const res = await fetch(`/api/hours?tenant_id=${encodeURIComponent(tenantId)}&year=${year}&month=${month}`);
            const data = await res.json();

            if (!data.success || !data.hours || data.hours.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--text-muted);">لا يوجد موظفون نشطون مسجلون في هذه الدورة</td></tr>';
                return;
            }

            let totalRegular = 0;
            let totalHs50 = 0;
            let totalHs100 = 0;
            let totalNight = 0;
            let totalOvertimePay = 0;

            let html = '';
            data.hours.forEach((h, idx) => {
                totalRegular += parseFloat(h.regular_hours || 0);
                totalHs50 += parseFloat(h.hs_50 || 0);
                totalHs100 += parseFloat(h.hs_100 || 0);
                totalNight += parseFloat(h.night_hours || 0);
                totalOvertimePay += parseFloat(h.overtime_pay || 0);

                html += `
                    <tr id="hoursRow_${h.employee_id}">
                        <td>
                            <strong style="color: var(--text-primary);">${h.employee_name}</strong>
                            <small style="color: var(--text-muted); display: block;">${h.job_title} • ${h.department}</small>
                        </td>
                        <td style="font-family: var(--font-mono); font-weight: 700;">
                            ${(h.base_salary || 0).toLocaleString()} <span style="font-size: 0.75rem; color: var(--text-muted);">دج</span>
                        </td>
                        <td style="font-family: var(--font-mono); color: var(--text-muted);">
                            ${(h.hourly_rate || 0).toFixed(2)} دج/س
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm hours-input" style="width: 80px;"
                                id="hrs_reg_${h.employee_id}" value="${h.regular_hours || 173.33}" step="0.5"
                                onchange="SyncraModules.recalculateRowOvertime('${h.employee_id}', ${h.hourly_rate})">
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm hours-input" style="width: 75px; color: #2563eb; font-weight: 700;"
                                id="hrs_hs50_${h.employee_id}" value="${h.hs_50 || 0}" step="0.5" min="0"
                                onchange="SyncraModules.recalculateRowOvertime('${h.employee_id}', ${h.hourly_rate})">
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm hours-input" style="width: 75px; color: #dc2626; font-weight: 700;"
                                id="hrs_hs100_${h.employee_id}" value="${h.hs_100 || 0}" step="0.5" min="0"
                                onchange="SyncraModules.recalculateRowOvertime('${h.employee_id}', ${h.hourly_rate})">
                        </td>
                        <td>
                            <input type="number" class="form-control form-control-sm hours-input" style="width: 75px; color: #4f46e5;"
                                id="hrs_night_${h.employee_id}" value="${h.night_hours || 0}" step="0.5" min="0">
                        </td>
                        <td>
                            <strong id="hrs_pay_${h.employee_id}" style="color: var(--success); font-family: var(--font-mono); font-size: 0.95rem;">
                                ${(h.overtime_pay || 0).toLocaleString()} دج
                            </strong>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-secondary" onclick="SyncraModules.saveSingleEmployeeHours('${h.employee_id}')" title="حفظ هذا الموظف">
                                <i class="fa-solid fa-floppy-disk"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;

            // Summary stats
            const elTotalHs = document.getElementById('hoursTotalHsCount');
            const elTotalPay = document.getElementById('hoursTotalHsPay');
            if (elTotalHs) elTotalHs.innerText = (totalHs50 + totalHs100).toFixed(1) + ' س';
            if (elTotalPay) elTotalPay.innerText = totalOvertimePay.toLocaleString() + ' دج';

        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger); padding: 20px;">خطأ: ${err.message}</td></tr>`;
        }
    }

    function recalculateRowOvertime(empId, hourlyRate) {
        const hs50 = parseFloat(document.getElementById(`hrs_hs50_${empId}`)?.value || 0);
        const hs100 = parseFloat(document.getElementById(`hrs_hs100_${empId}`)?.value || 0);
        const pay = (hs50 * hourlyRate * 1.5) + (hs100 * hourlyRate * 2.0);
        const payEl = document.getElementById(`hrs_pay_${empId}`);
        if (payEl) payEl.innerText = Math.round(pay).toLocaleString() + ' دج';
    }

    async function saveSingleEmployeeHours(empId) {
        const tenantId = getActiveTenantId();
        const year = parseInt(document.getElementById('hoursYearSelect')?.value || 2026);
        const month = parseInt(document.getElementById('hoursMonthSelect')?.value || 10);
        const reg = parseFloat(document.getElementById(`hrs_reg_${empId}`)?.value || 173.33);
        const hs50 = parseFloat(document.getElementById(`hrs_hs50_${empId}`)?.value || 0);
        const hs100 = parseFloat(document.getElementById(`hrs_hs100_${empId}`)?.value || 0);
        const night = parseFloat(document.getElementById(`hrs_night_${empId}`)?.value || 0);

        try {
            const res = await fetch('/api/hours', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    employee_id: empId,
                    year: year,
                    month: month,
                    regular_hours: reg,
                    hs_50: hs50,
                    hs_100: hs100,
                    night_hours: night
                })
            });
            const data = await res.json();
            if (data.success) {
                showNotification('تم حفظ ساعات العمل بنجاح');
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function saveAllHours() {
        const tenantId = getActiveTenantId();
        const year = parseInt(document.getElementById('hoursYearSelect')?.value || 2026);
        const month = parseInt(document.getElementById('hoursMonthSelect')?.value || 10);
        const rows = document.querySelectorAll('#hoursTableBody tr[id^="hoursRow_"]');

        const entries = [];
        rows.forEach(row => {
            const empId = row.id.replace('hoursRow_', '');
            const reg = parseFloat(document.getElementById(`hrs_reg_${empId}`)?.value || 173.33);
            const hs50 = parseFloat(document.getElementById(`hrs_hs50_${empId}`)?.value || 0);
            const hs100 = parseFloat(document.getElementById(`hrs_hs100_${empId}`)?.value || 0);
            const night = parseFloat(document.getElementById(`hrs_night_${empId}`)?.value || 0);

            entries.push({
                tenant_id: tenantId,
                employee_id: empId,
                year: year,
                month: month,
                regular_hours: reg,
                hs_50: hs50,
                hs_100: hs100,
                night_hours: night
            });
        });

        if (entries.length === 0) return;

        try {
            const res = await fetch('/api/hours/bulk-save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    year: year,
                    month: month,
                    entries: entries
                })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                loadHoursGrid();
            }
        } catch (err) {
            alert('خطأ أثناء حفظ الساعات: ' + err.message);
        }
    }

    function downloadHoursTemplateCSV() {
        const csvContent = "data:text/csv;charset=utf-8,\uFEFFID,Employee_Name,Regular_Hours,HS_50,HS_100,Night_Hours,Notes\nEMP-0001,AMINE MAZAR,173.33,10,4,0,Saisie mensuelle";
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "SYNCRA_Modele_Saisie_Heures.csv");
        document.body.appendChild(link);
        link.click();
        link.remove();
        showNotification("تم تنزيل نموذج ساعات العمل بنجاح");
    }

    // =========================================================================
    // 3. OCCUPATIONAL MEDICAL VISITS
    // =========================================================================
    async function loadMedicalVisits() {
        const tenantId = getActiveTenantId();
        const tbody = document.getElementById('medicalTableBody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin text-primary"></i> جاري تحميل سجل طب العمل...</td></tr>';

        try {
            const res = await fetch(`/api/medical-visits?tenant_id=${encodeURIComponent(tenantId)}`);
            const data = await res.json();

            if (!data.success || !data.visits || data.visits.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 32px; color: var(--text-muted);"><i class="fa-solid fa-heart-pulse" style="font-size: 2rem; margin-bottom: 8px; display: block;"></i>لا توجد زيارات طبية مجدولة حالياً</td></tr>';
                updateMedicalCounters({ total: 0, overdue: 0, scheduled: 0, completed: 0 });
                return;
            }

            updateMedicalCounters(data.summary || {});

            let html = '';
            data.visits.forEach(v => {
                const typeLabel = getMedicalTypeLabel(v.visit_type);
                const fitnessBadge = getFitnessBadge(v.fitness_status);
                const statusBadge = v.status === 'OVERDUE'
                    ? '<span class="badge badge-danger"><i class="fa-solid fa-triangle-exclamation"></i> متأخر</span>'
                    : v.status === 'COMPLETED'
                        ? '<span class="badge badge-success"><i class="fa-solid fa-check"></i> مكتمل</span>'
                        : '<span class="badge badge-info"><i class="fa-solid fa-calendar"></i> مجدول</span>';

                html += `
                    <tr>
                        <td>
                            <strong style="color: var(--text-primary); display: block;">${v.employee_name || v.employee_id}</strong>
                            <small style="color: var(--text-muted);">${v.job_title || ''} • NSS: ${v.nss || '-'}</small>
                        </td>
                        <td>${typeLabel}</td>
                        <td dir="ltr" style="font-family: var(--font-mono); font-size: 0.88rem;">${v.scheduled_date}</td>
                        <td>${v.doctor_name || 'طبيب العمل'} <br><small style="color: var(--text-muted);">${v.medical_center || ''}</small></td>
                        <td>${fitnessBadge}</td>
                        <td dir="ltr" style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted);">${v.next_visit_date || '-'}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <div style="display: flex; gap: 6px;">
                                ${v.status !== 'COMPLETED' ? `
                                    <button class="btn btn-sm btn-success" onclick="SyncraModules.markVisitCompleted('${v.id}')" title="تأكيد إجراء الفحص">
                                        <i class="fa-solid fa-circle-check"></i> إتمام
                                    </button>
                                ` : ''}
                                <button class="btn btn-sm btn-secondary" onclick="alert('ملاحظات الفحص: ' + '${v.notes || 'لا توجد ملاحظات'}')" title="عرض الملاحظات">
                                    <i class="fa-solid fa-notes-medical"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;

        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger); padding: 20px;">خطأ: ${err.message}</td></tr>`;
        }
    }

    function updateMedicalCounters(s) {
        const elTotal = document.getElementById('medCountTotal');
        const elOverdue = document.getElementById('medCountOverdue');
        const elScheduled = document.getElementById('medCountScheduled');
        const elCompleted = document.getElementById('medCountCompleted');
        if (elTotal) elTotal.innerText = s.total || 0;
        if (elOverdue) elOverdue.innerText = s.overdue || 0;
        if (elScheduled) elScheduled.innerText = s.scheduled || 0;
        if (elCompleted) elCompleted.innerText = s.completed || 0;
    }

    function getMedicalTypeLabel(t) {
        const types = {
            'EMBAUCHE': '<span class="badge badge-info">فحص التوظيف الأولي</span>',
            'PERIODIQUE': '<span class="badge badge-primary">فحص دوري سنوي</span>',
            'REPRISE': '<span class="badge badge-warning">فحص استئناف العمل</span>',
            'SPONTANEE': '<span class="badge badge-secondary">فحص عفوي</span>'
        };
        return types[t] || `<span class="badge">${t}</span>`;
    }

    function getFitnessBadge(f) {
        if (f === 'APTE') return '<span style="color: #16a34a; font-weight: 700;"><i class="fa-solid fa-check"></i> لائق طبياً</span>';
        if (f === 'APTE_RESTRICTIONS') return '<span style="color: #d97706; font-weight: 700;"><i class="fa-solid fa-triangle-exclamation"></i> لائق مع تحفظ</span>';
        if (f === 'INAPTE_TEMP') return '<span style="color: #dc2626; font-weight: 700;"><i class="fa-solid fa-xmark"></i> غير لائق مؤقتاً</span>';
        return f || 'غير محدد';
    }

    function openNewMedicalModal() {
        populateEmployeeSelectOptions('newMedEmployeeSelect');
        const modal = document.getElementById('modalNewMedicalVisit');
        if (modal) modal.style.display = 'flex';
    }

    function closeNewMedicalModal() {
        const modal = document.getElementById('modalNewMedicalVisit');
        if (modal) modal.style.display = 'none';
    }

    async function submitNewMedicalVisit(e) {
        if (e) e.preventDefault();
        const tenantId = getActiveTenantId();
        const empId = document.getElementById('newMedEmployeeSelect').value;
        const type = document.getElementById('newMedTypeSelect').value;
        const date = document.getElementById('newMedDate').value;
        const doc = document.getElementById('newMedDoctor').value;
        const center = document.getElementById('newMedCenter').value;
        const nextDate = document.getElementById('newMedNextDate').value;
        const notes = document.getElementById('newMedNotes').value;

        try {
            const res = await fetch('/api/medical-visits', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    employee_id: empId,
                    visit_type: type,
                    scheduled_date: date,
                    doctor_name: doc,
                    medical_center: center,
                    fitness_status: 'APTE',
                    next_visit_date: nextDate,
                    notes: notes
                })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                closeNewMedicalModal();
                loadMedicalVisits();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    async function markVisitCompleted(vid) {
        const fitness = prompt('حدد نتيجة الأهلية الطبية (APTE, APTE_RESTRICTIONS, INAPTE_TEMP):', 'APTE');
        if (!fitness) return;
        const today = new Date().toISOString().split('T')[0];
        try {
            const res = await fetch(`/api/medical-visits/${vid}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: 'COMPLETED',
                    completed_date: today,
                    fitness_status: fitness
                })
            });
            const data = await res.json();
            if (data.success) {
                showNotification(data.message);
                loadMedicalVisits();
            }
        } catch (err) {
            alert('خطأ: ' + err.message);
        }
    }

    // =========================================================================
    // 4. REUSABLE JOB TEMPLATES
    // =========================================================================
    async function loadJobTemplates() {
        const tenantId = getActiveTenantId();
        const container = document.getElementById('jobTemplatesGrid');
        if (!container) return;
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin text-primary"></i> جاري تحميل النماذج الوظيفية...</div>';

        try {
            const res = await fetch(`/api/job-templates?tenant_id=${encodeURIComponent(tenantId)}`);
            const data = await res.json();

            if (!data.success || !data.templates || data.templates.length === 0) {
                container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 32px; color: var(--text-muted);">لا توجد نماذج وظيفية محفوظة حالياً</div>';
                return;
            }

            let html = '';
            data.templates.forEach(t => {
                html += `
                    <div class="kpi-card" style="display: flex; flex-direction: column; justify-content: space-between; border-inline-start: 4px solid var(--primary);">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                <h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin: 0;">${t.title}</h4>
                                <span class="badge badge-info">${t.contract_type || 'CDI'}</span>
                            </div>
                            <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">${t.department} • ${t.description || ''}</p>
                            <div style="background: var(--bg-surface-elevated); padding: 10px; border-radius: 8px; margin-bottom: 14px; font-size: 0.85rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: var(--text-secondary);">الراتب الأساسي:</span>
                                    <strong style="color: var(--primary); font-family: var(--font-mono);">${(t.default_salary || 0).toLocaleString()} دج</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                    <span style="color: var(--text-secondary);">منحة النقل:</span>
                                    <span style="font-family: var(--font-mono);">${(t.transport || 0).toLocaleString()} دج</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: var(--text-secondary);">منحة القفة/السلة:</span>
                                    <span style="font-family: var(--font-mono);">${(t.basket || 0).toLocaleString()} دج</span>
                                </div>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm" style="width: 100%; font-weight: 700;" onclick="SyncraModules.applyJobTemplate(${JSON.stringify(t).replace(/"/g, '&quot;')})">
                            <i class="fa-solid fa-user-plus"></i> توظيف فوري بهذا النموذج
                        </button>
                    </div>
                `;
            });

            container.innerHTML = html;

        } catch (err) {
            container.innerHTML = `<div style="grid-column: 1/-1; color: var(--danger); text-align: center;">خطأ: ${err.message}</div>`;
        }
    }

    function applyJobTemplate(t) {
        // Switch to Add Employee tab and pre-fill form
        if (typeof switchSaaSTab === 'function') {
            switchSaaSTab('view-add-employee');
        }
        setTimeout(() => {
            const jobEl = document.getElementById('screenEmpJob');
            const deptEl = document.getElementById('screenEmpDept');
            const contractEl = document.getElementById('screenEmpContract');
            const salaryEl = document.getElementById('screenEmpBaseSalary');
            const transportEl = document.getElementById('screenEmpTransport');
            const basketEl = document.getElementById('screenEmpBasket');
            const bonusEl = document.getElementById('screenEmpBonus');

            if (jobEl) jobEl.value = t.title || '';
            if (deptEl) deptEl.value = t.department || 'الإدارة';
            if (contractEl) contractEl.value = t.contract_type || 'CDI';
            if (salaryEl) salaryEl.value = t.default_salary || 45000;
            if (transportEl) transportEl.value = t.transport || 3500;
            if (basketEl) basketEl.value = t.basket || 4500;
            if (bonusEl) bonusEl.value = t.bonus || 0;

            showNotification(`تم تحميل بيانات النموذج الوظيفي: ${t.title}`);
        }, 150);
    }

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

    // =========================================================================
    // 6. ANNUAL PERFORMANCE EVALUATIONS
    // =========================================================================
    async function loadEvaluations() {
        const tenantId = getActiveTenantId();
        const container = document.getElementById('evaluationsList');
        if (!container) return;
        container.innerHTML = '<div style="text-align: center; padding: 24px;"><i class="fa-solid fa-spinner fa-spin text-primary"></i> جاري تحميل تقييمات الأداء...</div>';

        try {
            const res = await fetch(`/api/evaluations?tenant_id=${encodeURIComponent(tenantId)}`);
            const data = await res.json();

            if (!data.success || !data.evaluations || data.evaluations.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 32px; color: var(--text-muted);"><i class="fa-solid fa-clipboard-check" style="font-size: 2rem; margin-bottom: 8px; display: block;"></i>لا توجد تقييمات سنوية مسجلة بعد</div>';
                return;
            }

            let html = '';
            data.evaluations.forEach(ev => {
                const scoreColor = ev.score_percentage >= 90 ? '#16a34a' : ev.score_percentage >= 75 ? '#2563eb' : '#d97706';
                html += `
                    <div class="kpi-card" style="margin-bottom: 12px; border-inline-start: 4px solid ${scoreColor};">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin: 0;">${ev.employee_name}</h4>
                                <small style="color: var(--text-muted);">${ev.job_title} • المقيم: ${ev.evaluator_name} • دورة ${ev.evaluation_year}</small>
                            </div>
                            <div style="text-align: right;">
                                <span style="font-size: 1.4rem; font-weight: 900; color: ${scoreColor}; font-family: var(--font-mono);">${ev.score_percentage}%</span>
                                <small style="display: block; color: var(--text-muted);">علامة التقييم</small>
                            </div>
                        </div>
                        <div style="margin-top: 12px; font-size: 0.88rem; line-height: 1.6; color: var(--text-secondary); background: var(--bg-surface-elevated); padding: 12px; border-radius: 8px;">
                            <p style="margin-bottom: 4px;"><strong>🎯 الأهداف المحققة:</strong> ${ev.objectives_achieved || '-'}</p>
                            <p style="margin-bottom: 4px;"><strong>💪 نقاط القوة:</strong> ${ev.strengths || '-'}</p>
                            <p style="margin: 0;"><strong>📈 محاور التطوير:</strong> ${ev.improvements || '-'}</p>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;

        } catch (err) {
            container.innerHTML = `<div style="color: var(--danger); text-align: center;">خطأ: ${err.message}</div>`;
        }
    }

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
