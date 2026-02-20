/** PREMIUM ADMIN DASHBOARD LOGIC **/
let currentTickets = [];
let activeTicketId = null;

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
        const url = statusFilter ? `http://localhost:8000/admin/tickets?status=${statusFilter}` : 'http://localhost:8000/admin/tickets';
        const response = await fetch(url);
        const data = await response.json();

        if (data.status === 'success') {
            currentTickets = data.tickets;
            renderTickets(currentTickets);
            updateStats(currentTickets);
        }
    } catch (error) {
        console.error("Fetch error:", error);
        listContainer.innerHTML = '<div style="padding: 60px; text-align: center; color: #EF4444;">Infrastructure timeout. Verify backend services.</div>';
    }
}

function renderTickets(tickets) {
    const listContainer = document.getElementById('ticket-list-container');
    if (tickets.length === 0) {
        listContainer.innerHTML = '<div style="padding: 60px; text-align: center; color: var(--dash-text-muted);">No active cases matching current filter.</div>';
        return;
    }

    listContainer.innerHTML = tickets.map(t => `
        <div class="table-row" onclick="openTicketDetail('${t.id}')">
            <span class="entity-info">${t.company_name}</span>
            <span class="tracking-id">${t.tracking_id}</span>
            <span style="font-size: 0.85rem; color: var(--dash-text-muted);">${new Date(t.submitted_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            <span><span class="badge badge-${getStatusClass(t.status)}">${t.status.replace(/_/g, ' ')}</span></span>
            <span style="text-align: right;">
                <button class="btn-premium" style="font-size: 0.7rem; padding: 6px 12px;">REVIEW</button>
            </span>
        </div>
    `).join('');

    // GSAP Entrance
    gsap.from('.table-row', {
        opacity: 0,
        y: 10,
        duration: 0.5,
        stagger: 0.05,
        ease: "power2.out"
    });
}

function getStatusClass(status) {
    switch (status) {
        case 'PENDING_REVIEW': return 'pending';
        case 'APPROVED': return 'approved';
        case 'REJECTED': return 'rejected';
        case 'VETTING_IN_PROGRESS': return 'vetting';
        case 'CLARIFICATION_REQUIRED': return 'clarification';
        default: return 'pending';
    }
}

