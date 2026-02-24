/** PREMIUM ADMIN DASHBOARD LOGIC — AML Blueprint Edition **/
let currentTickets = [];
let activeTicketId = null;
let logPollingInterval = null;

// Dynamically determine the backend URL
const API_BASE = (window.location.protocol === 'file:' || window.location.port !== '8000')
    ? 'http://localhost:8000'
    : window.location.origin;

document.addEventListener('DOMContentLoaded', () => {
    initAdminDashboard();
});

async function initAdminDashboard() {
    await fetchTickets();
}

async function fetchTickets(statusFilter = '') {
    const listContainer = document.getElementById('ticket-list-container');
    listContainer.innerHTML = '<div style="padding: 60px; text-align: center; color: var(--dash-text-muted);">Syncing board status...</div>';

    try {
        const url = statusFilter
            ? `${API_BASE}/admin/tickets?status=${statusFilter}`
            : `${API_BASE}/admin/tickets`;
        const res = await fetch(url);
        const data = await res.json();
        currentTickets = data.tickets || [];
        renderTicketList(currentTickets);
        updateStats(currentTickets);
    } catch (err) {
        listContainer.innerHTML = `<div style="padding:60px;text-align:center;color:#ef4444;">⚠ Failed to connect to backend. Ensure backend is running on port 8000.</div>`;
    }
}

function updateStats(tickets) {
    const total = tickets.length;
    const pending = tickets.filter(t => t.status === 'PENDING_REVIEW').length;
    const approved = tickets.filter(t => t.status === 'APPROVED').length;
    const flagged = tickets.filter(t => t.ai_risk_level === 'HIGH_RISK' || t.ai_risk_level === 'FLAGGED').length;

    const statEl = document.getElementById('ticket-stats');
    if (statEl) {
        const kycComplete = tickets.filter(t => t.status === 'KYC_COMPLETE').length;
        const amlComplete = tickets.filter(t => t.status === 'AML_COMPLETE').length;
        statEl.innerHTML = `
            <span style="color:var(--dash-text-muted);font-size:0.78rem;">
                <strong style="color:var(--dash-text);">${total}</strong> Total &nbsp;|&nbsp;
                <strong style="color:#f59e0b;">${pending}</strong> Pending &nbsp;|&nbsp;
                <strong style="color:#22c55e;">${approved}</strong> Approved &nbsp;|&nbsp;
                <strong style="color:#3b82f6;">${kycComplete}</strong> KYC &nbsp;|&nbsp;
                <strong style="color:#8b5cf6;">${amlComplete}</strong> AML
            </span>
        `;
    }
}

function getStatusClass(status) {
    const map = {
        'PENDING_REVIEW': 'pending',
        'VETTING_IN_PROGRESS': 'docs',
        'AI_REVIEW_COMPLETE': 'approved',
        'KYC_COMPLETE': 'vetting',
        'AML_IN_PROGRESS': 'vetting',
        'AML_COMPLETE': 'clarify',
        'AML_STAGE3_COMPLETE': 'clarify',
        'AML_REVIEW_READY': 'approved',
        'APPROVED': 'approved',
        'REJECTED': 'rejected',
        'CANCELLED': 'cancelled',
        'CLARIFICATION_REQUIRED': 'clarify',
    };
    return map[status] || 'pending';
}

function getRiskBadge(riskLevel) {
    if (!riskLevel) return '';
    const map = {
        'CLEARED': { color: '#22c55e', bg: '#052e16', icon: '🟢' },
        'FLAGGED': { color: '#f59e0b', bg: '#422006', icon: '🟡' },
        'HIGH_RISK': { color: '#ef4444', bg: '#3f0000', icon: '🔴' },
        'CRITICAL': { color: '#f87171', bg: '#3f0000', icon: '⛔' },
    };
    const style = map[riskLevel] || { color: '#9ca3af', bg: '#1f1f1f', icon: '⚪' };
    return `<span style="background:${style.bg};color:${style.color};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;margin-left:8px;">${style.icon} ${riskLevel.replace('_', ' ')}</span>`;
}

