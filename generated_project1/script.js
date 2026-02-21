// script.js – Interactivity for the Birthday Card
// No external dependencies; vanilla DOM manipulation only.

/**
 * Initializes the card by attaching event listeners.
 * Exported via `window.initializeCard` for external testing.
 */
function initializeCard() {
  // Cache DOM elements for efficiency
  const nameInput = document.getElementById('nameInput');
  const submitBtn = document.getElementById('submitBtn');
  const messageDiv = document.getElementById('message');

  /**
   * Handles form submission (button click or Enter key).
   * @param {Event} event
   */
  function handleSubmit(event) {
    // Prevent any default button behavior (e.g., form submission)
    event.preventDefault();

    const name = nameInput.value.trim();
    if (!name) {
      // Optional: add a brief shake animation if the input is empty.
      // The CSS for .shake is not defined in the stylesheet, but adding
      // a temporary class will not break anything.
      nameInput.classList.add('shake');
      setTimeout(() => nameInput.classList.remove('shake'), 300);
      return;
    }

    const message = `Happy Birthday, ${name}! 🎉`;
    messageDiv.textContent = message;

    // Reveal the message with animation – remove hidden, add reveal.
    messageDiv.classList.remove('hidden');
    // Force reflow to restart animation if needed
    void messageDiv.offsetWidth; // eslint-disable-line no-unused-expressions
    messageDiv.classList.add('reveal');
  }

  // Click on the button
  submitBtn.addEventListener('click', handleSubmit);

  // Press Enter while focused on the input
  nameInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
      handleSubmit(e);
    }
  });
}

// Ensure the init runs after the DOM is ready.
document.addEventListener('DOMContentLoaded', initializeCard);

// Export for external usage (e.g., tests)
window.initializeCard = initializeCard;
