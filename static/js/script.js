// static/js/script.js

// --- COMET ANIMATION LOGIC ---
// (Only runs if canvas exists on the page)
const canvas = document.getElementById('cometCanvas');
if (canvas) {
    const ctx = canvas.getContext('2d');
    let w, h;
    let comets = [];

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    class Comet {
        constructor() {
            this.x = Math.random() * w;
            this.y = Math.random() * h;
            this.length = Math.random() * 80 + 10;
            this.speed = Math.random() * 2 + 1.5;
            this.opacity = Math.random() * 0.5 + 0.1;
            this.angle = Math.PI / 4 + (Math.random() * 0.1 - 0.05); 
            this.dx = Math.cos(this.angle) * this.speed;
            this.dy = Math.sin(this.angle) * this.speed;
        }

        update() {
            this.x += this.dx;
            this.y += this.dy;
            if (this.x > w + 100 || this.y > h + 100) {
                this.x = Math.random() * w * 1.5 - w;
                this.y = -100;
                this.opacity = Math.random() * 0.5 + 0.5;
            }
        }

        draw() {
            ctx.beginPath();
            const headX = this.x;
            const headY = this.y;
            const tailX = this.x - Math.cos(this.angle) * this.length;
            const tailY = this.y - Math.sin(this.angle) * this.length;
            const gradient = ctx.createLinearGradient(headX, headY, tailX, tailY);
            gradient.addColorStop(0, `rgba(255, 255, 255, ${this.opacity})`);
            gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
            ctx.strokeStyle = gradient;
            ctx.lineWidth = 2;
            ctx.moveTo(headX, headY);
            ctx.lineTo(tailX, tailY);
            ctx.stroke();
        }
    }

    function initComets() {
        comets = [];
        for (let i = 0; i < 15; i++) {
            comets.push(new Comet());
        }
    }

    function animate() {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
        ctx.fillRect(0, 0, w, h);
        comets.forEach(comet => {
            comet.update();
            comet.draw();
        });
        requestAnimationFrame(animate);
    }

    initComets();
    animate();
}

// --- FORM TOGGLE LOGIC (Index page specific) ---
function setRole(role) {
    const candidateSection = document.getElementById('candidateSection');
    const recruiterSection = document.getElementById('recruiterSection');
    // Guards in case these elements don't exist on other pages
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

    if (type === 'login') {
        loginWrapper.style.display = 'block';
        signupWrapper.style.display = 'none';
        btnLogin.classList.add('border-b-2', 'border-white', 'font-bold');
        btnLogin.classList.remove('opacity-50');
        btnSignup.classList.remove('border-b-2', 'border-white', 'font-bold');
        btnSignup.classList.add('opacity-50');
    } else {
        loginWrapper.style.display = 'none';
        signupWrapper.style.display = 'block';
        btnSignup.classList.add('border-b-2', 'border-white', 'font-bold');
        btnSignup.classList.remove('opacity-50');
        btnLogin.classList.remove('border-b-2', 'border-white', 'font-bold');
        btnLogin.classList.add('opacity-50');
    }
}