function renderTicketList(tickets) {
    const listContainer = document.getElementById('ticket-list-container');

    if (!tickets.length) {
        listContainer.innerHTML = '<div style="padding:60px;text-align:center;color:var(--dash-text-muted);">No applications found.</div>';
        return;
    }

    listContainer.innerHTML = tickets.map(t => `
        <div class="ticket-card ${t.id === activeTicketId ? 'active' : ''}" onclick="loadTicket('${t.id}')" data-id="${t.id}">
            <div class="ticket-card-header">
                <span class="ticket-tracking">${t.tracking_id || 'N/A'}</span>
                <span class="status-badge ${getStatusClass(t.status)}">${t.status.replace(/_/g, ' ')}</span>
            </div>
            <div class="ticket-company">${t.company_name}</div>
            <div class="ticket-meta">
                ${t.country || ''} · ${t.entity_type || ''} ${getRiskBadge(t.ai_risk_level)}
            </div>
            <div class="ticket-date">${new Date(t.submitted_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
        </div>
    `).join('');
}

async function loadTicket(id) {
    activeTicketId = id;
    document.querySelectorAll('.ticket-card').forEach(c => c.classList.toggle('active', c.dataset.id === id));

    const detailContainer = document.getElementById('ticket-detail-container');
    detailContainer.innerHTML = '<div style="padding:80px;text-align:center;color:var(--dash-text-muted);">Loading...</div>';

    try {
        const res = await fetch(`${API_BASE}/admin/tickets/${id}`);
        const data = await res.json();
        const t = data.ticket;
        renderTicketDetail(t);

        // Start polling if ticket is in progress
        if (['PENDING_REVIEW', 'AML_IN_PROGRESS', 'KYC_COMPLETE'].includes(t.status)) {
            startLogPolling(id);
        }
    } catch (err) {
        detailContainer.innerHTML = `<div style="padding:40px;color:#ef4444;">Failed to load ticket: ${err.message}</div>`;
    }
}

function startLogPolling(id) {
    if (logPollingInterval) clearInterval(logPollingInterval);
    logPollingInterval = setInterval(async () => {
        if (activeTicketId !== id) {
            clearInterval(logPollingInterval);
            return;
        }
        await fetchAgentLogs(id);

        // Also check if status changed to enable buttons
        const res = await fetch(`${API_BASE}/admin/tickets/${id}`);
        const data = await res.json();
        if (data.ticket.status !== 'PENDING_REVIEW' && data.ticket.status !== 'AML_IN_PROGRESS') {
            // Status changed! Refresh full detail once to show buttons
            renderTicketDetail(data.ticket);
            clearInterval(logPollingInterval);
        }
    }, 5000);
}

