/** PARTICIPANT PORTAL LOGIC — Phase-Aware */

// Status → phase mapping
const PHASE_MAP = {
    'PENDING_REVIEW': { step: 1, result: 'in_progress' },
    'KYC_COMPLETE': { step: 1, result: 'done' },
    'AML_IN_PROGRESS': { step: 2, result: 'in_progress' },
    'AML_COMPLETE': { step: 2, result: 'done' },
    'AML_REVIEW_READY': { step: 3, result: 'in_progress' },
    'CLARIFICATION_REQUIRED': { step: 1, result: 'clarify' },
    'APPROVED': { step: 3, result: 'approved' },
    'REJECTED': { step: 3, result: 'rejected' },
    'CANCELLED': { step: 3, result: 'rejected' },
};

const NEXT_ACTION_MSG = {
    'PENDING_REVIEW': '⏳ Our AI compliance system is running your KYC screening. You will receive an email once complete.',
    'KYC_COMPLETE': '✅ KYC screening complete. Our compliance team is reviewing the findings before proceeding to AML Risk Assessment.',
    'AML_IN_PROGRESS': '⏳ AML Risk Assessment is in progress. You will receive an email once complete.',
    'AML_COMPLETE': '✅ AML Risk Assessment complete. Our Compliance Officers are making the final decision.',
    'AML_REVIEW_READY': '⏳ Final compliance review in progress.',
    'CLARIFICATION_REQUIRED': '⚠️ Action Required: Our team needs clarification. Please check your email for details.',
    'APPROVED': '🎉 Congratulations! Your institution has been approved. Your relationship manager will contact you shortly.',
    'REJECTED': '❌ Your application has not been approved. Please contact our compliance team if you have questions.',
    'CANCELLED': 'Your application has been cancelled.',
};

document.addEventListener('DOMContentLoaded', () => {
    loadParticipantData();
});

// Dynamically determine the backend URL
const API_BASE = (window.location.protocol === 'file:' || window.location.port !== '8000')
    ? 'http://localhost:8000'
    : window.location.origin;

async function loadParticipantData() {
    const userId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
    if (!userId) {
        showError('Session expired. Please log in again.');
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/portal/status/${userId}`);
        if (!res.ok) {
            showError('Could not load your application status. Please try again.');
            return;
        }
        const data = await res.json();
        updatePortalUI(data.record);
    } catch (err) {
        console.error('Portal fetch error:', err);
        showError('Connection error. Please ensure the app is running.');
    }
}

function showError(msg) {
    const el = document.getElementById('next-action');
    if (el) el.innerHTML = `<span style="color:red;">${msg}</span>`;
}

function updatePortalUI(record) {
    const status = record.status || 'PENDING_REVIEW';

    // Tracking ID and company name
    const badge = document.getElementById('tracking-badge');
    if (badge) badge.innerText = `ID: ${record.tracking_id || 'N/A'}`;
    const name = document.getElementById('entity-name');
    if (name) name.innerText = record.company_name || '—';

    // Phase tracker
    renderPhaseTracker(status, record.ai_risk_level);

    // Next action message
    const actionEl = document.getElementById('next-action');
    if (actionEl) actionEl.innerHTML = NEXT_ACTION_MSG[status] || 'Your application is under review.';
}

function renderPhaseTracker(status, riskLevel) {
    const container = document.getElementById('phase-tracker');
    if (!container) return;

    const phase = PHASE_MAP[status] || { step: 1, result: 'in_progress' };

    const steps = [
        { num: 1, label: 'KYC Screening', desc: 'Identity & Sanctions' },
        { num: 2, label: 'AML Risk Assessment', desc: 'Country & Volume Risk' },
        { num: 3, label: 'Final Decision', desc: 'Compliance Officer Review' },
    ];

    const html = steps.map(s => {
        let icon, color, bg, borderColor;

        if (s.num < phase.step) {
            // Completed step
            icon = '✅'; color = '#22c55e'; bg = '#052e16'; borderColor = '#22c55e';
        } else if (s.num === phase.step) {
            // Current step
            if (phase.result === 'approved') {
                icon = '✅'; color = '#22c55e'; bg = '#052e16'; borderColor = '#22c55e';
            } else if (phase.result === 'rejected') {
                icon = '❌'; color = '#ef4444'; bg = '#3f0000'; borderColor = '#ef4444';
            } else if (phase.result === 'clarify') {
                icon = '⚠️'; color = '#f59e0b'; bg = '#422006'; borderColor = '#f59e0b';
            } else {
                icon = '⏳'; color = '#f59e0b'; bg = '#1c1c1c'; borderColor = '#f59e0b';
            }
        } else {
            // Future step
            icon = '⬜'; color = '#6b7280'; bg = '#111'; borderColor = '#2f2f2f';
        }

        // Show risk level badge on current completed step
        const riskBadge = (s.num === phase.step && riskLevel && phase.result === 'done') ||
            (s.num < phase.step) ? '' : '';
        const showRisk = s.num === phase.step && riskLevel;
        const riskHtml = showRisk ? `<span style="display:block;margin-top:6px;font-size:0.72rem;font-weight:700;color:${riskLevel === 'LOW' ? '#22c55e' : riskLevel === 'MEDIUM' ? '#f59e0b' : '#ef4444'
            };letter-spacing:0.5px;">${riskLevel} RISK</span>` : '';

        return `
            <div style="flex:1;text-align:center;position:relative;">
                <div style="width:52px;height:52px;border-radius:50%;background:${bg};border:2px solid ${borderColor};
                     display:flex;align-items:center;justify-content:center;font-size:1.4rem;margin:0 auto 10px;">
                    ${icon}
                </div>
                <div style="font-weight:700;font-size:0.85rem;color:${color};">${s.label}</div>
                <div style="font-size:0.75rem;color:#6b7280;margin-top:3px;">${s.desc}</div>
                ${riskHtml}
            </div>`;
    }).join(`<div style="flex:0 0 40px;display:flex;align-items:flex-start;padding-top:24px;color:#374151;">──</div>`);

    container.innerHTML = `<div style="display:flex;align-items:flex-start;gap:0;justify-content:center;padding:20px 0;">${html}</div>`;
}

function getStatusColorClass(status) {
    switch (status) {
        case 'PENDING_REVIEW': return 'blue';
        case 'APPROVED': return 'green';
        case 'REJECTED': return 'red';
        case 'CLARIFICATION_REQUIRED': return 'orange';
        case 'AML_STAGE1_COMPLETE': return 'blue';
        case 'AML_STAGE2_COMPLETE': return 'blue';
        default: return 'blue';
    }
}

/** Chat Logic **/
function handleChatKey(e) {
    if (e.key === 'Enter') sendChatMessage();
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    appendMessage('user', msg);
    input.value = '';

    setTimeout(() => {
        appendMessage('ai', "I'm monitoring your application. Our compliance team is working through the KYC and AML review process. You'll receive email updates at each stage.");
    }, 1000);
}

function appendMessage(type, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.innerHTML = `<p>${text}</p>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
