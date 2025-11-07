/**
 * Accessibility Helper Utilities
 * WCAG 2.1 AA Compliant
 *
 * Provides reusable functions for:
 * - Focus management
 * - Modal focus trapping
 * - Screen reader announcements
 * - Keyboard navigation
 */

/**
 * Focus Trap Manager
 * Traps focus within a modal or dialog
 */
export class FocusTrap {
    constructor(element) {
        this.element = element;
        this.previousFocus = null;
        this.firstFocusableElement = null;
        this.lastFocusableElement = null;
        this.handleKeyDown = this.handleKeyDown.bind(this);
    }

    /**
     * Get all focusable elements within the container
     */
    getFocusableElements() {
        const focusableSelectors = [
            'a[href]',
            'area[href]',
            'input:not([disabled]):not([type="hidden"])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            'button:not([disabled])',
            'iframe',
            'object',
            'embed',
            '[contenteditable]',
            '[tabindex]:not([tabindex^="-"])'
        ].join(', ');

        return Array.from(this.element.querySelectorAll(focusableSelectors))
            .filter(el => {
                // Filter out elements that are not visible
                return el.offsetParent !== null &&
                       getComputedStyle(el).visibility !== 'hidden' &&
                       getComputedStyle(el).display !== 'none';
            });
    }

    /**
     * Activate the focus trap
     */
    activate() {
        // Store the currently focused element to return to later
        this.previousFocus = document.activeElement;

        const focusableElements = this.getFocusableElements();

        if (focusableElements.length === 0) {
            // No focusable elements, focus the container itself
            this.element.tabIndex = -1;
            this.element.focus();
            return;
        }

        this.firstFocusableElement = focusableElements[0];
        this.lastFocusableElement = focusableElements[focusableElements.length - 1];

        // Add event listener for Tab key
        this.element.addEventListener('keydown', this.handleKeyDown);

        // Focus the first element
        this.firstFocusableElement.focus();
    }

    /**
     * Handle Tab and Shift+Tab to trap focus
     */
    handleKeyDown(e) {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
            // Shift + Tab: Moving backwards
            if (document.activeElement === this.firstFocusableElement) {
                e.preventDefault();
                this.lastFocusableElement.focus();
            }
        } else {
            // Tab: Moving forwards
            if (document.activeElement === this.lastFocusableElement) {
                e.preventDefault();
                this.firstFocusableElement.focus();
            }
        }
    }

    /**
     * Deactivate the focus trap and return focus
     */
    deactivate() {
        this.element.removeEventListener('keydown', this.handleKeyDown);

        // Return focus to the previously focused element
        if (this.previousFocus && this.previousFocus.focus) {
            this.previousFocus.focus();
        }
    }
}

/**
 * Screen Reader Announcer
 * Announces messages to screen readers using aria-live regions
 */
export class ScreenReaderAnnouncer {
    constructor() {
        this.politeRegion = null;
        this.assertiveRegion = null;
        this.init();
    }

    /**
     * Initialize the announcement regions
     */
    init() {
        // Create polite announcement region
        this.politeRegion = document.createElement('div');
        this.politeRegion.setAttribute('aria-live', 'polite');
        this.politeRegion.setAttribute('aria-atomic', 'true');
        this.politeRegion.className = 'sr-only';
        document.body.appendChild(this.politeRegion);

        // Create assertive announcement region
        this.assertiveRegion = document.createElement('div');
        this.assertiveRegion.setAttribute('aria-live', 'assertive');
        this.assertiveRegion.setAttribute('aria-atomic', 'true');
        this.assertiveRegion.className = 'sr-only';
        document.body.appendChild(this.assertiveRegion);
    }

    /**
     * Announce a message (polite)
     * @param {string} message - The message to announce
     */
    announce(message) {
        // Clear and set message
        this.politeRegion.textContent = '';
        setTimeout(() => {
            this.politeRegion.textContent = message;
        }, 100);
    }

    /**
     * Announce a message (assertive - interrupts)
     * @param {string} message - The message to announce
     */
    announceAssertive(message) {
        // Clear and set message
        this.assertiveRegion.textContent = '';
        setTimeout(() => {
            this.assertiveRegion.textContent = message;
        }, 100);
    }
}

