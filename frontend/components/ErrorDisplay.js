/**
 * Error Display Component
 * User-friendly error display for API and AI generation errors
 *
 * Features:
 * - Parse structured error responses from backend
 * - Display actionable error messages with next steps
 * - Handle different error types (quota, rate limit, auth, etc.)
 * - Provide relevant links and actions
 * - Expandable error details for debugging
 */

export const ErrorDisplay = {
    name: 'ErrorDisplay',
    props: {
        error: {
            type: [String, Object],
            required: true
        },
        dismissible: {
            type: Boolean,
            default: true
        },
        showRetry: {
            type: Boolean,
            default: true
        },
        retryLabel: {
            type: String,
            default: 'Try Again'
        }
    },
    emits: ['retry', 'dismiss', 'action'],
    data() {
        return {
            showDetails: false
        };
    },
    computed: {
        parsedError() {
            // If error is already an object with structure, use it
            if (typeof this.error === 'object' && this.error.type) {
                return this.error;
            }

            // If error is a string, try to parse it
            if (typeof this.error === 'string') {
                return this.parseErrorString(this.error);
            }

            // Default error
            return {
                type: 'unknown',
                title: 'Something went wrong',
                message: String(this.error),
                provider: null,
                actions: []
            };
        },

        errorIcon() {
            const icons = {
                quota_exceeded: this.quotaIcon,
                invalid_key: this.keyIcon,
                rate_limit: this.clockIcon,
                timeout: this.timeoutIcon,
                service_unavailable: this.cloudIcon,
                network_error: this.wifiIcon,
                auth_error: this.lockIcon,
                unknown: this.alertIcon
            };
            return icons[this.parsedError.type] || this.alertIcon;
        },

        errorClass() {
            const classes = {
                quota_exceeded: 'border-red-600 bg-red-900/20',
                invalid_key: 'border-red-600 bg-red-900/20',
                rate_limit: 'border-yellow-600 bg-yellow-900/20',
                timeout: 'border-yellow-600 bg-yellow-900/20',
                service_unavailable: 'border-orange-600 bg-orange-900/20',
                network_error: 'border-orange-600 bg-orange-900/20',
                auth_error: 'border-red-600 bg-red-900/20',
                unknown: 'border-red-600 bg-red-900/20'
            };
            return classes[this.parsedError.type] || classes.unknown;
        },

        iconColorClass() {
            const classes = {
                quota_exceeded: 'text-red-400',
                invalid_key: 'text-red-400',
                rate_limit: 'text-yellow-400',
                timeout: 'text-yellow-400',
                service_unavailable: 'text-orange-400',
                network_error: 'text-orange-400',
                auth_error: 'text-red-400',
                unknown: 'text-red-400'
            };
            return classes[this.parsedError.type] || classes.unknown;
        },

        quotaIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
        },

        keyIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>';
        },

        clockIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
        },

        timeoutIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
        },

        cloudIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/></svg>';
        },

        wifiIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"/></svg>';
        },

        lockIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>';
        },

        alertIcon() {
            return '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>';
        }
    },
    methods: {
        parseErrorString(errorStr) {
            // Check for quota exceeded errors
            if (errorStr.toLowerCase().includes('quota') || errorStr.toLowerCase().includes('billing')) {
                return {
                    type: 'quota_exceeded',
                    title: 'API Quota Exceeded',
                    message: 'You have exceeded your current API usage quota.',
                    provider: this.detectProvider(errorStr),
                    actions: this.getQuotaActions(this.detectProvider(errorStr))
                };
            }

            // Check for invalid API key errors
            if (errorStr.toLowerCase().includes('api key') ||
                errorStr.toLowerCase().includes('invalid key') ||
                errorStr.toLowerCase().includes('authentication')) {
                return {
                    type: 'invalid_key',
                    title: 'Invalid API Key',
                    message: 'Your API key is invalid or has been revoked.',
                    provider: this.detectProvider(errorStr),
                    actions: this.getInvalidKeyActions()
                };
            }

            // Check for rate limit errors
            if (errorStr.toLowerCase().includes('rate limit') || errorStr.toLowerCase().includes('too many requests')) {
                return {
                    type: 'rate_limit',
                    title: 'Rate Limit Exceeded',
                    message: 'You have made too many requests. Please wait before trying again.',
                    provider: this.detectProvider(errorStr),
                    actions: this.getRateLimitActions()
                };
            }

            // Check for timeout errors
            if (errorStr.toLowerCase().includes('timeout') || errorStr.toLowerCase().includes('timed out')) {
                return {
                    type: 'timeout',
                    title: 'Request Timed Out',
                    message: 'The request took too long to complete.',
                    actions: this.getTimeoutActions()
                };
            }

            // Check for service unavailable errors
            if (errorStr.toLowerCase().includes('unavailable') ||
                errorStr.toLowerCase().includes('503') ||
                errorStr.toLowerCase().includes('service error')) {
                return {
                    type: 'service_unavailable',
                    title: 'Service Temporarily Unavailable',
                    message: 'The AI service is currently experiencing issues.',
                    provider: this.detectProvider(errorStr),
                    actions: this.getServiceUnavailableActions()
                };
            }

            // Check for network errors
            if (errorStr.toLowerCase().includes('network') ||
                errorStr.toLowerCase().includes('connection') ||
                errorStr.toLowerCase().includes('fetch')) {
                return {
                    type: 'network_error',
                    title: 'Network Error',
                    message: 'Unable to connect to the server. Please check your internet connection.',
                    actions: this.getNetworkErrorActions()
                };
            }

            // Default unknown error
            return {
                type: 'unknown',
                title: 'Generation Failed',
                message: errorStr,
                actions: this.getDefaultActions()
            };
        },

        detectProvider(errorStr) {
            if (errorStr.toLowerCase().includes('openai')) return 'openai';
            if (errorStr.toLowerCase().includes('anthropic') || errorStr.toLowerCase().includes('claude')) return 'anthropic';
            return null;
        },

        getQuotaActions(provider) {
            const actions = [];

            if (provider === 'openai') {
                actions.push({
                    label: 'Add OpenAI Billing',
                    url: 'https://platform.openai.com/account/billing',
                    type: 'primary',
                    icon: 'external'
                });
            } else if (provider === 'anthropic') {
                actions.push({
                    label: 'Add Anthropic Billing',
                    url: 'https://console.anthropic.com/settings/billing',
                    type: 'primary',
                    icon: 'external'
                });
            }

            actions.push({
                label: 'Update API Key',
                url: 'profile.html#api-keys',
                type: 'secondary',
                icon: 'key'
            });

            actions.push({
                label: 'Try Different Provider',
                url: 'profile.html#api-keys',
                type: 'secondary',
                icon: 'switch'
            });

            return actions;
        },

        getInvalidKeyActions() {
            return [
                {
                    label: 'Update API Key in Profile',
                    url: 'profile.html#api-keys',
                    type: 'primary',
                    icon: 'key'
                },
                {
                    label: 'Get New OpenAI Key',
                    url: 'https://platform.openai.com/api-keys',
                    type: 'secondary',
                    icon: 'external'
                },
                {
                    label: 'Get New Anthropic Key',
                    url: 'https://console.anthropic.com/settings/keys',
                    type: 'secondary',
                    icon: 'external'
                }
            ];
        },

        getRateLimitActions() {
            return [
                {
                    label: 'Wait and Retry',
                    action: 'retry_delayed',
                    type: 'primary',
                    icon: 'clock',
                    delay: 60 // seconds
                },
                {
                    label: 'Check API Usage',
                    url: 'profile.html#api-keys',
                    type: 'secondary',
                    icon: 'chart'
                }
            ];
        },

        getTimeoutActions() {
            return [
                {
                    label: 'Retry Now',
                    action: 'retry',
                    type: 'primary',
                    icon: 'refresh'
                },
                {
                    label: 'Check Connection',
                    type: 'secondary',
                    icon: 'wifi'
                }
            ];
        },

        getServiceUnavailableActions() {
            return [
                {
                    label: 'Try Again in a Moment',
                    action: 'retry_delayed',
                    type: 'primary',
                    icon: 'clock',
                    delay: 30
                },
                {
                    label: 'Check Service Status',
                    url: 'https://status.openai.com',
                    type: 'secondary',
                    icon: 'external'
                }
            ];
        },

        getNetworkErrorActions() {
            return [
                {
                    label: 'Retry Connection',
                    action: 'retry',
                    type: 'primary',
                    icon: 'refresh'
                },
                {
                    label: 'Check Internet Connection',
                    type: 'secondary',
                    icon: 'wifi'
                }
            ];
        },

        getDefaultActions() {
            return [
                {
                    label: 'Try Again',
                    action: 'retry',
                    type: 'primary',
                    icon: 'refresh'
                },
                {
                    label: 'Back to Articles',
                    url: 'index.html',
                    type: 'secondary',
                    icon: 'arrow-left'
                }
            ];
        },

        handleAction(action) {
            if (action.action === 'retry') {
                this.$emit('retry');
            } else if (action.action === 'retry_delayed') {
                this.$emit('retry', action.delay || 30);
            } else if (action.url) {
                window.open(action.url, action.url.startsWith('http') ? '_blank' : '_self');
            } else {
                this.$emit('action', action);
            }
        },

        handleRetry() {
            this.$emit('retry');
        },

        handleDismiss() {
            this.$emit('dismiss');
        },

        toggleDetails() {
            this.showDetails = !this.showDetails;
        }
    },
    template: `
        <div class="bg-gray-800 rounded-lg border-2 shadow-xl p-6 animate-slide-in" :class="errorClass">
            <!-- Header -->
            <div class="flex items-start mb-4">
                <div class="flex-shrink-0" :class="iconColorClass" v-html="errorIcon"></div>
                <div class="ml-4 flex-1">
                    <h3 class="text-xl font-semibold text-white mb-2">{{ parsedError.title }}</h3>
                    <p class="text-gray-300 leading-relaxed">{{ parsedError.message }}</p>

                    <!-- Provider Badge -->
                    <div v-if="parsedError.provider" class="mt-3 inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-700 text-gray-300">
                        <svg class="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"/>
                        </svg>
                        {{ parsedError.provider === 'openai' ? 'OpenAI' : parsedError.provider === 'anthropic' ? 'Anthropic (Claude)' : 'AI Provider' }}
                    </div>
                </div>

                <!-- Dismiss Button -->
                <button v-if="dismissible"
                        @click="handleDismiss"
                        class="ml-4 text-gray-400 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 rounded-lg p-1"
                        aria-label="Dismiss error">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                </button>
            </div>

            <!-- What to do section -->
            <div v-if="parsedError.actions && parsedError.actions.length > 0" class="mt-6 p-4 bg-gray-900/50 rounded-lg border border-gray-700">
                <h4 class="text-sm font-semibold text-gray-300 mb-3 flex items-center">
                    <svg class="w-4 h-4 mr-2 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    What to do next:
                </h4>

                <div class="space-y-2">
                    <button v-for="(action, index) in parsedError.actions"
                            :key="index"
                            @click="handleAction(action)"
                            class="w-full flex items-center justify-between px-4 py-3 rounded-lg transition-all text-left group"
                            :class="action.type === 'primary'
                                ? 'bg-indigo-600 hover:bg-indigo-700 text-white font-medium'
                                : 'bg-gray-700 hover:bg-gray-600 text-gray-200'">
                        <span class="flex items-center">
                            <svg class="w-5 h-5 mr-2 opacity-75 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                            </svg>
                            {{ action.label }}
                        </span>

                        <svg v-if="action.url && action.url.startsWith('http')"
                             class="w-4 h-4 opacity-60 group-hover:opacity-100"
                             fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- Additional Actions -->
            <div class="mt-6 flex flex-wrap gap-3">
                <button v-if="showRetry"
                        @click="handleRetry"
                        class="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-800">
                    <svg class="w-4 h-4 inline-block mr-2 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    {{ retryLabel }}
                </button>

                <button @click="() => window.location.href = 'index.html'"
                        class="px-5 py-2.5 bg-gray-700 text-white text-sm font-medium rounded-lg hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-800">
                    Back to Articles
                </button>

                <button @click="toggleDetails"
                        class="px-5 py-2.5 bg-gray-700 text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-800">
                    {{ showDetails ? 'Hide' : 'Show' }} Details
                </button>
            </div>

            <!-- Error Details (Expandable) -->
            <div v-if="showDetails" class="mt-4 p-4 bg-gray-900 rounded-lg border border-gray-700">
                <h5 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Technical Details</h5>
                <pre class="text-xs text-gray-400 font-mono overflow-x-auto whitespace-pre-wrap break-words">{{ typeof error === 'object' ? JSON.stringify(error, null, 2) : error }}</pre>
            </div>
        </div>
    `
};

// Export as default and named export
export default ErrorDisplay;

// Make available globally for non-module scripts
if (typeof window !== 'undefined') {
    window.ErrorDisplay = ErrorDisplay;
}