function renderTicketDetail(t) {
    const aml = t.aml_questions || {};
    const container = document.getElementById('ticket-detail-container');

    // Parse dates
    const submittedDate = t.submitted_at ? new Date(t.submitted_at).toLocaleString() : 'N/A';

    // Directors HTML
    const directorsHtml = (t.directors && t.directors.length)
        ? t.directors.map(d => `
            <tr>
                <td>${d.full_name || '—'}</td>
                <td>${d.role || '—'}</td>
                <td>${d.nationality || '—'}</td>
                <td>${d.country_of_residence || '—'}</td>
            </tr>`).join('')
        : '<tr><td colspan="4" style="color:var(--dash-text-muted);font-style:italic;text-align:center;">No directors declared</td></tr>';

    // UBOs HTML
    const ubosHtml = (t.ubos && t.ubos.length)
        ? t.ubos.map(u => `
            <tr>
                <td>${u.full_name || '—'}</td>
                <td>${u.stake_percent ? u.stake_percent + '%' : '—'}</td>
                <td>${u.nationality || '—'}</td>
                <td>${u.country_of_residence || '—'}</td>
                <td>${u.date_of_birth || '—'}</td>
                <td>${u.tax_id || '—'}</td>
                <td><span style="color:${u.is_pep ? '#ef4444' : '#22c55e'}">${u.is_pep ? '⚠ YES' : 'No'}</span></td>
            </tr>`).join('')
        : '<tr><td colspan="6" style="color:var(--dash-text-muted);font-style:italic;text-align:center;">No UBOs declared</td></tr>';

    // Audit history
    const histHtml = (t.history && t.history.length)
        ? t.history.map(h => `
            <div class="audit-row">
                <span class="audit-dot"></span>
                <div>
                    <span class="status-badge ${getStatusClass(h.new_status || '')}">${(h.new_status || '').replace(/_/g, ' ')}</span>
                    ${h.old_status ? `<span style="font-size:0.75rem;color:var(--dash-text-muted);margin-left:6px;">← ${h.old_status.replace(/_/g, ' ')}</span>` : ''}
                    <div style="font-size:0.75rem;color:var(--dash-text-muted);margin-top:3px;">${h.action_timestamp ? new Date(h.action_timestamp).toLocaleString() : ''} ${h.remarks ? '— ' + h.remarks : ''}</div>
                </div>
            </div>
        `).join('')
        : '<div style="color:var(--dash-text-muted);font-size:0.82rem;">No audit history.</div>';

    container.innerHTML = `
        <div class="ticket-detail-inner">
            <!-- Header -->
            <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:24px;">
                <div>
                    <div style="font-size:0.7rem;color:var(--dash-text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">${t.tracking_id || 'ID N/A'}</div>
                    <h2 style="font-size:1.5rem;font-weight:800;color:var(--dash-text);margin:0;">${t.company_name || 'N/A'}</h2>
                    <div style="margin-top:6px;display:flex;align-items:center;flex-wrap:wrap;gap:8px;">
                        <span class="status-badge ${getStatusClass(t.status)}">${t.status.replace(/_/g, ' ')}</span>
                        ${getRiskBadge(t.ai_risk_level)}
                        <span style="font-size:0.75rem;color:var(--dash-text-muted);">Submitted ${submittedDate}</span>
                    </div>
                </div>
                <div class="action-btns" style="display:flex;gap:8px;flex-wrap:wrap;">
                    ${renderActionButtons(t)}
                </div>
            </div>

            <!-- AI Agent Logs (PROMOTED TO TOP) -->
            <div class="detail-section" style="background: rgba(0, 255, 163, 0.03); padding: 15px; border-radius: 8px; border: 1px solid rgba(0, 255, 163, 0.1); margin-bottom: 24px;">
                <div class="detail-section-title" style="color: var(--dash-accent); border-color: rgba(0, 255, 163, 0.2);">🤖 AI Screening Intelligence</div>
                <div id="agent-logs-container" style="font-size:0.82rem;">
                    <div style="color:var(--dash-text-muted);">Syncing AI audit logs...</div>
                </div>
            </div>

            <!-- Entity Identity -->
            <div class="detail-section">
                <div class="detail-section-title">Entity Identity</div>
                <div class="detail-grid">
                    <div class="detail-item"><span class="d-label">Legal Entity</span><span class="d-value">${t.company_name || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Entity Type</span><span class="d-value">${t.entity_type || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">LEI</span><span class="d-value" style="font-family:monospace;">${t.lei_identifier || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Registration No.</span><span class="d-value">${t.registration_number || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">EIN / Tax ID</span><span class="d-value">${t.ein_number || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">DBA Name</span><span class="d-value">${t.dba_name || 'None'}</span></div>
                    <div class="detail-item"><span class="d-label">Incorporation Date</span><span class="d-value">${t.incorporation_date || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Ownership Type</span><span class="d-value">${t.ownership_type || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Regulatory Status</span><span class="d-value">${t.regulatory_status || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Regulatory Authority</span><span class="d-value">${t.regulatory_authority || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Email</span><span class="d-value">${t.email || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Phone</span><span class="d-value">${t.phone_number || '—'}</span></div>
                </div>
            </div>

            <!-- Address -->
            <div class="detail-section">
                <div class="detail-section-title">Address</div>
                <div class="detail-grid">
                    <div class="detail-item"><span class="d-label">Registered Address</span><span class="d-value">${t.company_address || '—'}, ${t.city || ''}, ${t.state || ''}, ${t.country || ''} ${t.zip_code || ''}</span></div>
                    <div class="detail-item"><span class="d-label">Trading Address</span><span class="d-value">${t.trading_address || 'Same as registered'}</span></div>
                    <div class="detail-item"><span class="d-label">Tax Residency</span><span class="d-value">${t.tax_residency_country || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Company Website</span><span class="d-value">${t.website ? `<a href="${t.website.startsWith('http') ? t.website : 'https://' + t.website}" target="_blank" style="color:var(--dash-accent);">${t.website}</a>` : '—'}</span></div>
                </div>
            </div>

            <!-- Directors -->
            <div class="detail-section">
                <div class="detail-section-title">Directors (${(t.directors || []).length})</div>
                <div style="overflow-x:auto;">
                    <table class="detail-table">
                        <thead><tr><th>Name</th><th>Role</th><th>Nationality</th><th>Country of Residence</th></tr></thead>
                        <tbody>${directorsHtml}</tbody>
                    </table>
                </div>
            </div>

            <!-- UBOs -->
            <div class="detail-section">
                <div class="detail-section-title">Ultimate Beneficial Owners (${(t.ubos || []).length})</div>
                <div style="overflow-x:auto;">
                    <table class="detail-table">
                        <thead><tr><th>Name</th><th>Stake %</th><th>Nationality</th><th>Country of Residence</th><th>DOB</th><th>ID/Tax ID</th><th>PEP</th></tr></thead>
                        <tbody>${ubosHtml}</tbody>
                    </table>
                </div>
            </div>

            <!-- Settlement Details -->
            <div class="detail-section">
                <div class="detail-section-title">Settlement & Bank Details</div>
                <div class="detail-grid">
                    <div class="detail-item"><span class="d-label">Recipient Bank</span><span class="d-value">${t.bank_name || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Routing / SWIFT</span><span class="d-value" style="font-family:monospace;">${t.routing_number || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Account Number</span><span class="d-value" style="font-family:monospace;">${t.account_number || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Risk Category (MCC)</span><span class="d-value"><span style="background:rgba(255,255,255,0.05);padding:2px 6px;border-radius:4px;">${t.mcc_code || '—'}</span></span></div>
                </div>
            </div>

            <!-- AML Profile -->
            <div class="detail-section">
                <div class="detail-section-title">AML Profile</div>
                <div class="detail-grid">
                    <div class="detail-item"><span class="d-label">Business Activity</span><span class="d-value">${t.business_activity || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Source of Funds</span><span class="d-value">${t.source_of_funds || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Source of Wealth</span><span class="d-value">${t.source_of_wealth || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Expected Monthly Volume</span><span class="d-value">${t.expected_volume || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Countries of Operation</span><span class="d-value">${t.countries_operation || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Sanctions Exposure</span><span class="d-value">${aml.sanctions_exposure || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">PEP Declaration</span><span class="d-value" style="color:${t.pep_declaration ? '#ef4444' : '#22c55e'}">${t.pep_declaration ? '⚠ YES — PEP Declared' : 'No'}</span></div>
                    <div class="detail-item"><span class="d-label">AML Program</span><span class="d-value">${aml.aml_program_confirmed === 'yes' ? '✔ Confirmed' : '✗ Not Confirmed'}</span></div>
                    <div class="detail-item"><span class="d-label">AML Program Description</span><span class="d-value">${t.aml_program_description || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Correspondent Bank</span><span class="d-value">${t.correspondent_bank || '—'}</span></div>
                    <div class="detail-item"><span class="d-label">Adverse Media Consent</span><span class="d-value">${t.adverse_media_consent ? '✔ Consented' : '✗ Not Consented'}</span></div>
                </div>
            </div>

            <!-- Documents -->
            <div class="detail-section">
                <div class="detail-section-title">Documents</div>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/bod" target="_blank" class="doc-link">📄 Board of Directors</a>
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/financials" target="_blank" class="doc-link">📊 Financials</a>
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/ownership" target="_blank" class="doc-link">🏢 Ownership Structure</a>
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/incorporation" target="_blank" class="doc-link">📋 Certificate of Incorporation</a>
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/bank" target="_blank" class="doc-link">🏦 Bank Statement</a>
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/ein" target="_blank" class="doc-link">🪪 EIN Certificate</a>
                    <a href="${API_BASE}/admin/tickets/${t.id}/docs/ubo_id" target="_blank" class="doc-link">🆔 UBO ID</a>
                </div>
            </div>

            <!-- Audit Trail -->
            <div class="detail-section">
                <div class="detail-section-title">Audit Trail</div>
                <div class="audit-timeline">${histHtml}</div>
            </div>
        </div>
    `;

    // Fetch agent logs async
    fetchAgentLogs(t.id);
}

