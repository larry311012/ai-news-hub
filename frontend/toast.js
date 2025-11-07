/**
 * Toast Notification System
 * Provides accessible, stackable toast notifications
 */

class ToastManager {
    constructor() {
        this.toasts = [];
        this.container = null;
        this.maxToasts = 5;
        this.init();
    }

    init() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
            this.container.setAttribute('aria-live', 'polite');
            this.container.setAttribute('aria-atomic', 'true');
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }

        // Add styles
        this.addStyles();
    }

    addStyles() {
        if (document.getElementById('toast-styles')) return;

        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            @keyframes toastSlideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            @keyframes toastSlideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }

            .toast-enter {
                animation: toastSlideIn 0.3s ease-out forwards;
            }

            .toast-exit {
                animation: toastSlideOut 0.3s ease-in forwards;
            }

            .toast-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background-color: rgba(255, 255, 255, 0.3);
                animation: toastProgress linear forwards;
            }

            @keyframes toastProgress {
                from { width: 100%; }
                to { width: 0%; }
            }
        `;
        document.head.appendChild(style);
    }

    show(message, type = 'success', duration = 3000, options = {}) {
        // Remove oldest toast if max limit reached
        if (this.toasts.length >= this.maxToasts) {
            this.dismiss(this.toasts[0].id);
        }

        const toast = this.createToast(message, type, duration, options);
        this.toasts.push(toast);
        this.container.appendChild(toast.element);

        // Auto dismiss after duration
        if (duration > 0) {
            toast.timeoutId = setTimeout(() => {
                this.dismiss(toast.id);
            }, duration);
        }

        return toast.id;
    }

    createToast(message, type, duration, options) {
        const id = `toast-${Date.now()}-${Math.random()}`;
        const toast = document.createElement('div');

        toast.id = id;
        toast.className = `toast-enter max-w-sm w-full px-6 py-4 rounded-lg shadow-lg relative cursor-pointer transition-transform hover:scale-105`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');

        const colors = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            warning: 'bg-yellow-500 text-white',
            info: 'bg-blue-500 text-white'
        };

        const icons = {
            success: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>`,
            error: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>`,
            warning: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>`,
            info: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>`
        };

        toast.className += ` ${colors[type] || colors.info}`;

        const hasAction = options.action && options.actionText;

        toast.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    ${icons[type] || icons.info}
                </div>
                <div class="flex-1 min-w-0">
                    ${options.title ? `<p class="text-sm font-bold mb-1">${options.title}</p>` : ''}
                    <p class="text-sm">${message}</p>
                    ${hasAction ? `
                        <button class="mt-2 text-xs font-semibold underline hover:no-underline focus:outline-none"
                                onclick="window.toastManager.handleAction('${id}')">
                            ${options.actionText}
                        </button>
                    ` : ''}
                </div>
                <button class="flex-shrink-0 ml-3 focus:outline-none focus:ring-2 focus:ring-white rounded"
                        onclick="window.toastManager.dismiss('${id}')"
                        aria-label="Close">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
            ${duration > 0 ? `<div class="toast-progress" style="animation-duration: ${duration}ms;"></div>` : ''}
        `;

        // Click to dismiss
        toast.addEventListener('click', (e) => {
            if (!e.target.closest('button')) {
                this.dismiss(id);
            }
        });

        return {
            id,
            element: toast,
            timeoutId: null,
            action: options.action
        };
    }

    handleAction(toastId) {
        const toast = this.toasts.find(t => t.id === toastId);
        if (toast && toast.action) {
            toast.action();
            this.dismiss(toastId);
        }
    }

    dismiss(toastId) {
        const toastIndex = this.toasts.findIndex(t => t.id === toastId);
        if (toastIndex === -1) return;

        const toast = this.toasts[toastIndex];

        // Clear timeout if exists
        if (toast.timeoutId) {
            clearTimeout(toast.timeoutId);
        }

        // Add exit animation
        toast.element.classList.remove('toast-enter');
        toast.element.classList.add('toast-exit');

        // Remove from DOM after animation
        setTimeout(() => {
            if (toast.element.parentNode) {
                toast.element.parentNode.removeChild(toast.element);
            }
            this.toasts.splice(toastIndex, 1);
        }, 300);
    }

    dismissAll() {
        const toastIds = this.toasts.map(t => t.id);
        toastIds.forEach(id => this.dismiss(id));
    }

    success(message, duration = 3000, options = {}) {
        return this.show(message, 'success', duration, options);
    }

    error(message, duration = 5000, options = {}) {
        return this.show(message, 'error', duration, options);
    }

    warning(message, duration = 4000, options = {}) {
        return this.show(message, 'warning', duration, options);
    }

    info(message, duration = 3000, options = {}) {
        return this.show(message, 'info', duration, options);
    }
}

// Create global instance
window.toastManager = new ToastManager();

// Convenience methods
window.showToast = (message, type, duration, options) => {
    return window.toastManager.show(message, type, duration, options);
};

window.toast = {
    success: (message, duration, options) => window.toastManager.success(message, duration, options),
    error: (message, duration, options) => window.toastManager.error(message, duration, options),
    warning: (message, duration, options) => window.toastManager.warning(message, duration, options),
    info: (message, duration, options) => window.toastManager.info(message, duration, options),
    dismiss: (id) => window.toastManager.dismiss(id),
    dismissAll: () => window.toastManager.dismissAll()
};
