/*
 * Simple BODMAS Calculator - Core Logic & UI Interaction
 * ---------------------------------------------------
 * This script provides:
 *   1. Tokenizer – converts an expression string into an array of tokens.
 *   2. Shunting‑yard algorithm – converts infix tokens to postfix (RPN).
 *   3. Postfix evaluator – computes the numeric result from RPN.
 *   4. Expression evaluator – orchestrates the above with unified error handling.
 *   5. UI wiring – connects the calculator UI defined in index.html.
 *
 * All public helpers are attached to the `window` object for debugging
 * and potential external use.
 */

/* -------------------------------------------------------------------------- */
/*  Step 1: Tokenizer                                                       */
/* -------------------------------------------------------------------------- */
/**
 * Splits an arithmetic expression into tokens.
 * Supported tokens: numbers (including decimal), operators (+ - * / ^),
 * parentheses '(' ')'. Whitespace is ignored.
 *
 * @param {string} expr - The raw expression entered by the user.
 * @returns {string[]} Ordered array of token strings.
 * @throws {SyntaxError} If an unknown character is encountered.
 */
function tokenize(expr) {
  const tokens = [];
  const length = expr.length;
  let i = 0;

  while (i < length) {
    const ch = expr[i];

    // Skip whitespace
    if (/\s/.test(ch)) {
      i++;
      continue;
    }

    // Number (integer or decimal)
    if (/\d/.test(ch) || ch === '.') {
      let num = '';
      let dotCount = 0;
      while (i < length && (/[\d.]/.test(expr[i]))) {
        const cur = expr[i];
        if (cur === '.') {
          dotCount++;
          if (dotCount > 1) {
            throw new SyntaxError(`Invalid number with multiple decimal points at position ${i}`);
          }
        }
        num += cur;
        i++;
      }
      // Guard against a lone '.' (e.g., ".")
      if (num === '.' || num.endsWith('.')) {
        throw new SyntaxError(`Invalid numeric literal '${num}'`);
      }
      tokens.push(num);
      continue;
    }

    // Operators and parentheses
    if (/[+\-*/^()]/.test(ch)) {
      tokens.push(ch);
      i++;
      continue;
    }

    // Anything else is illegal
    throw new SyntaxError(`Invalid character '${ch}' at position ${i}`);
  }

  return tokens;
}

// Export for debugging / external use
window.tokenize = tokenize;

/* -------------------------------------------------------------------------- */
/*  Step 2: Infix‑to‑Postfix (Shunting‑Yard)                                 */
/* -------------------------------------------------------------------------- */
/**
 * Convert an array of infix tokens to postfix (RPN) using the shunting‑yard
 * algorithm.
 *
 * @param {string[]} tokens - Token array produced by {@link tokenize}.
 * @returns {string[]} Postfix token array.
 * @throws {SyntaxError} For mismatched parentheses or unknown tokens.
 */
function infixToPostfix(tokens) {
  const output = [];
  const opStack = [];

  const precedence = {
    '^': 4,
    '*': 3,
    '/': 3,
    '+': 2,
    '-': 2,
  };

  const rightAssociative = new Set(['^']);

  const isOperator = (t) => Object.prototype.hasOwnProperty.call(precedence, t);

  for (const token of tokens) {
    if (/^\d+(?:\.\d+)?$/.test(token)) {
      // Numeric literal
      output.push(token);
    } else if (isOperator(token)) {
      while (
        opStack.length &&
        isOperator(opStack[opStack.length - 1]) &&
        (
          (!rightAssociative.has(token) && precedence[token] <= precedence[opStack[opStack.length - 1]]) ||
          (rightAssociative.has(token) && precedence[token] < precedence[opStack[opStack.length - 1]])
        )
      ) {
        output.push(opStack.pop());
      }
      opStack.push(token);
    } else if (token === '(') {
      opStack.push(token);
    } else if (token === ')') {
      // Pop until matching '(' or error
      let foundLeft = false;
      while (opStack.length) {
        const top = opStack.pop();
        if (top === '(') {
          foundLeft = true;
          break;
        }
        output.push(top);
      }
      if (!foundLeft) {
        throw new SyntaxError('Mismatched parentheses: no matching "("');
      }
    } else {
      throw new SyntaxError(`Unknown token '${token}'`);
    }
  }

  // Drain remaining operators
  while (opStack.length) {
    const top = opStack.pop();
    if (top === '(' || top === ')') {
      throw new SyntaxError('Mismatched parentheses');
    }
    output.push(top);
  }

  return output;
}