function renderActionButtons(t) {
    const status = t.status;
    const id = t.id;
    const terminal = ['APPROVED', 'REJECTED', 'CANCELLED'];

    if (terminal.includes(status)) {
        return `<span style="color:var(--dash-text-muted);font-size:0.82rem;font-style:italic;">No further actions available.</span>`;
    }

    if (status === 'PENDING_REVIEW') {
        return `<span style="color:#f59e0b;font-size:0.82rem;font-weight:600;display:flex;align-items:center;gap:6px;">
            <span class="pulse">⏳</span> Complex AI Screening in Progress (10+ Checks Running)
        </span>
        <div style="font-size:0.65rem;color:var(--dash-text-muted);margin-top:4px;">Approve/Reject buttons will appear once stage 1 is complete (~25s).</div>`;
    }

    if (status === 'KYC_COMPLETE') {
        return `
            <button class="dash-btn dash-btn-approve" onclick="takeAction('${id}','approve')">✔ Approve KYC → Start AML</button>
            <button class="dash-btn dash-btn-clarify" onclick="takeAction('${id}','clarify')">? Clarify</button>
            <button class="dash-btn dash-btn-reject" onclick="takeAction('${id}','reject')">✕ Reject at KYC</button>
            <button class="dash-btn" onclick="takeAction('${id}','cancel')">◼ Cancel</button>`;
    }

    if (status === 'AML_IN_PROGRESS') {
        return `<span style="color:#f59e0b;font-size:0.82rem;">⏳ AML Risk assessment running...</span>`;
    }

    if (status === 'AML_COMPLETE') {
        return `
            <button class="dash-btn dash-btn-approve" onclick="takeAction('${id}','approve')">✔ Final Approve</button>
            <button class="dash-btn dash-btn-clarify" onclick="takeAction('${id}','clarify')">? Request Clarification</button>
            <button class="dash-btn dash-btn-reject" onclick="takeAction('${id}','reject')">✕ Final Reject</button>
            <button class="dash-btn" onclick="takeAction('${id}','cancel')">◼ Cancel</button>`;
    }

    // Default: show all 4 buttons for any other status (CLARIFICATION_REQUIRED etc.)
    return `
        <button class="dash-btn dash-btn-approve" onclick="takeAction('${id}','approve')">✔ Approve</button>
        <button class="dash-btn dash-btn-clarify" onclick="takeAction('${id}','clarify')">? Clarify</button>
        <button class="dash-btn dash-btn-reject" onclick="takeAction('${id}','reject')">✕ Reject</button>
        <button class="dash-btn" onclick="takeAction('${id}','cancel')">◼ Cancel</button>`;
}

