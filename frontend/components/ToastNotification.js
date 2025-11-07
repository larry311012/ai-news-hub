/**
 * Toast Notification Component
 * Production-ready toast notification system with queue management
 *
 * Features:
 * - Multiple toast types (success, error, warning, info)
 * - Auto-dismiss with configurable duration
 * - Manual dismiss
 * - Toast queue with max display limit
 * - Accessible (ARIA labels, keyboard navigation)
 * - Animation support
 */

const ToastNotification = {
    name: 'ToastNotification',
    template: `
        <div class="toast-container" role="region" aria-live="polite" aria-label="Notifications">
            <transition-group name="toast">
                <div
                    v-for="toast in toasts"
                    :key="toast.id"
                    :class="['toast', \`toast-\${toast.type}\`]"
                    role="alert"
                    :aria-labelledby="\`toast-title-\${toast.id}\`"
                    :aria-describedby="\`toast-message-\${toast.id}\`"
                >
                    <!-- Icon -->
                    <div class="toast-icon" aria-hidden="true">
                        <svg v-if="toast.type === 'success'" class="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                        <svg v-else-if="toast.type === 'error'" class="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                        <svg v-else-if="toast.type === 'warning'" class="w-6 h-6 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                        <svg v-else-if="toast.type === 'info'" class="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                    </div>

                    <!-- Content -->
                    <div class="toast-content">
                        <p v-if="toast.title" :id="\`toast-title-\${toast.id}\`" class="toast-title">
                            {{ toast.title }}
                        </p>
                        <p :id="\`toast-message-\${toast.id}\`" class="toast-message">
                            {{ toast.message }}
                        </p>
                        <!-- Progress bar -->
                        <div v-if="toast.showProgress && toast.duration" class="mt-2">
                            <div class="w-full bg-gray-200 rounded-full h-1">
                                <div
                                    class="h-1 rounded-full transition-all"
                                    :class="progressBarClass(toast.type)"
                                    :style="{ width: toast.progress + '%' }"
                                ></div>
                            </div>
                        </div>
                    </div>

                    <!-- Close Button -->
                    <button
                        @click="removeToast(toast.id)"
                        class="toast-close"
                        :aria-label="\`Close \${toast.title || 'notification'}\`"
                    >
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </button>
                </div>
            </transition-group>
        </div>
    `,
    data() {
        return {
            toasts: [],
            maxToasts: 3,
            nextId: 1
        };
    },
    methods: {
        /**
         * Show a toast notification
         * @param {Object} options - Toast options
         * @param {string} options.message - Toast message
         * @param {string} [options.title] - Toast title
         * @param {string} [options.type='info'] - Toast type (success, error, warning, info)
         * @param {number} [options.duration=5000] - Duration in ms (0 for persistent)
         * @param {boolean} [options.showProgress=false] - Show progress bar
         */
        show(options) {
            const toast = {
                id: this.nextId++,
                message: options.message,
                title: options.title || null,
                type: options.type || 'info',
                duration: options.duration !== undefined ? options.duration : 5000,
                showProgress: options.showProgress || false,
                progress: 100
            };

            // Remove oldest toast if we've hit the max
            if (this.toasts.length >= this.maxToasts) {
                this.removeToast(this.toasts[0].id);
            }

            this.toasts.push(toast);

            // Auto-dismiss if duration is set
            if (toast.duration > 0) {
                this.startAutoDismiss(toast);
            }

            return toast.id;
        },

        /**
         * Start auto-dismiss timer with progress bar
         */
        startAutoDismiss(toast) {
            const startTime = Date.now();
            const interval = 50; // Update every 50ms for smooth progress

            const updateProgress = () => {
                const elapsed = Date.now() - startTime;
                const remaining = Math.max(0, toast.duration - elapsed);
                toast.progress = (remaining / toast.duration) * 100;

                if (remaining <= 0) {
                    this.removeToast(toast.id);
                } else {
                    setTimeout(updateProgress, interval);
                }
            };

            if (toast.showProgress) {
                updateProgress();
            } else {
                setTimeout(() => {
                    this.removeToast(toast.id);
                }, toast.duration);
            }
        },

        /**
         * Remove a toast by ID
         */
        removeToast(id) {
            const index = this.toasts.findIndex(t => t.id === id);
            if (index > -1) {
                this.toasts.splice(index, 1);
            }
        },

        /**
         * Clear all toasts
         */
        clearAll() {
            this.toasts = [];
        },

        /**
         * Convenience methods
         */
        success(message, title = 'Success', options = {}) {
            return this.show({ message, title, type: 'success', ...options });
        },

        error(message, title = 'Error', options = {}) {
            return this.show({ message, title, type: 'error', duration: 7000, ...options });
        },

        warning(message, title = 'Warning', options = {}) {
            return this.show({ message, title, type: 'warning', ...options });
        },

        info(message, title = null, options = {}) {
            return this.show({ message, title, type: 'info', ...options });
        },

        /**
         * Get progress bar color class
         */
        progressBarClass(type) {
            const classes = {
                success: 'bg-green-600',
                error: 'bg-red-600',
                warning: 'bg-yellow-600',
                info: 'bg-blue-600'
            };
            return classes[type] || 'bg-gray-600';
        }
    }
};

// Export for use in other components
if (typeof window !== 'undefined') {
    window.ToastNotification = ToastNotification;
}