/**
 * Keyboard Navigation Helper
 * Provides common keyboard event handlers
 */
export const KeyboardNav = {
    /**
     * Check if key is Enter or Space
     */
    isActivationKey(event) {
        return event.key === 'Enter' || event.key === ' ';
    },

    /**
     * Check if key is Escape
     */
    isEscapeKey(event) {
        return event.key === 'Escape' || event.key === 'Esc';
    },

    /**
     * Check if key is Arrow key
     */
    isArrowKey(event) {
        return ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key);
    },

    /**
     * Make an element keyboard accessible (Enter/Space to click)
     */
    makeClickable(element, callback) {
        element.addEventListener('keydown', (e) => {
            if (this.isActivationKey(e)) {
                e.preventDefault();
                callback(e);
            }
        });
    },

    /**
     * Handle arrow key navigation in a list
     */
    handleArrowNavigation(event, items, currentIndex) {
        let newIndex = currentIndex;

        switch (event.key) {
            case 'ArrowDown':
            case 'ArrowRight':
                event.preventDefault();
                newIndex = (currentIndex + 1) % items.length;
                break;
            case 'ArrowUp':
            case 'ArrowLeft':
                event.preventDefault();
                newIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
                break;
            case 'Home':
                event.preventDefault();
                newIndex = 0;
                break;
            case 'End':
                event.preventDefault();
                newIndex = items.length - 1;
                break;
        }

        return newIndex;
    }
};

/**
 * Modal Manager
 * Handles modal accessibility including focus trap and Escape key
 */
export class ModalManager {
    constructor(modalElement, options = {}) {
        this.modal = modalElement;
        this.options = {
            onClose: options.onClose || null,
            closeOnEscape: options.closeOnEscape !== false,
            closeOnBackdropClick: options.closeOnBackdropClick !== false,
            ...options
        };
        this.focusTrap = new FocusTrap(modalElement);
        this.handleEscape = this.handleEscape.bind(this);
        this.handleBackdropClick = this.handleBackdropClick.bind(this);
    }

    /**
     * Open the modal
     */
    open() {
        // Set aria attributes
        this.modal.setAttribute('role', 'dialog');
        this.modal.setAttribute('aria-modal', 'true');

        // Prevent body scroll
        document.body.classList.add('modal-open');

        // Activate focus trap
        this.focusTrap.activate();

        // Add event listeners
        if (this.options.closeOnEscape) {
            document.addEventListener('keydown', this.handleEscape);
        }

        if (this.options.closeOnBackdropClick) {
            this.modal.addEventListener('click', this.handleBackdropClick);
        }
    }

    /**
     * Close the modal
     */
    close() {
        // Remove aria attributes
        this.modal.removeAttribute('aria-modal');

        // Re-enable body scroll
        document.body.classList.remove('modal-open');

        // Deactivate focus trap
        this.focusTrap.deactivate();

        // Remove event listeners
        document.removeEventListener('keydown', this.handleEscape);
        this.modal.removeEventListener('click', this.handleBackdropClick);

        // Call onClose callback
        if (this.options.onClose) {
            this.options.onClose();
        }
    }

    /**
     * Handle Escape key press
     */
    handleEscape(event) {
        if (KeyboardNav.isEscapeKey(event)) {
            event.preventDefault();
            this.close();
        }
    }

    /**
     * Handle backdrop click
     */
    handleBackdropClick(event) {
        // Only close if clicking the backdrop itself, not child elements
        if (event.target === this.modal) {
            this.close();
        }
    }
}

/**
 * Form Validation Announcer
 * Announces form validation errors to screen readers
 */
export class FormValidationAnnouncer {
    constructor(formElement) {
        this.form = formElement;
        this.announcer = new ScreenReaderAnnouncer();
    }