window.infixToPostfix = infixToPostfix;

/* -------------------------------------------------------------------------- */
/*  Step 3: Postfix Evaluator                                                */
/* -------------------------------------------------------------------------- */
/**
 * Evaluate a postfix (RPN) token list and return the numeric result.
 *
 * @param {string[]} postfixTokens - Tokens in postfix order.
 * @returns {number} Computed result.
 * @throws {Error} For division by zero or malformed expressions.
 */
function evaluatePostfix(postfixTokens) {
  const stack = [];

  for (const token of postfixTokens) {
    if (/^\d+(?:\.\d+)?$/.test(token)) {
      stack.push(Number(token));
    } else {
      // Operator – need two operands
      if (stack.length < 2) {
        throw new Error('Malformed expression: insufficient values for operation');
      }
      const b = stack.pop();
      const a = stack.pop();
      let result;
      switch (token) {
        case '+':
          result = a + b;
          break;
        case '-':
          result = a - b;
          break;
        case '*':
          result = a * b;
          break;
        case '/':
          if (b === 0) {
            throw new Error('Division by zero');
          }
          result = a / b;
          break;
        case '^':
          result = Math.pow(a, b);
          break;
        default:
          throw new Error(`Unsupported operator '${token}'`);
      }
      stack.push(result);
    }
  }

  if (stack.length !== 1) {
    throw new Error('Malformed expression: leftover values after evaluation');
  }

  return stack[0];
}

window.evaluatePostfix = evaluatePostfix;

/* -------------------------------------------------------------------------- */
/*  Step 4: Expression Evaluator                                             */
/* -------------------------------------------------------------------------- */
/**
 * High‑level helper that takes a raw expression string and returns the
 * calculated result. Errors from any stage are wrapped in a generic `Error`
 * with a clear message for UI consumption.
 *
 * @param {string} expr - The arithmetic expression to evaluate.
 * @returns {number} Result of the evaluation.
 * @throws {Error} Unified error containing the original cause.
 */
function evaluateExpression(expr) {
  try {
    const tokens = tokenize(expr);
    const postfix = infixToPostfix(tokens);
    return evaluatePostfix(postfix);
  } catch (e) {
    // Preserve original error type/message but present a consistent API.
    throw new Error(`Error evaluating expression: ${e.message}`);
  }
}

window.evaluateExpression = evaluateExpression;

/* -------------------------------------------------------------------------- */
/*  Step 5: UI Interaction Layer                                            */
/* -------------------------------------------------------------------------- */
/**
 * Initialise UI event listeners once the DOM is ready.
 */
function initialiseCalculatorUI() {
  const inputEl = document.getElementById('expression');
  const resultEl = document.getElementById('result');
  const buttons = document.querySelectorAll('.button-grid button');
  const clearBtn = document.getElementById('clear');
  const equalsBtn = document.getElementById('equals');

  // Helper to reset error styling
  const clearResult = () => {
    resultEl.textContent = '';
    resultEl.classList.remove('error');
  };

  // Generic button click – append data-value (ignore clear/equal which have dedicated handlers)
  buttons.forEach((btn) => {
    // Skip if this button is the clear or equals button (they have IDs).
    if (btn.id === 'clear' || btn.id === 'equals') return;
    btn.addEventListener('click', () => {
      const val = btn.getAttribute('data-value');
      inputEl.value += val;
    });
  });

  // Clear button
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      inputEl.value = '';
      clearResult();
    });
  }

  // Equals button – perform evaluation
  const evaluateAndDisplay = () => {
    const expr = inputEl.value.trim();
    if (!expr) {
      clearResult();
      return;
    }
    try {
      const result = evaluateExpression(expr);
      resultEl.textContent = result;
      resultEl.classList.remove('error');
    } catch (err) {
      resultEl.textContent = err.message;
      resultEl.classList.add('error');
    }
  };

  if (equalsBtn) {
    equalsBtn.addEventListener('click', evaluateAndDisplay);
  }

  // Allow Enter key to trigger evaluation when focus is on the input field.
  if (inputEl) {
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        evaluateAndDisplay();
      }
    });
  }
}

// Register after DOM is fully parsed.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialiseCalculatorUI);
} else {
  // Document already ready (unlikely in typical defer script usage).
  initialiseCalculatorUI();
}

/* End of script.js */