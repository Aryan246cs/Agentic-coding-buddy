// assets/confetti.js
// Lightweight confetti animation library
// Exposes two functions on the global window object: startConfetti(options) and stopConfetti()
// The library creates a canvas context on the <canvas id="confetti-canvas"> element and runs a simple particle system.

(() => {
  // Default configuration values
  const DEFAULTS = {
    particleCount: 150, // Number of particles per launch
    spread: 60, // Degrees of spread from the vertical
    duration: 5000, // How long the animation runs (ms). 0 = infinite until stopped
    colors: ["#FFC107", "#FF5722", "#4CAF50", "#2196F3", "#9C27B0", "#E91E63"], // Theme colors
    size: { min: 5, max: 12 }, // Particle size range (px)
    speed: { min: 2, max: 6 }, // Initial speed range (px per frame)
    gravity: 0.15, // Gravity per frame (px per frame²)
    friction: 0.99, // Horizontal friction per frame
  };

  let canvas, ctx;
  let particles = [];
  let animationId = null;
  let startTime = null;
  let running = false;
  let config = { ...DEFAULTS };

  /** Utility: random number in [min, max) */
  const rand = (min, max) => Math.random() * (max - min) + min;
  /** Utility: convert degrees to radians */
  const degToRad = (deg) => (deg * Math.PI) / 180;

  /** Initialise canvas and its size handling */
  const initCanvas = () => {
    const el = document.getElementById("confetti-canvas");
    if (!el) {
      console.warn("Confetti canvas element not found.");
      return false;
    }
    canvas = el;
    ctx = canvas.getContext("2d");
    const resize = () => {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
    };
    resize();
    window.addEventListener("resize", resize);
    return true;
  };

  /** Create a single particle based on the current config */
  const createParticle = () => {
    // Launch angle: upward (-90deg) plus/minus half the spread
    const angle = degToRad(rand(-config.spread / 2, config.spread / 2) - 90);
    const speed = rand(config.speed.min, config.speed.max);
    return {
      x: canvas.width / 2,
      y: canvas.height,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: rand(config.size.min, config.size.max),
      color: config.colors[Math.floor(rand(0, config.colors.length))],
      life: 0,
      // Approximate max frames based on duration (assuming ~60fps)
      maxLife: config.duration > 0 ? Math.ceil(config.duration / 16.67) : Infinity,
    };
  };

  /** Populate the particles array */
  const emitParticles = () => {
    particles = [];
    for (let i = 0; i < config.particleCount; i++) {
      particles.push(createParticle());
    }
  };

  /** Render a single animation frame */
  const render = (timestamp) => {
    if (!startTime) startTime = timestamp;
    const elapsed = timestamp - startTime;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Update and draw each particle
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      // Apply physics
      p.vy += config.gravity;
      p.vx *= config.friction;
      p.x += p.vx;
      p.y += p.vy;
      p.life++;

      // Draw as a small rotated rectangle (simple confetti look)
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.vx * 0.1);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.4);
      ctx.restore();

      // Remove if out of view or lived too long
      if (p.y - p.size > canvas.height || p.life > p.maxLife) {
        particles.splice(i, 1);
      }
    }

    // Determine whether we should keep animating
    const shouldContinue =
      (config.duration === 0 || elapsed < config.duration) && particles.length > 0 && running;
    if (shouldContinue) {
      animationId = requestAnimationFrame(render);
    } else {
      stopConfetti();
    }
  };

  /** Public API: start the confetti animation */
  const startConfetti = (options = {}) => {
    if (running) return; // Prevent multiple concurrent runs
    config = { ...DEFAULTS, ...options };
    if (!initCanvas()) return;
    emitParticles();
    running = true;
    startTime = null;
    animationId = requestAnimationFrame(render);
  };

  /** Public API: stop the confetti animation and clean up */
  const stopConfetti = () => {
    running = false;
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles = [];
  };

  // Expose the two functions on the global window object
  window.startConfetti = startConfetti;
  window.stopConfetti = stopConfetti;
})();