async function runKycAgent(ticketId) {
    const btn = event.target;
    btn.disabled = true;
    btn.innerText = '⏳ Running KYC...';
    try {
        await fetch(`${API_BASE}/admin/tickets/${ticketId}/run-kyc`, { method: 'POST' });
        setTimeout(async () => {
            await fetchTickets();
            await loadTicket(ticketId);
        }, 3000);
    } catch (err) {
        alert('Failed to trigger KYC agent: ' + err.message);
        btn.disabled = false;
        btn.innerText = '▶ Run KYC Agent';
    }
}

const _RISK_BADGE_STYLE = {
    'LOW': { bg: '#052e16', color: '#22c55e', icon: '🟢' },
    'MEDIUM': { bg: '#422006', color: '#f59e0b', icon: '🟡' },
    'HIGH': { bg: '#3f0000', color: '#ef4444', icon: '🔴' },
    'CRITICAL': { bg: '#3f0000', color: '#f87171', icon: '⛔' },
};

function agentRiskBadge(risk) {
    const s = _RISK_BADGE_STYLE[risk] || { bg: '#1f2937', color: '#9ca3af', icon: '⚪' };
    return `<span style="background:${s.bg};color:${s.color};padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;">${s.icon} ${risk || 'UNKNOWN'}</span>`;
}