    /**
     * Announce validation errors
     */
    announceErrors(errors) {
        const errorCount = Object.keys(errors).length;

        if (errorCount === 0) {
            this.announcer.announce('Form is valid. You can submit now.');
            return;
        }

        const errorMessage = errorCount === 1
            ? '1 error found in the form. Please correct it and try again.'
            : `${errorCount} errors found in the form. Please correct them and try again.`;

        this.announcer.announceAssertive(errorMessage);
    }

    /**
     * Announce field error
     */
    announceFieldError(fieldName, errorMessage) {
        this.announcer.announce(`${fieldName}: ${errorMessage}`);
    }

    /**
     * Announce success
     */
    announceSuccess(message = 'Form submitted successfully') {
        this.announcer.announce(message);
    }
}

/**
 * Loading State Announcer
 * Announces loading states to screen readers
 */
export class LoadingStateAnnouncer {
    constructor() {
        this.announcer = new ScreenReaderAnnouncer();
    }

    /**
     * Announce loading started
     */
    start(message = 'Loading...') {
        this.announcer.announce(message);
    }

    /**
     * Announce loading completed
     */
    complete(message = 'Loading complete') {
        this.announcer.announce(message);
    }

    /**
     * Announce error
     */
    error(message = 'An error occurred') {
        this.announcer.announceAssertive(message);
    }

    /**
     * Announce progress
     */
    progress(percentage, message = '') {
        const announcement = message
            ? `${percentage}% complete. ${message}`
            : `${percentage}% complete`;
        this.announcer.announce(announcement);
    }
}

/**
 * Skip Link Helper
 * Adds skip navigation link to page
 */
export function addSkipLink(targetId = 'main-content', linkText = 'Skip to main content') {
    // Check if skip link already exists
    if (document.querySelector('.skip-link')) {
        return;
    }

    const skipLink = document.createElement('a');
    skipLink.href = `#${targetId}`;
    skipLink.className = 'skip-link';
    skipLink.textContent = linkText;

    // Insert as first element in body
    document.body.insertBefore(skipLink, document.body.firstChild);

    // Ensure target has id and tabindex
    const target = document.getElementById(targetId);
    if (target) {
        target.setAttribute('tabindex', '-1');

        // Handle skip link click
        skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            target.focus();
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }
}

/**
 * Ensure Main Landmark
 * Ensures the main content area has proper landmark
 */
export function ensureMainLandmark(selector = 'main, [role="main"]') {
    const main = document.querySelector(selector);

    if (!main) {
        console.warn('No main landmark found. Add <main> or role="main" to your content area.');
        return null;
    }

    // Add id if not present
    if (!main.id) {
        main.id = 'main-content';
    }

    // Ensure role if not <main> element
    if (main.tagName !== 'MAIN' && !main.getAttribute('role')) {
        main.setAttribute('role', 'main');
    }

    return main;
}

/**
 * Auto-focus on page load
 * Automatically focus first heading or main content on page load
 */
export function autoFocusOnLoad() {
    // Wait for page to load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', focusMain);
    } else {
        focusMain();
    }

    function focusMain() {
        // Try to focus h1 first
        const h1 = document.querySelector('h1');
        if (h1) {
            h1.setAttribute('tabindex', '-1');
            h1.focus();
            return;
        }

        // Fallback to main content
        const main = document.querySelector('main, [role="main"]');
        if (main) {
            main.setAttribute('tabindex', '-1');
            main.focus();
        }
    }
}

/**
 * Create Global Announcer Instance
 */
export const globalAnnouncer = new ScreenReaderAnnouncer();

/**
 * Convenience function to announce messages globally
 */
export function announce(message, assertive = false) {
    if (assertive) {
        globalAnnouncer.announceAssertive(message);
    } else {
        globalAnnouncer.announce(message);
    }
}

/**
 * Initialize all accessibility features
 */
export function initAccessibility() {
    // Add skip link
    addSkipLink();

    // Ensure main landmark
    ensureMainLandmark();

    // Auto focus on load
    autoFocusOnLoad();

    console.log('✓ Accessibility features initialized');
}

// Auto-initialize if in browser environment
if (typeof window !== 'undefined') {
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAccessibility);
    } else {
        initAccessibility();
    }
}
