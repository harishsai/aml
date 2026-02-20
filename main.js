// Navigation Hide/Show on Scroll
let lastScroll = 0;
const nav = document.querySelector('.nav');

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    const nav = document.querySelector('.nav');

    if (nav) {
        if (currentScroll > 50) {
            nav.classList.add('nav-scrolled');
        } else {
            nav.classList.remove('nav-scrolled');
        }

        if (currentScroll > lastScroll && currentScroll > 100) {
            nav.classList.add('nav-hidden');
        } else {
            nav.classList.remove('nav-hidden');
        }
    }
    lastScroll = currentScroll;
});

// GSAP Animations
if (typeof gsap !== 'undefined') {
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
                once: true
            }
        }
    );
}

// Persona Management
function openLogin() {
    document.getElementById('login-modal').classList.add('active');
}

function closeLogin() {
    document.getElementById('login-modal').classList.remove('active');
}

function loginAs(role) {
    // Redirect to standalone login page
    window.location.href = `login.html?role=${role}`;
}