function renderAgentEvidence(log) {
    if (!log.output && !log.input_context) return '';

    let html = '<div style="margin-top:8px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; border-left: 3px solid var(--dash-accent);">';

    if (log.check_name === 'ocr_extraction') {
        const form = log.input_context?.form_data || {};
        const ai = log.output || {};

        // Use fallbacks if form_data is missing (older logs)
        const submittedName = form.company_name || '—';
        const submittedReg = form.registration_number || '—';

        html += `
            <div style="font-size:0.7rem; color:var(--dash-accent); margin-bottom:6px; font-weight:bold; text-transform:uppercase; letter-spacing:0.05em;">AI Comparison Evidence</div>
            <table style="width:100%; font-size:0.75rem; border-collapse:collapse;">
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <th style="text-align:left; padding:4px; color:var(--dash-text-muted);">Detail</th>
                    <th style="text-align:left; padding:4px; color:var(--dash-text-muted);">Form Value</th>
                    <th style="text-align:left; padding:4px; color:var(--dash-text-muted);">AI Extracted</th>
                </tr>
                <tr>
                    <td style="padding:4px; color:var(--dash-text-muted);">Legal Name</td>
                    <td style="padding:4px;">${submittedName}</td>
                    <td style="padding:4px; font-weight:bold; color:${submittedName !== ai.extracted_name && submittedName !== '—' ? '#f87171' : '#4ade80'}">${ai.extracted_name || '—'}</td>
                </tr>
                <tr>
                    <td style="padding:4px; color:var(--dash-text-muted);">Reg Number</td>
                    <td style="padding:4px;">${submittedReg}</td>
                    <td style="padding:4px; font-weight:bold; color:${submittedReg !== ai.reg_number && submittedReg !== '—' ? '#f87171' : '#4ade80'}">${ai.reg_number || '—'}</td>
                </tr>
            </table>
            <div style="margin-top:6px; font-size:0.7rem; color:var(--dash-text-muted);">Confidence Score: <span style="color:var(--dash-accent); font-weight:bold;">${ai.consistency_score || 0}%</span> ${log.input_context?.form_data ? '' : '<span style="font-style:italic; font-size:0.6rem;">(Historical context restricted)</span>'}</div>
        `;
    } else if (log.check_name === 'lei_verify' || log.check_name === 'entity_verification') {
        const lei = log.output?.lei_row || {};
        const input = log.input_context || {};
        html += `
            <div style="font-size:0.7rem; color:var(--dash-accent); margin-bottom:6px; font-weight:bold; text-transform:uppercase;">Registry Comparison</div>
            <table style="width:100%; font-size:0.75rem; border-collapse:collapse;">
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <th style="text-align:left; padding:4px; color:var(--dash-text-muted);">Field</th>
                    <th style="text-align:left; padding:4px; color:var(--dash-text-muted);">Submitted</th>
                    <th style="text-align:left; padding:4px; color:var(--dash-text-muted);">Registry</th>
                </tr>
                <tr>
                    <td style="padding:4px; color:var(--dash-text-muted);">Legal Name</td>
                    <td style="padding:4px;">${input.company_name || '—'}</td>
                    <td style="padding:4px; font-weight:bold; color:${!log.output?.name_match ? '#f87171' : '#4ade80'}">${lei.legal_name || '—'}</td>
                </tr>
            </table>
        `;
    } else if (log.output?.hits?.length > 0) {
        html += `
            <div style="font-size:0.7rem; color:#f87171; margin-bottom:6px; font-weight:bold; text-transform:uppercase;">Identified Matches</div>
            ${log.output.hits.map(h => `
                <div style="font-size:0.72rem; padding:6px; border-bottom:1px solid rgba(255,255,255,0.05); background:rgba(248,113,113,0.05); margin-bottom:2px; border-radius:3px;">
                    <span style="color:var(--dash-accent); font-weight:bold;">${h.matched_name || h.ubo || h.director}</span>
                    <span style="color:var(--dash-text-muted); font-size:0.65rem; margin-left:5px;">[${h.program || 'N/A'}]</span>
                    <div style="color:var(--dash-text-muted); font-size:0.65rem; margin-top:2px;">Type: ${h.entity_type || 'Individual'} | Country: ${h.country || 'N/A'}</div>
                </div>
            `).join('')}
        `;
    }

    if (log.output?.decision_logic || log.output?.rationale || log.ai_summary || log.output?.audit_trail) {
        html += `
            <button onclick='showEvidenceModal(${JSON.stringify(log).replace(/'/g, "&apos;")})' 
                    style="margin-top:10px; background:rgba(0, 255, 163, 0.05); border:1px solid rgba(0, 255, 163, 0.2); color:var(--dash-accent); padding:4px 10px; border-radius:4px; font-size:0.65rem; cursor:pointer; font-weight:bold; transition:all 0.2s; width:100%; text-align:center;">
                🔎 VIEW DECISION LOG & EVIDENCE
            </button>
        `;
    }

    html += '</div>';
    return html;
}

