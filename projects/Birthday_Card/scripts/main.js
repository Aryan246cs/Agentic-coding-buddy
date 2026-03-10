// scripts/main.js
// Interactive behavior for the birthday card
// Assumes that startConfetti and stopConfetti are available globally (loaded via assets/confetti.js)
// Also assumes html2canvas is loaded globally via a CDN script.

// -----------------------------------------------------------------------------
// DOM element references
// -----------------------------------------------------------------------------
const greetingEl = document.getElementById('greeting');
const messageEl = document.getElementById('message');
const downloadBtn = document.getElementById('download-btn');
const shareTwitter = document.getElementById('share-twitter');
const shareFacebook = document.getElementById('share-facebook');
const cardEl = document.getElementById('card');

let currentTheme = null;

// -----------------------------------------------------------------------------
// Helper: ordinal suffix for numbers (1st, 2nd, 3rd, 4th, ...)
// -----------------------------------------------------------------------------
function ordinalSuffix(i) {
  const j = i % 10,
    k = i % 100;
  if (j === 1 && k !== 11) return `${i}st`;
  if (j === 2 && k !== 12) return `${i}nd`;
  if (j === 3 && k !== 13) return `${i}rd`;
  return `${i}th`;
}

// -----------------------------------------------------------------------------
// Set greeting and message text
// -----------------------------------------------------------------------------
function setGreeting(name, age) {
  const ageText = ordinalSuffix(age);
  greetingEl.textContent = `Happy ${ageText} Birthday, ${name}!`;
  messageEl.textContent = `Wishing you an amazing year ahead, ${name}.`;
}

// -----------------------------------------------------------------------------
// Apply theme colours via CSS custom properties
// -----------------------------------------------------------------------------
function applyTheme(theme) {
  if (!theme) return;
  const root = document.documentElement;
  root.style.setProperty('--primary-color', theme.primary);
  root.style.setProperty('--secondary-color', theme.secondary);
  root.style.setProperty('--background-color', theme.background);
  currentTheme = theme; // store for later use (e.g., confetti colours)
}

// -----------------------------------------------------------------------------
// Initialise confetti animation and optional background animation
// -----------------------------------------------------------------------------
function initAnimations() {
  if (!currentTheme) return;
  // Start confetti with theme colours
  if (typeof window.startConfetti === 'function') {
    window.startConfetti({ colors: [currentTheme.primary, currentTheme.secondary] });
  } else {
    console.warn('startConfetti function not found.');
  }

  // Optional subtle background animation – toggle a class that could be defined in CSS
  // Here we simply ensure the gradient animation defined in style.css runs (it already does).
}

// -----------------------------------------------------------------------------
// Handle card download as PNG using html2canvas
// -----------------------------------------------------------------------------
function handleDownload() {
  if (typeof html2canvas !== 'function') {
    console.error('html2canvas library is required for downloading the card.');
    return;
  }

  html2canvas(cardEl, { backgroundColor: null })
    .then((canvas) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          console.error('Failed to create blob from canvas.');
          return;
        }
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'Robin_21_Birthday.png';
        // Append to DOM to trigger click in Firefox
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      });
    })
    .catch((err) => console.error('Error generating card image:', err));
}

// -----------------------------------------------------------------------------
// Setup social sharing URLs for Twitter and Facebook
// -----------------------------------------------------------------------------
function setupSocialSharing() {
  const pageUrl = encodeURIComponent(window.location.href);
  const text = encodeURIComponent(greetingEl.textContent || 'Happy Birthday!');

  // Twitter share URL (using intent)
  const twitterUrl = `https://twitter.com/intent/tweet?text=${text}&url=${pageUrl}`;
  shareTwitter.href = twitterUrl;
  shareTwitter.target = '_blank';
  shareTwitter.rel = 'noopener noreferrer';

  // Facebook share URL (using sharer.php)
  const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${pageUrl}&quote=${text}`;
  shareFacebook.href = facebookUrl;
  shareFacebook.target = '_blank';
  shareFacebook.rel = 'noopener noreferrer';
}

// -----------------------------------------------------------------------------
// Event listeners
// -----------------------------------------------------------------------------
downloadBtn.addEventListener('click', handleDownload);

// -----------------------------------------------------------------------------
// Initialise everything once DOM is ready
// -----------------------------------------------------------------------------
function initCard() {
  setGreeting('Robin', 21);
  applyTheme({ primary: '#ff4081', secondary: '#ff80ab', background: '#fff0f5' });
  initAnimations();
  setupSocialSharing();
}

document.addEventListener('DOMContentLoaded', initCard);

// Export for potential external use (e.g., tests or other modules)
if (typeof window !== 'undefined') {
  window.initCard = initCard;
}
