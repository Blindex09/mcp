/**
 * Accessible Web Component with ElementInternals (Custom Elements v1 & AOM)
 * Demonstrates:
 * 1. Form participation via static formAssociated = true.
 * 2. Shadow DOM accessibility using ElementInternals.
 * 3. Delegating ARIA states (role, aria-checked, aria-disabled) to the host element.
 * 4. Keyboard navigation (Space key toggle) and focus management.
 */

class AccessibleCustomCheckbox extends HTMLElement {
  static formAssociated = true;

  constructor() {
    super();
    this.internals_ = this.attachInternals();
    this.attachShadow({ mode: 'open' });

    // Set default ARIA role and state on the host
    this.internals_.role = 'checkbox';
    this.internals_.ariaChecked = 'false';

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          cursor: pointer;
          font-family: inherit;
        }
        :host(:focus-visible) .box {
          outline: 3px solid #005fcc;
          outline-offset: 2px;
        }
        .box {
          width: 20px;
          height: 20px;
          border: 2px solid #333;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        :host([checked]) .box::after {
          content: '✓';
          font-weight: bold;
        }
      </style>
      <div class="box"></div>
      <slot></slot>
    `;
  }

  connectedCallback() {
    if (!this.hasAttribute('tabindex')) {
      this.setAttribute('tabindex', '0');
    }

    this.addEventListener('click', this.toggle_);
    this.addEventListener('keydown', this.handleKeyDown_);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this.toggle_);
    this.removeEventListener('keydown', this.handleKeyDown_);
  }

  toggle_() {
    const isChecked = this.hasAttribute('checked');
    if (isChecked) {
      this.removeAttribute('checked');
      this.internals_.ariaChecked = 'false';
      this.internals_.setFormValue(null);
    } else {
      this.setAttribute('checked', '');
      this.internals_.ariaChecked = 'true';
      this.internals_.setFormValue('on');
    }
  }

  handleKeyDown_(e) {
    if (e.key === ' ' || e.key === 'Spacebar') {
      e.preventDefault();
      this.toggle_();
    }
  }
}

customElements.define('custom-checkbox', AccessibleCustomCheckbox);
