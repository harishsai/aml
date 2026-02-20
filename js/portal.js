/** PARTICIPANT PORTAL LOGIC **/
document.addEventListener('DOMContentLoaded', () => {
    loadParticipantData();
});

async function loadParticipantData() {
    // In a real app, this would fetch based on the logged-in session
    // For this demo, we can fetch the latest ticket or a specific ID from localStorage
    try {
        const response = await fetch('http://localhost:8000/admin/tickets');
        const data = await response.json();

        if (data.status === 'success' && data.tickets.length > 0) {
            // Pick the most recent one for the demo
            const latest = data.tickets[0];
            updatePortalUI(latest);
        }
    } catch (error) {
        console.error("Portal data fetch error:", error);
    }
}

function updatePortalUI(ticket) {
    document.getElementById('tracking-badge').innerText = `ID: ${ticket.tracking_id}`;
    document.getElementById('entity-name').innerText = ticket.company_name;
    document.getElementById('current-status').innerText = ticket.status.replace('_', ' ');
    document.getElementById('current-status').className = `value tag ${getStatusColorClass(ticket.status)}`;

    // Custom messaging based on status
    const actionLabel = document.getElementById('next-action');
    if (ticket.status === 'CLARIFICATION_REQUIRED') {
        actionLabel.innerHTML = '<span style="color:red; font-weight:700;">Action Required:</span> Please check your email for clarification prompts.';
    } else if (ticket.status === 'APPROVED') {
        actionLabel.innerText = 'Congratulations! Your institution is fully onboarded. Accessing gateway...';
    }
}

function getStatusColorClass(status) {
    switch (status) {
        case 'PENDING_REVIEW': return 'blue';
        case 'APPROVED': return 'green';
        case 'REJECTED': return 'red';
        case 'CLARIFICATION_REQUIRED': return 'orange';
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
        appendMessage('ai', "I'm monitoring your application. It's currently in the vetting phase with our Operations team.");
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