window.showEvidenceModal = function (log) {
    const isObject = typeof log === 'object';
    const logicText = isObject ? (log.output?.decision_logic || log.output?.rationale || log.ai_summary) : log;
    const auditTrail = isObject ? log.output?.audit_trail : null;

    let modal = document.getElementById('evidence-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'evidence-modal';
        document.body.appendChild(modal);
    }

    let auditHtml = '';
    if (auditTrail && Array.isArray(auditTrail) && auditTrail.length > 0) {
        auditHtml = `
            <div style="margin-bottom:20px;">
                <div style="font-size:0.75rem; color:var(--dash-accent); font-weight:bold; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid rgba(0,255,163,0.2); padding-bottom:5px;">
                    🛡 Verification Summary Table
                </div>
                <table style="width:100%; border-collapse:collapse; font-size:0.8rem; background:rgba(255,255,255,0.02); border-radius:8px; overflow:hidden;">
                    <thead style="background:rgba(0,0,0,0.3);">
                        <tr>
                            <th style="padding:10px; text-align:left; color:var(--dash-text-muted);">Check Point</th>
                            <th style="padding:10px; text-align:left; color:var(--dash-text-muted);">Form Value</th>
                            <th style="padding:10px; text-align:left; color:var(--dash-text-muted);">OCR / Agent Found</th>
                            <th style="padding:10px; text-align:center; color:var(--dash-text-muted);">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${auditTrail.map(step => `
                            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                                <td style="padding:10px; font-weight:bold; color:var(--dash-text);">${step.label}</td>
                                <td style="padding:10px; color:var(--dash-text-muted);">${step.form_value || '—'}</td>
                                <td style="padding:10px; color:var(--dash-text); font-family:monospace;">${step.ocr_value || '—'}</td>
                                <td style="padding:10px; text-align:center;">
                                    <span style="padding:2px 6px; border-radius:4px; font-weight:bold; font-size:0.65rem; 
                                        color:${step.status === 'MATCH' ? '#4ade80' : step.status === 'PARTIAL' ? '#fbbf24' : '#f87171'};
                                        background:${step.status === 'MATCH' ? 'rgba(74,222,128,0.1)' : step.status === 'PARTIAL' ? 'rgba(251,191,36,0.1)' : 'rgba(248,113,113,0.1)'};">
                                        ${step.status}
                                    </span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    modal.innerHTML = `
        <div id="evidence-modal-backdrop" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); backdrop-filter:blur(10px); z-index:9999; display:flex; align-items:center; justify-content:center;">
            <div style="background:var(--dash-bg); border:1px solid rgba(0,255,163,0.2); border-radius:12px; width:95%; max-width:800px; padding:30px; position:relative; box-shadow:0 10px 40px rgba(0,0,0,0.5); overflow-y:auto; max-height:90vh;">
                <div style="font-size:1.2rem; font-weight:bold; color:var(--dash-accent); margin-bottom:20px; display:flex; align-items:center; gap:10px;">
                    <span>🛡</span> AI Audit Intelligence Report
                </div>
                
                ${auditHtml}

                <div style="font-size:0.75rem; color:var(--dash-accent); font-weight:bold; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px; border-bottom:1px solid rgba(0,255,163,0.2); padding-bottom:5px;">
                    🧠 Detailed Agent Reasoning
                </div>
                <div id="evidence-content" style="font-size:0.9rem; line-height:1.6; color:var(--dash-text-muted); padding-right:10px; border-left:3px solid var(--dash-accent); padding-left:15px; background:rgba(255,255,255,0.02); border-radius:0 8px 8px 0; white-space:pre-wrap;">${logicText || 'No detailed reasoning available.'}</div>
                
                <button onclick="document.getElementById('evidence-modal').remove()" 
                        style="margin-top:25px; width:100%; background:var(--dash-accent); border:none; color:black; padding:12px; border-radius:8px; font-weight:bold; cursor:pointer; text-transform:uppercase; letter-spacing:1px;">
                    Close Audit Report
                </button>
                <div style="margin-top:10px; font-size:0.7rem; color:var(--dash-text-muted); text-align:center;">
                    This comprehensive audit trail is generated in real-time by Amazon Bedrock agents.
                </div>
            </div>
        </div>
    `;
};

async function fetchAgentLogs(ticketId) {
    const container = document.getElementById('agent-logs-container');
    if (!container) return;
    try {
        const res = await fetch(`${API_BASE}/admin/tickets/${ticketId}/agent-logs`);
        const data = await res.json();
        const logs = data.logs || [];
        if (!logs.length) {
            container.innerHTML = '<div style="color:var(--dash-text-muted);font-style:italic;">No agent logs yet. KYC check will run automatically after signup.</div>';
            return;
        }

        // Group by stage
        const byStage = {};
        logs.forEach(log => {
            const stageKey = log.stage === 1 ? '1 — KYC Screening' : log.stage === 2 ? '2 — AML Risk Profiling' : `${log.stage} — Orchestrator`;
            if (!byStage[stageKey]) byStage[stageKey] = [];
            byStage[stageKey].push(log);
        });

        let html = '';
        for (const [stageName, entries] of Object.entries(byStage)) {
            html += `<div style="margin-bottom:16px;">
                <div style="font-size:0.75rem;font-weight:700;color:var(--dash-text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:4px;">Stage ${stageName}</div>`;
            entries.forEach(log => {
                const flags = Array.isArray(log.flags) && log.flags.length
                    ? `<div style="margin-top:4px;color:#f59e0b;font-size:0.75rem;">⚠ ${log.flags.join(' | ')}</div>` : '';
                html += `<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
                    <div style="min-width:160px;font-weight:600;color:var(--dash-text);">${(log.check_name || '').replace(/_/g, ' ')}</div>
                    <div style="flex:1;">
                        ${agentRiskBadge(log.risk_level)}
                        <span style="margin-left:8px;font-size:0.75rem;color:var(--dash-text-muted);">${log.recommendation || ''}</span>
                        <div style="margin-top:4px;color:var(--dash-text-muted);font-size:0.78rem;">${log.ai_summary || ''}</div>
                        ${renderAgentEvidence(log)}
                        ${flags}
                    </div>
                    <div style="font-size:0.7rem;color:var(--dash-text-muted);min-width:80px;text-align:right;">${log.duration_ms || 0}ms</div>
                </div>`;
            });
            html += '</div>';
        }
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div style="color:#ef4444;font-size:0.8rem;">Failed to load agent logs: ${err.message}</div>`;
    }
}

async function takeAction(ticketId, action) {
    const remarks = prompt(`Enter remarks for action: ${action.toUpperCase()} (optional):\n`);
    if (remarks === null) return; // user cancelled

    try {
        const res = await fetch(`${API_BASE}/admin/tickets/${ticketId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, remarks: remarks || '' })
        });

        if (res.ok) {
            await fetchTickets();
            await loadTicket(ticketId);
        } else {
            const err = await res.json();
            alert('Action failed: ' + (err.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Connection error: ' + err.message);
    }
}

// Filter buttons
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            fetchTickets(btn.dataset.status || '');
        });
    });
});