async function openTicketDetail(id) {
    activeTicketId = id;
    const overlay = document.getElementById('ticket-detail-overlay');
    const content = document.getElementById('ticket-detail-content');

    content.innerHTML = '<div style="padding-top: 40px; color: var(--dash-text-muted);">Initiating case review...</div>';
    overlay.classList.add('active');

    try {
        const response = await fetch(`http://localhost:8000/admin/tickets/${id}`);
        const data = await response.json();

        if (data.status === 'success') {
            const t = data.ticket;
            content.innerHTML = `
                <div class="case-header">
                    <span class="badge badge-${getStatusClass(t.status)}" style="float:right">${t.status.replace(/_/g, ' ')}</span>
                    <h2 style="font-size: 1.8rem; margin-bottom: 8px;">${t.company_name}</h2>
                    <p class="tracking-id" style="font-size: 0.9rem;">${t.tracking_id}</p>
                </div>

                <div class="case-module">
                    <h4 class="module-title">Entity Specification</h4>
                    <div class="data-grid">
                        <div class="data-row"><span class="data-label">Full Name</span><span class="data-value">${t.company_name}</span></div>
                        <div class="data-row"><span class="data-label">LEI Identifier</span><span class="data-value">${t.lei_identifier}</span></div>
                        <div class="data-row"><span class="data-label">Entity Classification</span><span class="data-value">${t.entity_type.toUpperCase()}</span></div>
                        <div class="data-row"><span class="data-label">Primary Email</span><span class="data-value">${t.email || 'N/A'}</span></div>
                        <div class="data-row"><span class="data-label">Jurisdiction</span><span class="data-value">${t.country}</span></div>
                    </div>
                </div>

                <div class="case-module">
                    <h4 class="module-title">Business Logic</h4>
                    <div class="data-grid">
                        <div class="data-row"><span class="data-label">Activity Type</span><span class="data-value">${t.business_activity}</span></div>
                        <div class="data-row"><span class="data-label">Funds Source</span><span class="data-value">${t.source_of_funds}</span></div>
                    </div>
                </div>

                <div class="case-module">
                    <h4 class="module-title">Compliance Documentation</h4>
                    <div style="display: grid; gap: 12px; margin-top: 16px;">
                        <div class="doc-item" onclick="viewDoc('${t.id}', 'bod')">
                            <span>📄</span>
                            <div style="flex: 1;"><p style="font-weight: 600; font-size: 0.85rem;">Board of Directors</p><p style="font-size: 0.7rem; color: var(--dash-text-muted);">Validated Multi-page PDF</p></div>
                            <span class="badge badge-approved" style="font-size: 0.6rem;">VIEW</span>
                        </div>
                        <div class="doc-item" onclick="viewDoc('${t.id}', 'financials')">
                            <span>📉</span>
                            <div style="flex: 1;"><p style="font-weight: 600; font-size: 0.85rem;">Audited Financials</p><p style="font-size: 0.7rem; color: var(--dash-text-muted);">Certified Statement</p></div>
                            <span class="badge badge-approved" style="font-size: 0.6rem;">VIEW</span>
                        </div>
                        <div class="doc-item" onclick="viewDoc('${t.id}', 'ownership')">
                            <span>🏢</span>
                            <div style="flex: 1;"><p style="font-weight: 600; font-size: 0.85rem;">Ownership Structure</p><p style="font-size: 0.7rem; color: var(--dash-text-muted);">UBO Declaration</p></div>
                            <span class="badge badge-approved" style="font-size: 0.6rem;">VIEW</span>
                        </div>
                    </div>
                </div>

                <div class="case-module" style="border-bottom: none;">
                    <h4 class="module-title">Decision Engine</h4>
                    <div class="action-grid">
                        <button class="btn-premium btn-primary" onclick="handleAction('${t.id}', 'approve')">APPROVE PARTNERSHIP</button>
                        <button class="btn-premium" onclick="promptAction('${t.id}', 'clarify')" style="color: var(--clr-clarify); border-color: var(--clr-clarify);">REQUEST DATA</button>
                        <button class="btn-premium" onclick="promptAction('${t.id}', 'reject')" style="color: var(--clr-rejected); border-color: var(--clr-rejected); margin-top: 8px;">REJECT APPLICATION</button>
                        <button class="btn-premium btn-full" onclick="closeTicketDetail()" style="margin-top: 12px;">CLOSE REVIEW</button>
                    </div>
                </div>

                <div class="case-module" style="background: #F8FAFC; padding: 24px; border-radius: var(--radius-lg); border: none;">
                    <h4 class="module-title" style="margin-bottom: 20px;">Master Audit Trail</h4>
                    ${t.history.map((h, i) => `
                        <div style="padding-left: 20px; border-left: 2px solid ${i === 0 ? 'var(--dash-primary)' : 'var(--dash-border)'}; position: relative; padding-bottom: 24px;">
                            <div style="position: absolute; left: -6px; top: 0; width: 10px; height: 10px; border-radius: 50%; background: ${i === 0 ? 'var(--dash-primary)' : 'var(--dash-border)'};"></div>
                            <p style="font-size: 0.7rem; color: var(--dash-text-muted); font-weight: 600; text-transform: uppercase;">${new Date(h.action_timestamp).toLocaleString()}</p>
                            <p style="font-size: 0.85rem; font-weight: 600; margin: 4px 0;">${h.old_status || 'INIT'} <span style="color: var(--dash-text-muted);">→</span> ${h.new_status}</p>
                            ${h.remarks ? `<div style="margin-top: 8px; padding: 12px; background: white; border-radius: 6px; border: 1px solid var(--dash-border); font-size: 0.8rem; font-style: italic;">"${h.remarks}"</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;

            // GSAP Entrance
            gsap.from('#ticket-detail-content > *', {
                opacity: 0,
                x: 30,
                duration: 0.5,
                stagger: 0.1,
                ease: "power2.out"
            });
        }
    } catch (e) {
        content.innerHTML = '<div style="color: #EF4444; padding-top: 40px;">State synchronization error.</div>';
    }
}

function closeTicketDetail() {
    document.getElementById('ticket-detail-overlay').classList.remove('active');
}

function viewDoc(id, type) {
    window.open(`http://localhost:8000/admin/tickets/${id}/docs/${type}`, '_blank');
}

function filterTickets(status) {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    event.currentTarget.classList.add('active');
    fetchTickets(status);
}

function updateStats(tickets) {
    document.getElementById('count-all').innerText = tickets.length;
}

let pendingAction = null;
function promptAction(id, action) {
    pendingAction = { id, action };
    document.getElementById('remarks-title').innerText = `REASON FOR ${action.toUpperCase()}`;
    document.getElementById('remarks-modal').style.display = 'flex';
}

function closeRemarksModal() {
    document.getElementById('remarks-modal').style.display = 'none';
    pendingAction = null;
}

document.getElementById('confirm-remark-btn').onclick = function () {
    const remarks = document.getElementById('remarks-input').value;
    if (pendingAction) {
        handleAction(pendingAction.id, pendingAction.action, remarks);
        closeRemarksModal();
    }
};

async function handleAction(id, action, remarks = '') {
    try {
        const response = await fetch(`http://localhost:8000/admin/tickets/${id}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, remarks })
        });
        const data = await response.json();
        if (data.status === 'success') {
            openTicketDetail(id);
            fetchTickets(''); // Refresh main list
        }
    } catch (err) { alert("Operational failure. Check system logs."); }
}


