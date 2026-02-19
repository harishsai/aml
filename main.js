// Custom Cursor Interaction
const dot = document.querySelector('.cursor-dot');
const outline = document.querySelector('.cursor-outline');

window.addEventListener('mousemove', (e) => {
    // Show cursor on first movement
    if (dot.style.opacity !== '1') {
        dot.style.opacity = '1';
        outline.style.opacity = '1';
    }

    gsap.to(dot, { x: e.clientX, y: e.clientY, xPercent: -50, yPercent: -50, duration: 0 });
    gsap.to(outline, { x: e.clientX, y: e.clientY, xPercent: -50, yPercent: -50, duration: 0.15 });
});

// Navigation Hide/Show on Scroll
let lastScroll = 0;
const nav = document.querySelector('.nav');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;

    // Glass background on scroll
    if (currentScroll > 50) {
        nav.classList.add('nav-scrolled');
    } else {
        nav.classList.remove('nav-scrolled');
    }

    // Hide/Show logic
    if (currentScroll > lastScroll && currentScroll > 100) {
        // Scrolling down
        nav.classList.add('nav-hidden');
    } else {
        // Scrolling up
        nav.classList.remove('nav-hidden');
    }

    lastScroll = currentScroll;
});

// GSAP Animations
gsap.registerPlugin(ScrollTrigger);

// Hero Entrance
const tl = gsap.timeline();
tl.from('.hero-title', {
    y: 100,
    opacity: 0,
    duration: 1.2,
    ease: "power4.out"
})
    .from('.hero-pre', {
        y: 20,
        opacity: 0,
        duration: 0.8
    }, "-=0.8")
    .from('.hero-subtitle', {
        y: 20,
        opacity: 0,
        duration: 0.8
    }, "-=0.6")
    .from('.hero-cta', {
        y: 20,
        opacity: 0,
        duration: 0.8
    }, "-=0.6");

// Scroll Animations for Pain Points
gsap.fromTo('.pain-card',
    { y: 60, opacity: 0 },
    {
        y: 0,
        opacity: 1,
        duration: 1,
        stagger: 0.1,
        delay: 0.5,
        ease: "power4.out",
        scrollTrigger: {
            trigger: '.pain-grid',
            start: 'top 90%',
            once: true,
            onEnter: () => ScrollTrigger.refresh()
        }
    }
);

// Demo Section Onboarding Logic
function nextStep(stepNum) {
    updateUI(stepNum);
}

function jumpToStep(stepNum) {
    updateUI(stepNum);
}

function updateUI(stepNum) {
    // Update roadmap steps UI
    document.querySelectorAll('.roadmap-step').forEach((s, idx) => {
        if (idx + 1 === stepNum) {
            s.classList.add('active');
        } else {
            s.classList.remove('active');
        }
    });

    // Update content UI
    document.querySelectorAll('.step-content').forEach(c => {
        c.classList.remove('active');
        gsap.killTweensOf(c); // Stop any running animations
    });

    const nextStepEl = document.getElementById(`step-${stepNum}`);
    nextStepEl.classList.add('active');

    // GSAP Entrance with fromTo for explicit state control
    gsap.fromTo(nextStepEl,
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.8, ease: "power3.out", clearProps: "all" }
    );

    // Special behavior for progress line
    const totalSteps = 4;
    const progress = ((stepNum - 1) / (totalSteps - 1)) * 100;

    // Trigger AI Agent Simulation
    simulateAgent(stepNum);
}

