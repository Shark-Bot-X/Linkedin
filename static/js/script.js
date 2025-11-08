// static/js/script.js

// --- UI Logic: Hide Loading Overlay ---
window.addEventListener('load', () => {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        // Hide overlay after content loads
        setTimeout(() => {
            loadingOverlay.classList.add('hidden');
        }, 500); 
    }
});


// --- SQUARED BACKGROUND ANIMATION LOGIC ---
const canvas = document.getElementById('cometCanvas');
if (canvas) {
    const ctx = canvas.getContext('2d');
    let w, h;
    let particles = [];
    // Define accent color here for use in canvas
    const ACCENT_COLOR = '#b19eef'; 

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    class SquareParticle {
        constructor() {
            this.size = Math.random() * 2 + 1; // Small square size
            this.x = Math.random() * w;
            this.y = Math.random() * h;
            this.speed = Math.random() * 0.5 + 0.1; // Slower, subtle movement
            this.opacity = Math.random() * 0.4 + 0.1;
            this.angle = Math.PI * 0.25; // Gentle diagonal drift
            this.dx = Math.cos(this.angle) * this.speed;
            this.dy = Math.sin(this.angle) * this.speed;
        }

        update() {
            this.x += this.dx;
            this.y += this.dy;
            
            // Loop particles back from the top-left when they exit bottom-right
            if (this.x > w + this.size * 2) {
                this.x = -this.size * 2;
            }
            if (this.y > h + this.size * 2) {
                this.y = -this.size * 2;
            }
        }

        draw() {
            // Draw the small box using the accent color
            ctx.fillStyle = `rgba(177, 158, 239, ${this.opacity})`; 
            ctx.fillRect(this.x, this.y, this.size, this.size);
        }
    }

    function initParticles() {
        particles = [];
        // Denser field of particles/boxes
        for (let i = 0; i < 200; i++) {
            particles.push(new SquareParticle());
        }
    }

    function animate() {
        // Use a very dark, slightly transparent overlay to create subtle trails/fading
        ctx.fillStyle = 'rgba(0, 0, 0, 0.05)'; 
        ctx.fillRect(0, 0, w, h);
        
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        requestAnimationFrame(animate);
    }

    initParticles();
    animate();
}
// --- END SQUARED BACKGROUND ANIMATION LOGIC ---


// --- FORM TOGGLE LOGIC (Index page specific) ---
function setRole(role) {
    const candidateSection = document.getElementById('candidateSection');
    const recruiterSection = document.getElementById('recruiterSection');
    if (!candidateSection || !recruiterSection) return; 

    const btnCandidate = document.getElementById('btn-role-candidate');
    const btnRecruiter = document.getElementById('btn-role-recruiter');

    if (role === 'candidate') {
        candidateSection.style.display = 'block';
        recruiterSection.style.display = 'none';
        btnCandidate.classList.add('active-tab');
        btnRecruiter.classList.remove('active-tab');
    } else {
        candidateSection.style.display = 'none';
        recruiterSection.style.display = 'block';
        btnRecruiter.classList.add('active-tab');
        btnCandidate.classList.remove('active-tab');
    }
}

function setFormType(role, type) {
    const loginWrapper = document.getElementById(`${role}LoginFormWrapper`);
    const signupWrapper = document.getElementById(`${role}SignupFormWrapper`);
    if (!loginWrapper || !signupWrapper) return;

    const btnLogin = document.getElementById(`btn-${role}-login`);
    const btnSignup = document.getElementById(`btn-${role}-signup`);

    // Use the accent color class defined in Tailwind config in layout.html
    const activeBorderClass = 'border-accent-purple'; 

    if (type === 'login') {
        loginWrapper.style.display = 'block';
        signupWrapper.style.display = 'none';
        // Active border should be purple
        btnLogin.classList.add('border-b-2', activeBorderClass, 'font-bold');
        btnLogin.classList.remove('opacity-50', 'border-white');
        
        btnSignup.classList.remove('border-b-2', activeBorderClass, 'font-bold');
        btnSignup.classList.add('opacity-50');
    } else {
        loginWrapper.style.display = 'none';
        signupWrapper.style.display = 'block';
        // Active border should be purple
        btnSignup.classList.add('border-b-2', activeBorderClass, 'font-bold');
        btnSignup.classList.remove('opacity-50', 'border-white');
        
        btnLogin.classList.remove('border-b-2', activeBorderClass, 'font-bold');
        btnLogin.classList.add('opacity-50');
    }
}