function simulateAgent(stepNum) {
    const statusText = document.getElementById('ai-status-text');
    const logs = {
        1: [
            "Initializing Global Registry bridge...",
            "Connecting to Jurisdiction Data Lake...",
            "Extracting Entity Metadata...",
            "Data Sourcing: SUCCESS"
        ],
        2: [
            "Awaiting corporate legal filings...",
            "Document detected: Certificate of Inc.",
            "AI OCR Engine: Processing...",
            "Data Extraction: 98% Confidence",
            "Classification: LEGAL_CORPORATE"
        ],
        3: [
            "Cross-referencing Global Sanctions List...",
            "AI Agent Kyra: Analyzing Match Risk...",
            "Significance Check: NO CRITICAL SHIFTS",
            "Screening: CLEAR"
        ],
        4: [
            "Monitoring process readiness...",
            "Pre-filling Go-Live checklist...",
            "Autocompleting Operational Hand-off...",
            "Agent: READY FOR ACTIVATION"
        ]
    };

    const stepAgentId = { 1: 'vetting', 2: 'app', 3: 'readiness', 4: 'active' };
    const agentId = stepAgentId[stepNum];

    if (agentId) {
        const agentWindow = document.getElementById(`agent-${agentId}`);
        const statusEl = agentWindow.querySelector('.agent-status');
        const logContainer = document.getElementById(`logs-${agentId}`);
        const scannerLine = document.querySelector('.scanner-line');

        statusEl.innerText = "PROCESSING...";
        statusText.innerText = `AI Agent: ${agentId.toUpperCase()} Processing...`;

        // Trigger Scanner Animation for Phase 2 (Document Agent)
        if (stepNum === 2) {
            scannerLine.style.animation = "scanLineAnim 3s infinite linear";
        } else {
            scannerLine.style.animation = "none";
        }

        logs[stepNum].forEach((log, index) => {
            setTimeout(() => {
                addAgentLog(logContainer, log);
                if (index === logs[stepNum].length - 1) {
                    statusEl.innerText = "COMPLETED";
                    statusText.innerText = "AI Agent: Monitoring Session...";
                    if (stepNum === 2) scannerLine.style.animation = "none";
                }
            }, (index + 1) * 1200);
        });
    }
}

function addAgentLog(container, text) {
    const p = document.createElement('p');
    p.className = 'log-entry new';
    p.innerText = `> ${text}`;
    container.appendChild(p);
    container.scrollTop = container.scrollHeight;
}

// Hover effects for magnetic elements
document.querySelectorAll('.btn-primary, .nav-link, .roadmap-step, label, .pain-card').forEach(link => {
    link.addEventListener('mouseenter', () => {
        outline.classList.add('arrow-active');
    });
    link.addEventListener('mouseleave', () => {
        outline.classList.remove('arrow-active');
    });
});

// Magnetic effect for labels (subtle)
document.querySelectorAll('label').forEach(label => {
    label.addEventListener('mousemove', (e) => {
        const rect = label.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;
        gsap.to(label, {
            x: x * 0.3,
            y: y * 0.3,
            duration: 0.3,
            ease: "power2.out"
        });
    });
    label.addEventListener('mouseleave', () => {
        gsap.to(label, { x: 0, y: 0, duration: 0.5, ease: "elastic.out(1, 0.3)" });
    });
});

// Signup Modal Logic
function openSignup() {
    document.getElementById('signup-modal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeSignup() {
    document.getElementById('signup-modal').classList.remove('active');
    document.body.style.overflow = 'auto';
}

function submitSignup() {
    const btn = document.querySelector('.signup-form .btn-primary');
    const originalText = btn.innerText;

    btn.innerText = "INITIALIZING ENTITY SCAN...";
    btn.style.opacity = "0.7";
    btn.disabled = true;

    setTimeout(() => {
        btn.innerText = "REGISTRATION SUCCESSFUL";
        btn.style.background = "#00ffa3";
        btn.style.color = "#000";

        setTimeout(() => {
            closeSignup();
            // Reset button
            btn.innerText = originalText;
            btn.style.background = "var(--accent)";
            btn.disabled = false;
            btn.style.opacity = "1";

            // Jump to first step of demo
            window.location.hash = "#demo";
            jumpToStep(1);
        }, 1500);
    }, 2000);
}

// Chat Widget Logic
function toggleChat() {
    const chatWindow = document.getElementById('chat-window');
    chatWindow.classList.toggle('active');
}

function handleChatKey(e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (message) {
        addChatMessage('user', message);
        input.value = '';

        // Simulate AI Response
        setTimeout(() => {
            const responses = [
                "I'm looking into your onboarding status. One moment...",
                "The Document Agent is currently verifying your Certificate of Incorporation. You're 75% complete!",
                "Great question! Strategic Onboarding usually takes 3 to 5 business days for full activation.",
                "Would you like me to schedule a call with your Strategic Lead?",
                "All systems are green! You're on track for your Go-Live date."
            ];
            const randomResponse = responses[Math.floor(Math.random() * responses.length)];
            addChatMessage('ai', randomResponse);
        }, 1200);
    }
}

function addChatMessage(type, text) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    msgDiv.innerHTML = `<p>${text}</p>`;

    container.appendChild(msgDiv);

    // GSAP Animation for message
    gsap.from(msgDiv, {
        y: 10,
        opacity: 0,
        duration: 0.4,
        ease: "power2.out"
    });

    container.scrollTop = container.scrollHeight;
}
