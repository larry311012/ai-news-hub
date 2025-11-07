/**
 * OAuth Admin Configuration - Professional UI
 *
 * Clean, modern interface for managing social media OAuth credentials.
 * Features: Secure storage, real-time validation, connection testing.
 *
 * Design Principles:
 * - No debug output in production (logs gated behind localhost check)
 * - Clear visual hierarchy with loading states
 * - User-friendly error messages
 * - Platform status overview
 * - Professional aesthetic
 */

const { createApp } = Vue;

// ============================================================================
// Configuration & Utilities
// ============================================================================

const API_BASE_URL = window.location.origin.includes('localhost')
    ? 'http://localhost:8000'
    : window.location.origin;

const IS_DEV = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

function isAuthenticated() {
    return !!getAuthToken();
}

// User-friendly error message mapping
function getUserFriendlyError(error) {
    const errorMessage = error?.message || error?.toString() || 'Unknown error';

    // Network errors
    if (errorMessage.includes('Failed to fetch') || errorMessage.includes('NetworkError') || errorMessage.includes('Network request failed')) {
        return 'Cannot connect to server. Please check your internet connection.';
    }

    // Authentication errors
    if (errorMessage.includes('401') || errorMessage.includes('Unauthorized')) {
        return 'Your session expired. Please log in again.';
    }

    // Permission errors
    if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
        return 'You don\'t have permission to access this page.';
    }

    // Not found errors
    if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
        return 'The requested resource was not found.';
    }

    // Server errors
    if (errorMessage.includes('500') || errorMessage.includes('Internal Server Error') || errorMessage.includes('Server Error')) {
        return 'Server error. Please try again later.';
    }

    // Timeout errors
    if (errorMessage.includes('timeout') || errorMessage.includes('timed out')) {
        return 'Request timed out. Please try again.';
    }

    // Default fallback - return original message if it's user-friendly enough
    if (errorMessage.length < 100 && !errorMessage.includes('Error:') && !errorMessage.includes('Exception')) {
        return errorMessage;
    }

    return 'Something went wrong. Please try again or contact support.';
}

// Safe console logging (only in development)
function devLog(...args) {
    if (IS_DEV) {}
}

function devError(...args) {
    if (IS_DEV) {
        console.error(...args);
    }
}

// ============================================================================
// Platform Logo Component
// ============================================================================

const PlatformLogo = {
    name: 'PlatformLogo',
    props: {
        platform: {
            type: String,
            required: true,
            validator: (value) => ['twitter', 'linkedin', 'threads'].includes(value)
        },
        configured: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        logoConfig() {
            const configs = {
                twitter: {
                    bg: this.configured ? 'bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700' : 'bg-gray-100 dark:bg-gray-800',
                    icon: 'text-gray-900 dark:text-gray-100',
                    gradient: this.configured
                },
                linkedin: {
                    bg: this.configured ? 'bg-gradient-to-br from-blue-500 to-blue-600' : 'bg-gray-100 dark:bg-gray-800',
                    icon: this.configured ? 'text-white' : 'text-gray-600 dark:text-gray-400',
                    gradient: this.configured
                },
                threads: {
                    bg: this.configured ? 'bg-gradient-to-br from-gray-900 to-gray-800 dark:from-gray-700 dark:to-gray-600' : 'bg-gray-100 dark:bg-gray-800',
                    icon: this.configured ? 'text-white' : 'text-gray-600 dark:text-gray-400',
                    gradient: this.configured
                }
            };
            return configs[this.platform] || configs.twitter;
        }
    },
    template: `
        <div :class="['w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm', logoConfig.bg]">
            <!-- LinkedIn Icon -->
            <svg v-if="platform === 'linkedin'" viewBox="0 0 24 24" fill="currentColor" :class="['w-7 h-7', logoConfig.icon]">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
            </svg>

            <!-- Twitter/X Icon -->
            <svg v-else-if="platform === 'twitter'" viewBox="0 0 24 24" fill="currentColor" :class="['w-7 h-7', logoConfig.icon]">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>

            <!-- Threads Icon -->
            <svg v-else-if="platform === 'threads'" viewBox="0 0 24 24" fill="currentColor" :class="['w-7 h-7', logoConfig.icon]">
                <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.704-1.488 0-2.743-.546-3.625-1.577a5.688 5.688 0 0 1-1.081-2.174c-.288-.901-.438-1.886-.438-2.936 0-1.043.156-2.03.465-2.935.29-.852.703-1.613 1.226-2.26.924-1.132 2.141-1.706 3.614-1.706 1.493 0 2.718.573 3.644 1.705.488.598.853 1.326 1.086 2.167l1.01-.548c-.34-.876-.82-1.647-1.429-2.29-1.17-1.238-2.707-1.914-4.562-2.009-.025-.02-.05-.041-.075-.06l-.023-.023c-.878-.834-1.898-1.255-3.034-1.255-1.137 0-2.156.423-3.032 1.258-.866.826-1.313 1.904-1.313 3.203v.989c.032 2.015.827 3.51 2.37 4.45.916.56 1.996.844 3.208.844 1.208 0 2.283-.285 3.197-.845.492-.3.948-.69 1.358-1.163.37-.429.676-.92.91-1.465l.022.012c.01.005.018.012.028.018.464.315.84.693 1.117 1.122.397.614.617 1.34.654 2.157.023.485.012.97-.031 1.452-.095 1.032-.38 1.977-.849 2.813-.698 1.244-1.784 2.202-3.23 2.85-.967.43-2.07.65-3.275.65h-.001z"/>
            </svg>
        </div>
    `
};

// ============================================================================
// Status Badge Component
// ============================================================================

const StatusBadge = {
    name: 'StatusBadge',
    props: {
        status: {
            type: String,
            required: true,
            validator: (value) => ['not_configured', 'configured', 'testing', 'error'].includes(value)
        }
    },
    computed: {
        config() {
            const configs = {
                not_configured: {
                    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
                    border: 'border-yellow-300 dark:border-yellow-900/50',
                    text: 'text-yellow-800 dark:text-yellow-400',
                    icon: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
                    label: 'Not Configured',
                    pulse: false
                },
                configured: {
                    bg: 'bg-green-50 dark:bg-green-900/20',
                    border: 'border-green-300 dark:border-green-900/50',
                    text: 'text-green-800 dark:text-green-400',
                    icon: 'M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z',
                    label: 'Active',
                    pulse: false
                },
                testing: {
                    bg: 'bg-blue-50 dark:bg-blue-900/20',
                    border: 'border-blue-300 dark:border-blue-900/50',
                    text: 'text-blue-800 dark:text-blue-400',
                    icon: null,
                    label: 'Testing...',
                    pulse: true
                },
                error: {
                    bg: 'bg-red-50 dark:bg-red-900/20',
                    border: 'border-red-300 dark:border-red-900/50',
                    text: 'text-red-800 dark:text-red-400',
                    icon: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
                    label: 'Error',
                    pulse: false
                }
            };
            return configs[this.status] || configs.not_configured;
        }
    },
    template: `
        <span :class="[
            'inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-full border shadow-sm animate-fadeIn',
            config.bg, config.border, config.text
        ]">
            <svg v-if="config.icon" class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" :d="config.icon" clip-rule="evenodd"/>
            </svg>
            <span v-if="status === 'testing'" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
            {{ config.label }}
        </span>
    `
};

// ============================================================================
// Loading Skeleton Component
// ============================================================================

const LoadingSkeleton = {
    name: 'LoadingSkeleton',
    template: `
        <div class="space-y-4 animate-fadeIn">
            <div v-for="i in 3" :key="i" class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm">
                <div class="flex items-start gap-4">
                    <div class="w-14 h-14 bg-gray-200 dark:bg-slate-700 rounded-xl skeleton"></div>
                    <div class="flex-1 space-y-3">
                        <div class="h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/4 skeleton"></div>
                        <div class="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/2 skeleton"></div>
                    </div>
                    <div class="h-7 bg-gray-200 dark:bg-slate-700 rounded-full w-24 skeleton"></div>
                </div>
            </div>
        </div>
    `
};

// ============================================================================
// Twitter Configuration Card
// ============================================================================

const TwitterConfigCard = {
    name: 'TwitterConfigCard',
    components: { PlatformLogo, StatusBadge },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            isTesting: false,
            status: 'not_configured',
            form: {
                api_key: '',
                api_secret: '',
                callback_url: this.getCallbackUrl()
            },
            saved: {
                api_key_masked: null,
                last_updated: null,
                updated_by: null
            },
            errors: {
                api_key: null,
                api_secret: null,
                connection: null
            },
            showPassword: false
        };
    },
    computed: {
        isConfigured() {
            return this.status === 'configured';
        }
    },
    methods: {
        getCallbackUrl() {
            return `${window.location.origin}/api/social-media/twitter-oauth1/callback`;
        },

        async loadConfiguration() {
            this.isLoading = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/twitter`, {
                    withCredentials: true
                });

                if (response.ok) {
                    const data = await response.json();
                    this.saved.api_key_masked = data.masked_credentials?.api_key || null;
                    this.saved.last_updated = data.updated_at;
                    this.saved.updated_by = data.updated_by_email;
                    this.status = 'configured';
                    this.$emit('status-update', { platform: 'twitter', configured: true });
                } else if (response.status === 404) {
                    this.status = 'not_configured';
                    this.$emit('status-update', { platform: 'twitter', configured: false });
                } else if (response.status === 403) {
                    const friendlyMessage = getUserFriendlyError(new Error('403'));
                    this.$emit('toast', { type: 'error', message: friendlyMessage });
                }
            } catch (error) {
                devError('Failed to load Twitter configuration:', error);
                const friendlyMessage = getUserFriendlyError(error);
                this.$emit('toast', { type: 'error', message: 'Failed to load configuration', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },

        async saveCredentials() {
            if (!this.validateForm()) return;

            this.isLoading = true;
            this.errors.connection = null;

            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/twitter`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    credentials: 'include'
                    },
                    body: JSON.stringify({
                        oauth_version: '1.0a',
                        api_key: this.form.api_key.trim(),
                        api_secret: this.form.api_secret.trim(),
                        callback_url: this.form.callback_url
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save credentials');
                }

                await this.loadConfiguration();
                this.isExpanded = false;
                this.form.api_key = '';
                this.form.api_secret = '';
                this.showPassword = false;
                this.$emit('toast', {
                    type: 'success',
                    message: 'Twitter credentials saved successfully!',
                    description: 'Your credentials are now active and ready to use.'
                });

            } catch (error) {
                const friendlyMessage = getUserFriendlyError(error);
                this.errors.connection = friendlyMessage;
                this.$emit('toast', { type: 'error', message: 'Failed to save credentials', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },

        async testConnection() {
            if (!this.validateForm()) return;

            this.isTesting = true;
            this.status = 'testing';
            this.errors.connection = null;

            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/twitter/test`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    credentials: 'include'
                    },
                    body: JSON.stringify({
                        oauth_version: '1.0a',
                        api_key: this.form.api_key.trim(),
                        api_secret: this.form.api_secret.trim(),
                        callback_url: this.form.callback_url
                    })
                });

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(result.message || result.detail || 'Connection test failed');
                }

                this.status = this.isConfigured ? 'configured' : 'not_configured';
                this.$emit('toast', {
                    type: 'success',
                    message: 'Connection successful!',
                    description: 'Your Twitter credentials are working correctly.'
                });

            } catch (error) {
                this.status = 'error';
                const friendlyMessage = getUserFriendlyError(error);
                this.errors.connection = friendlyMessage;
                this.$emit('toast', { type: 'error', message: 'Connection test failed', description: friendlyMessage });
            } finally {
                this.isTesting = false;
                setTimeout(() => {
                    if (this.status === 'error') {
                        this.status = this.isConfigured ? 'configured' : 'not_configured';
                    }
                }, 3000);
            }
        },

        async removeCredentials() {
            if (!confirm('Remove Twitter credentials? Users will not be able to connect their Twitter accounts until you configure OAuth again.')) {
                return;
            }

            this.isLoading = true;

            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/twitter`, {
                    method: 'DELETE',
                    withCredentials: true
                });

                if (!response.ok) {
                    throw new Error('Failed to remove credentials');
                }

                this.status = 'not_configured';
                this.saved = { api_key_masked: null, last_updated: null, updated_by: null };
                this.form.api_key = '';
                this.form.api_secret = '';
                this.$emit('status-update', { platform: 'twitter', configured: false });
                this.$emit('toast', { type: 'success', message: 'Twitter credentials removed successfully' });

            } catch (error) {
                const friendlyMessage = getUserFriendlyError(error);
                this.$emit('toast', { type: 'error', message: 'Failed to remove credentials', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },

        validateForm() {
            let isValid = true;
            this.errors.api_key = null;
            this.errors.api_secret = null;

            if (!this.form.api_key.trim()) {
                this.errors.api_key = 'API Key is required';
                isValid = false;
            } else if (!/^[a-zA-Z0-9_-]+$/.test(this.form.api_key.trim())) {
                this.errors.api_key = 'API Key contains invalid characters';
                isValid = false;
            }

            if (!this.form.api_secret.trim()) {
                this.errors.api_secret = 'API Secret is required';
                isValid = false;
            }

            return isValid;
        },

        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.$emit('toast', { type: 'success', message: 'Copied to clipboard!' });
            }).catch(() => {
                this.$emit('toast', { type: 'error', message: 'Failed to copy to clipboard' });
            });
        },

        togglePasswordVisibility() {
            this.showPassword = !this.showPassword;
        },

        toggleForm() {
            this.isExpanded = !this.isExpanded;
            if (!this.isExpanded) {
                this.form.api_key = '';
                this.form.api_secret = '';
                this.errors = { api_key: null, api_secret: null, connection: null };
                this.showPassword = false;
            }
        },

        formatDate(dateString) {
            if (!dateString) return 'Never';
            const date = new Date(dateString);
            const now = new Date();
            const diffHours = Math.floor((now - date) / 3600000);

            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return `${diffHours}h ago`;

            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        }
    },
    mounted() {
        // Configure axios to send httpOnly cookies
        axios.defaults.withCredentials = true;

        this.loadConfiguration();
    },
    template: `
        <div class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm card-hover">
            <!-- Card Header -->
            <div class="flex items-start justify-between gap-4 mb-4">
                <div class="flex items-start gap-4 flex-1">
                    <platform-logo platform="twitter" :configured="isConfigured"></platform-logo>
                    <div class="flex-1 min-w-0">
                        <h3 class="text-xl font-bold text-gray-900 dark:text-gray-50 mb-1.5">
                            Twitter / X
                        </h3>
                        <p v-if="!isConfigured && !isExpanded" class="text-sm text-gray-600 dark:text-gray-400">
                            Configure your Twitter OAuth 1.0a credentials to enable posting
                        </p>
                        <div v-else-if="isConfigured && !isExpanded" class="space-y-1.5">
                            <div class="flex items-center gap-2">
                                <code class="px-2.5 py-1 bg-gray-100 dark:bg-slate-700 rounded-lg text-xs font-mono text-gray-800 dark:text-gray-200">
                                    {{ saved.api_key_masked }}
                                </code>
                                <button @click="copyToClipboard(saved.api_key_masked)"
                                        class="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                        aria-label="Copy API Key">
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                                    </svg>
                                </button>
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400">
                                Updated {{ formatDate(saved.last_updated) }}<template v-if="saved.updated_by"> by {{ saved.updated_by }}</template>
                            </p>
                        </div>
                    </div>
                </div>
                <status-badge :status="status"></status-badge>
            </div>

            <!-- Configuration Form -->
            <div v-if="isExpanded" class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700 animate-slideDown">
                <form @submit.prevent="saveCredentials" class="space-y-5">

                    <!-- API Key Field -->
                    <div>
                        <label for="twitter-api-key" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            API Key (Consumer Key) <span class="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            id="twitter-api-key"
                            v-model="form.api_key"
                            placeholder="Enter your Twitter API Key"
                            required
                            :class="[
                                'w-full px-4 py-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-900 border rounded-lg transition-all',
                                errors.api_key
                                    ? 'border-red-500 focus:ring-2 focus:ring-red-500'
                                    : 'border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
                            ]"
                        />
                        <p v-if="errors.api_key" class="text-xs text-red-600 dark:text-red-400 mt-1.5 flex items-center gap-1">
                            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"/>
                            </svg>
                            {{ errors.api_key }}
                        </p>
                        <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                            Get this from the
                            <a href="https://developer.twitter.com/en/portal/dashboard" target="_blank" rel="noopener"
                               class="text-blue-600 dark:text-blue-400 hover:underline font-medium">
                                Twitter Developer Portal
                            </a>
                        </p>
                    </div>

                    <!-- API Secret Field -->
                    <div>
                        <label for="twitter-api-secret" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            API Secret (Consumer Secret) <span class="text-red-500">*</span>
                        </label>
                        <div class="relative">
                            <input
                                :type="showPassword ? 'text' : 'password'"
                                id="twitter-api-secret"
                                v-model="form.api_secret"
                                placeholder="Enter your Twitter API Secret"
                                required
                                :class="[
                                    'w-full px-4 py-3 pr-12 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-900 border rounded-lg transition-all',
                                    errors.api_secret
                                        ? 'border-red-500 focus:ring-2 focus:ring-red-500'
                                        : 'border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
                                ]"
                            />
                            <button
                                type="button"
                                @click="togglePasswordVisibility"
                                class="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
                                :aria-label="showPassword ? 'Hide secret' : 'Show secret'"
                            >
                                <svg v-if="!showPassword" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                                </svg>
                                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                                </svg>
                            </button>
                        </div>
                        <p v-if="errors.api_secret" class="text-xs text-red-600 dark:text-red-400 mt-1.5 flex items-center gap-1">
                            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"/>
                            </svg>
                            {{ errors.api_secret }}
                        </p>
                        <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1.5 flex items-center gap-1">
                            <svg class="w-3.5 h-3.5 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                            </svg>
                            Keep this secret secure - never share publicly
                        </p>
                    </div>

                    <!-- Callback URL -->
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            Callback URL
                        </label>
                        <div class="flex gap-2">
                            <input
                                type="text"
                                :value="form.callback_url"
                                readonly
                                class="flex-1 px-4 py-3 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-600 rounded-lg cursor-default"
                            />
                            <button
                                type="button"
                                @click="copyToClipboard(form.callback_url)"
                                class="px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2"
                            >
                                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                                </svg>
                                Copy
                            </button>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                            Add this URL to your Twitter app's callback URL settings
                        </p>
                    </div>

                    <!-- Connection Error Display -->
                    <div v-if="errors.connection" class="bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-900/50 rounded-xl p-4">
                        <div class="flex items-start gap-3">
                            <div class="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center flex-shrink-0">
                                <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/>
                                </svg>
                            </div>
                            <div class="flex-1">
                                <p class="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">Connection Test Failed</p>
                                <p class="text-xs text-red-800 dark:text-red-300 mb-2">{{ errors.connection }}</p>
                                <div class="text-xs text-red-800 dark:text-red-300">
                                    <p class="font-medium mb-1">Common solutions:</p>
                                    <ul class="list-disc list-inside space-y-0.5 ml-1">
                                        <li>Verify API Key is correct (no typos or extra spaces)</li>
                                        <li>Check API Secret matches exactly</li>
                                        <li>Ensure your Twitter app has Read and Write permissions</li>
                                        <li>Confirm callback URL is added to your Twitter app settings</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Form Actions -->
                    <div class="flex flex-col-reverse sm:flex-row gap-3 pt-2">
                        <button
                            type="button"
                            @click="toggleForm"
                            class="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="button"
                            @click="testConnection"
                            :disabled="isLoading || isTesting"
                            class="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
                        >
                            <span v-if="isTesting" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                            {{ isTesting ? 'Testing...' : 'Test Connection' }}
                        </button>
                        <button
                            type="submit"
                            :disabled="isLoading || isTesting"
                            class="px-6 py-3 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
                        >
                            <span v-if="isLoading" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                            </svg>
                            {{ isLoading ? 'Saving...' : 'Save Credentials' }}
                        </button>
                    </div>
                </form>
            </div>

            <!-- Action Buttons (When Collapsed) -->
            <div v-else class="flex flex-wrap gap-3 mt-5">
                <button
                    v-if="!isConfigured"
                    @click="toggleForm"
                    class="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm"
                >
                    Configure Twitter
                </button>
                <template v-else>
                    <button
                        @click="testConnection"
                        :disabled="isTesting"
                        class="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2"
                    >
                        <span v-if="isTesting" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                        <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        {{ isTesting ? 'Testing...' : 'Test' }}
                    </button>
                    <button
                        @click="toggleForm"
                        class="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 transition-all shadow-sm"
                    >
                        Edit
                    </button>
                    <button
                        @click="removeCredentials"
                        :disabled="isLoading"
                        class="px-5 py-2.5 text-sm font-semibold text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2"
                    >
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                        Remove
                    </button>
                </template>
            </div>
        </div>
    `
};

// ============================================================================
// LinkedIn Configuration Card
// (Similar structure to Twitter)
// ============================================================================

const LinkedInConfigCard = {
    name: 'LinkedInConfigCard',
    components: { PlatformLogo, StatusBadge },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            isTesting: false,
            status: 'not_configured',
            form: {
                client_id: '',
                client_secret: '',
                redirect_uri: this.getRedirectUri(),
                scopes: ['openid', 'profile', 'email', 'w_member_social']
            },
            saved: {
                client_id_masked: null,
                last_updated: null,
                updated_by: null
            },
            errors: {
                client_id: null,
                client_secret: null,
                connection: null
            },
            showPassword: false
        };
    },
    computed: {
        isConfigured() {
            return this.status === 'configured';
        }
    },
    methods: {
        getRedirectUri() {
            return `${window.location.origin}/api/social-media/linkedin/callback`;
        },
        async loadConfiguration() {
            this.isLoading = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/linkedin`, {
                    withCredentials: true
                });
                if (response.ok) {
                    const data = await response.json();
                    this.saved.client_id_masked = data.masked_credentials?.client_id || null;
                    this.saved.last_updated = data.updated_at;
                    this.saved.updated_by = data.updated_by_email;
                    this.status = 'configured';
                    this.$emit('status-update', { platform: 'linkedin', configured: true });
                } else if (response.status === 404) {
                    this.status = 'not_configured';
                    this.$emit('status-update', { platform: 'linkedin', configured: false });
                } else if (response.status === 403) {
                    const friendlyMessage = getUserFriendlyError(new Error('403'));
                    this.$emit('toast', { type: 'error', message: friendlyMessage });
                }
            } catch (error) {
                devError('Failed to load LinkedIn configuration:', error);
                const friendlyMessage = getUserFriendlyError(error);
                this.$emit('toast', { type: 'error', message: 'Failed to load configuration', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },
        async saveCredentials() {
            if (!this.validateForm()) return;
            this.isLoading = true;
            this.errors.connection = null;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/linkedin`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    credentials: 'include'
                    },
                    body: JSON.stringify({
                        oauth_version: '2.0',
                        client_id: this.form.client_id.trim(),
                        client_secret: this.form.client_secret.trim(),
                        redirect_uri: this.form.redirect_uri,
                        scopes: this.form.scopes
                    })
                });
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save credentials');
                }
                await this.loadConfiguration();
                this.isExpanded = false;
                this.form.client_id = '';
                this.form.client_secret = '';
                this.showPassword = false;
                this.$emit('toast', {
                    type: 'success',
                    message: 'LinkedIn credentials saved successfully!',
                    description: 'Your credentials are now active and ready to use.'
                });
            } catch (error) {
                const friendlyMessage = getUserFriendlyError(error);
                this.errors.connection = friendlyMessage;
                this.$emit('toast', { type: 'error', message: 'Failed to save credentials', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },
        async testConnection() {
            if (!this.validateForm()) return;
            this.isTesting = true;
            this.status = 'testing';
            this.errors.connection = null;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/linkedin/test`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    credentials: 'include'
                    },
                    body: JSON.stringify({
                        oauth_version: '2.0',
                        client_id: this.form.client_id.trim(),
                        client_secret: this.form.client_secret.trim(),
                        redirect_uri: this.form.redirect_uri,
                        scopes: this.form.scopes
                    })
                });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    throw new Error(result.message || result.detail || 'Connection test failed');
                }
                this.status = this.isConfigured ? 'configured' : 'not_configured';
                this.$emit('toast', {
                    type: 'success',
                    message: 'Connection successful!',
                    description: 'Your LinkedIn credentials are working correctly.'
                });
            } catch (error) {
                this.status = 'error';
                const friendlyMessage = getUserFriendlyError(error);
                this.errors.connection = friendlyMessage;
                this.$emit('toast', { type: 'error', message: 'Connection test failed', description: friendlyMessage });
            } finally {
                this.isTesting = false;
                setTimeout(() => {
                    if (this.status === 'error') {
                        this.status = this.isConfigured ? 'configured' : 'not_configured';
                    }
                }, 3000);
            }
        },
        async removeCredentials() {
            if (!confirm('Remove LinkedIn credentials? Users will not be able to connect their LinkedIn accounts.')) return;
            this.isLoading = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/linkedin`, {
                    method: 'DELETE',
                    withCredentials: true
                });
                if (!response.ok) throw new Error('Failed to remove credentials');
                this.status = 'not_configured';
                this.saved = { client_id_masked: null, last_updated: null, updated_by: null };
                this.form.client_id = '';
                this.form.client_secret = '';
                this.$emit('status-update', { platform: 'linkedin', configured: false });
                this.$emit('toast', { type: 'success', message: 'LinkedIn credentials removed successfully' });
            } catch (error) {
                const friendlyMessage = getUserFriendlyError(error);
                this.$emit('toast', { type: 'error', message: 'Failed to remove credentials', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },
        validateForm() {
            let isValid = true;
            this.errors.client_id = null;
            this.errors.client_secret = null;
            if (!this.form.client_id.trim()) {
                this.errors.client_id = 'Client ID is required';
                isValid = false;
            }
            if (!this.form.client_secret.trim()) {
                this.errors.client_secret = 'Client Secret is required';
                isValid = false;
            }
            return isValid;
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.$emit('toast', { type: 'success', message: 'Copied to clipboard!' });
            }).catch(() => {
                this.$emit('toast', { type: 'error', message: 'Failed to copy to clipboard' });
            });
        },
        togglePasswordVisibility() {
            this.showPassword = !this.showPassword;
        },
        toggleForm() {
            this.isExpanded = !this.isExpanded;
            if (!this.isExpanded) {
                this.form.client_id = '';
                this.form.client_secret = '';
                this.errors = { client_id: null, client_secret: null, connection: null };
                this.showPassword = false;
            }
        },
        formatDate(dateString) {
            if (!dateString) return 'Never';
            const date = new Date(dateString);
            const now = new Date();
            const diffHours = Math.floor((now - date) / 3600000);
            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return `${diffHours}h ago`;
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        }
    },
    mounted() {
        this.loadConfiguration();
    },
    template: `
        <div class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm card-hover">
            <div class="flex items-start justify-between gap-4 mb-4">
                <div class="flex items-start gap-4 flex-1">
                    <platform-logo platform="linkedin" :configured="isConfigured"></platform-logo>
                    <div class="flex-1 min-w-0">
                        <h3 class="text-xl font-bold text-gray-900 dark:text-gray-50 mb-1.5">
                            LinkedIn
                        </h3>
                        <p v-if="!isConfigured && !isExpanded" class="text-sm text-gray-600 dark:text-gray-400">
                            Configure your LinkedIn OAuth 2.0 credentials to enable posting
                        </p>
                        <div v-else-if="isConfigured && !isExpanded" class="space-y-1.5">
                            <div class="flex items-center gap-2">
                                <code class="px-2.5 py-1 bg-gray-100 dark:bg-slate-700 rounded-lg text-xs font-mono text-gray-800 dark:text-gray-200">
                                    {{ saved.client_id_masked }}
                                </code>
                                <button @click="copyToClipboard(saved.client_id_masked)"
                                        class="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                        aria-label="Copy Client ID">
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                                    </svg>
                                </button>
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400">
                                Updated {{ formatDate(saved.last_updated) }}<template v-if="saved.updated_by"> by {{ saved.updated_by }}</template>
                            </p>
                        </div>
                    </div>
                </div>
                <status-badge :status="status"></status-badge>
            </div>

            <div v-if="isExpanded" class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700 animate-slideDown">
                <form @submit.prevent="saveCredentials" class="space-y-5">
                    <div>
                        <label for="linkedin-client-id" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            Client ID <span class="text-red-500">*</span>
                        </label>
                        <input type="text" id="linkedin-client-id" v-model="form.client_id" placeholder="Enter your LinkedIn Client ID" required
                            :class="['w-full px-4 py-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-900 border rounded-lg transition-all',
                                errors.client_id ? 'border-red-500 focus:ring-2 focus:ring-red-500' : 'border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500']"/>
                        <p v-if="errors.client_id" class="text-xs text-red-600 dark:text-red-400 mt-1.5">{{ errors.client_id }}</p>
                        <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">
                            Get this from <a href="https://developer.linkedin.com/docs/getting-started" target="_blank" rel="noopener" class="text-blue-600 dark:text-blue-400 hover:underline font-medium">LinkedIn Developer Portal</a>
                        </p>
                    </div>
                    <div>
                        <label for="linkedin-client-secret" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            Client Secret <span class="text-red-500">*</span>
                        </label>
                        <div class="relative">
                            <input :type="showPassword ? 'text' : 'password'" id="linkedin-client-secret" v-model="form.client_secret" placeholder="Enter your LinkedIn Client Secret" required
                                :class="['w-full px-4 py-3 pr-12 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-900 border rounded-lg transition-all',
                                    errors.client_secret ? 'border-red-500 focus:ring-2 focus:ring-red-500' : 'border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500']"/>
                            <button type="button" @click="togglePasswordVisibility"
                                class="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors">
                                <svg v-if="!showPassword" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                                </svg>
                                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                                </svg>
                            </button>
                        </div>
                        <p v-if="errors.client_secret" class="text-xs text-red-600 dark:text-red-400 mt-1.5">{{ errors.client_secret }}</p>
                        <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Keep this secret secure - never share publicly</p>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Redirect URI</label>
                        <div class="flex gap-2">
                            <input type="text" :value="form.redirect_uri" readonly class="flex-1 px-4 py-3 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-600 rounded-lg cursor-default"/>
                            <button type="button" @click="copyToClipboard(form.redirect_uri)" class="px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2">
                                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                                Copy
                            </button>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Add this redirect URI to your LinkedIn app settings</p>
                    </div>
                    <div v-if="errors.connection" class="bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-900/50 rounded-xl p-4">
                        <div class="flex items-start gap-3">
                            <div class="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center flex-shrink-0">
                                <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/></svg>
                            </div>
                            <div class="flex-1">
                                <p class="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">Connection Test Failed</p>
                                <p class="text-xs text-red-800 dark:text-red-300">{{ errors.connection }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="flex flex-col-reverse sm:flex-row gap-3 pt-2">
                        <button type="button" @click="toggleForm" class="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors">Cancel</button>
                        <button type="button" @click="testConnection" :disabled="isLoading || isTesting" class="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2">
                            <span v-if="isTesting" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            {{ isTesting ? 'Testing...' : 'Test Connection' }}
                        </button>
                        <button type="submit" :disabled="isLoading || isTesting" class="px-6 py-3 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2">
                            <span v-if="isLoading" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                            {{ isLoading ? 'Saving...' : 'Save Credentials' }}
                        </button>
                    </div>
                </form>
            </div>

            <div v-else class="flex flex-wrap gap-3 mt-5">
                <button v-if="!isConfigured" @click="toggleForm" class="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm">Configure LinkedIn</button>
                <template v-else>
                    <button @click="testConnection" :disabled="isTesting" class="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2">
                        <span v-if="isTesting" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                        <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        {{ isTesting ? 'Testing...' : 'Test' }}
                    </button>
                    <button @click="toggleForm" class="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 transition-all shadow-sm">Edit</button>
                    <button @click="removeCredentials" :disabled="isLoading" class="px-5 py-2.5 text-sm font-semibold text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        Remove
                    </button>
                </template>
            </div>
        </div>
    `
};

// ============================================================================
// Threads Configuration Card
// (Similar structure - abbreviated for brevity, follows same pattern)
// ============================================================================

const ThreadsConfigCard = {
    name: 'ThreadsConfigCard',
    components: { PlatformLogo, StatusBadge },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            isTesting: false,
            status: 'not_configured',
            form: {
                client_id: '',
                client_secret: '',
                redirect_uri: this.getRedirectUri()
            },
            saved: {
                client_id_masked: null,
                last_updated: null,
                updated_by: null
            },
            errors: {
                client_id: null,
                client_secret: null,
                connection: null
            },
            showPassword: false
        };
    },
    computed: {
        isConfigured() {
            return this.status === 'configured';
        }
    },
    methods: {
        getRedirectUri() {
            return `${window.location.origin}/api/social-media/threads/callback`;
        },
        async loadConfiguration() {
            this.isLoading = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/threads`, {
                    withCredentials: true
                });
                if (response.ok) {
                    const data = await response.json();
                    this.saved.client_id_masked = data.masked_credentials?.client_id || null;
                    this.saved.last_updated = data.updated_at;
                    this.saved.updated_by = data.updated_by_email;
                    this.status = 'configured';
                    this.$emit('status-update', { platform: 'threads', configured: true });
                } else if (response.status === 404) {
                    this.status = 'not_configured';
                    this.$emit('status-update', { platform: 'threads', configured: false });
                } else if (response.status === 403) {
                    const friendlyMessage = getUserFriendlyError(new Error('403'));
                    this.$emit('toast', { type: 'error', message: friendlyMessage });
                }
            } catch (error) {
                devError('Failed to load Threads configuration:', error);
                const friendlyMessage = getUserFriendlyError(error);
                this.$emit('toast', { type: 'error', message: 'Failed to load configuration', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },
        async saveCredentials() {
            if (!this.validateForm()) return;
            this.isLoading = true;
            this.errors.connection = null;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/threads`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    credentials: 'include'
                    },
                    body: JSON.stringify({
                        oauth_version: '2.0',
                        client_id: this.form.client_id.trim(),
                        client_secret: this.form.client_secret.trim(),
                        redirect_uri: this.form.redirect_uri
                    })
                });
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to save credentials');
                }
                await this.loadConfiguration();
                this.isExpanded = false;
                this.form.client_id = '';
                this.form.client_secret = '';
                this.showPassword = false;
                this.$emit('toast', {
                    type: 'success',
                    message: 'Threads credentials saved successfully!',
                    description: 'Your credentials are now active and ready to use.'
                });
            } catch (error) {
                const friendlyMessage = getUserFriendlyError(error);
                this.errors.connection = friendlyMessage;
                this.$emit('toast', { type: 'error', message: 'Failed to save credentials', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },
        async testConnection() {
            if (!this.validateForm()) return;
            this.isTesting = true;
            this.status = 'testing';
            this.errors.connection = null;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/threads/test`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    credentials: 'include'
                    },
                    body: JSON.stringify({
                        oauth_version: '2.0',
                        client_id: this.form.client_id.trim(),
                        client_secret: this.form.client_secret.trim(),
                        redirect_uri: this.form.redirect_uri
                    })
                });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    throw new Error(result.message || result.detail || 'Connection test failed');
                }
                this.status = this.isConfigured ? 'configured' : 'not_configured';
                this.$emit('toast', {
                    type: 'success',
                    message: 'Connection successful!',
                    description: 'Your Threads credentials are working correctly.'
                });
            } catch (error) {
                this.status = 'error';
                const friendlyMessage = getUserFriendlyError(error);
                this.errors.connection = friendlyMessage;
                this.$emit('toast', { type: 'error', message: 'Connection test failed', description: friendlyMessage });
            } finally {
                this.isTesting = false;
                setTimeout(() => {
                    if (this.status === 'error') {
                        this.status = this.isConfigured ? 'configured' : 'not_configured';
                    }
                }, 3000);
            }
        },
        async removeCredentials() {
            if (!confirm('Remove Threads credentials? Users will not be able to connect their Threads accounts.')) return;
            this.isLoading = true;
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials/threads`, {
                    method: 'DELETE',
                    withCredentials: true
                });
                if (!response.ok) throw new Error('Failed to remove credentials');
                this.status = 'not_configured';
                this.saved = { client_id_masked: null, last_updated: null, updated_by: null };
                this.form.client_id = '';
                this.form.client_secret = '';
                this.$emit('status-update', { platform: 'threads', configured: false });
                this.$emit('toast', { type: 'success', message: 'Threads credentials removed successfully' });
            } catch (error) {
                const friendlyMessage = getUserFriendlyError(error);
                this.$emit('toast', { type: 'error', message: 'Failed to remove credentials', description: friendlyMessage });
            } finally {
                this.isLoading = false;
            }
        },
        validateForm() {
            let isValid = true;
            this.errors.client_id = null;
            this.errors.client_secret = null;
            if (!this.form.client_id.trim()) {
                this.errors.client_id = 'App ID is required';
                isValid = false;
            }
            if (!this.form.client_secret.trim()) {
                this.errors.client_secret = 'App Secret is required';
                isValid = false;
            }
            return isValid;
        },
        copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                this.$emit('toast', { type: 'success', message: 'Copied to clipboard!' });
            }).catch(() => {
                this.$emit('toast', { type: 'error', message: 'Failed to copy to clipboard' });
            });
        },
        togglePasswordVisibility() {
            this.showPassword = !this.showPassword;
        },
        toggleForm() {
            this.isExpanded = !this.isExpanded;
            if (!this.isExpanded) {
                this.form.client_id = '';
                this.form.client_secret = '';
                this.errors = { client_id: null, client_secret: null, connection: null };
                this.showPassword = false;
            }
        },
        formatDate(dateString) {
            if (!dateString) return 'Never';
            const date = new Date(dateString);
            const now = new Date();
            const diffHours = Math.floor((now - date) / 3600000);
            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return `${diffHours}h ago`;
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        }
    },
    mounted() {
        this.loadConfiguration();
    },
    template: `
        <div class="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-2xl p-6 shadow-sm card-hover">
            <div class="flex items-start justify-between gap-4 mb-4">
                <div class="flex items-start gap-4 flex-1">
                    <platform-logo platform="threads" :configured="isConfigured"></platform-logo>
                    <div class="flex-1 min-w-0">
                        <h3 class="text-xl font-bold text-gray-900 dark:text-gray-50 mb-1.5">Threads</h3>
                        <p v-if="!isConfigured && !isExpanded" class="text-sm text-gray-600 dark:text-gray-400">Configure your Threads OAuth 2.0 credentials to enable posting</p>
                        <div v-else-if="isConfigured && !isExpanded" class="space-y-1.5">
                            <div class="flex items-center gap-2">
                                <code class="px-2.5 py-1 bg-gray-100 dark:bg-slate-700 rounded-lg text-xs font-mono text-gray-800 dark:text-gray-200">{{ saved.client_id_masked }}</code>
                                <button @click="copyToClipboard(saved.client_id_masked)" class="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" aria-label="Copy App ID">
                                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                                </button>
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400">Updated {{ formatDate(saved.last_updated) }}<template v-if="saved.updated_by"> by {{ saved.updated_by }}</template></p>
                        </div>
                    </div>
                </div>
                <status-badge :status="status"></status-badge>
            </div>

            <div v-if="isExpanded" class="mt-6 pt-6 border-t border-gray-200 dark:border-slate-700 animate-slideDown">
                <form @submit.prevent="saveCredentials" class="space-y-5">
                    <div>
                        <label for="threads-client-id" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">App ID <span class="text-red-500">*</span></label>
                        <input type="text" id="threads-client-id" v-model="form.client_id" placeholder="Enter your Threads App ID" required
                            :class="['w-full px-4 py-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-900 border rounded-lg transition-all',
                                errors.client_id ? 'border-red-500 focus:ring-2 focus:ring-red-500' : 'border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500']"/>
                        <p v-if="errors.client_id" class="text-xs text-red-600 dark:text-red-400 mt-1.5">{{ errors.client_id }}</p>
                        <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Get this from <a href="https://developers.facebook.com/apps" target="_blank" rel="noopener" class="text-blue-600 dark:text-blue-400 hover:underline font-medium">Meta for Developers</a></p>
                    </div>
                    <div>
                        <label for="threads-client-secret" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">App Secret <span class="text-red-500">*</span></label>
                        <div class="relative">
                            <input :type="showPassword ? 'text' : 'password'" id="threads-client-secret" v-model="form.client_secret" placeholder="Enter your Threads App Secret" required
                                :class="['w-full px-4 py-3 pr-12 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-slate-900 border rounded-lg transition-all',
                                    errors.client_secret ? 'border-red-500 focus:ring-2 focus:ring-red-500' : 'border-gray-300 dark:border-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-blue-500']"/>
                            <button type="button" @click="togglePasswordVisibility" class="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors">
                                <svg v-if="!showPassword" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/></svg>
                            </button>
                        </div>
                        <p v-if="errors.client_secret" class="text-xs text-red-600 dark:text-red-400 mt-1.5">{{ errors.client_secret }}</p>
                        <p v-else class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Keep this secret secure - never share publicly</p>
                    </div>
                    <div>
                        <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Redirect URI</label>
                        <div class="flex gap-2">
                            <input type="text" :value="form.redirect_uri" readonly class="flex-1 px-4 py-3 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-600 rounded-lg cursor-default"/>
                            <button type="button" @click="copyToClipboard(form.redirect_uri)" class="px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2">
                                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                                Copy
                            </button>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Add this redirect URI to your Threads app settings</p>
                    </div>
                    <div v-if="errors.connection" class="bg-red-50 dark:bg-red-900/20 border border-red-300 dark:border-red-900/50 rounded-xl p-4">
                        <div class="flex items-start gap-3">
                            <div class="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center flex-shrink-0">
                                <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"/></svg>
                            </div>
                            <div class="flex-1">
                                <p class="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">Connection Test Failed</p>
                                <p class="text-xs text-red-800 dark:text-red-300">{{ errors.connection }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="flex flex-col-reverse sm:flex-row gap-3 pt-2">
                        <button type="button" @click="toggleForm" class="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors">Cancel</button>
                        <button type="button" @click="testConnection" :disabled="isLoading || isTesting" class="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2">
                            <span v-if="isTesting" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            {{ isTesting ? 'Testing...' : 'Test Connection' }}
                        </button>
                        <button type="submit" :disabled="isLoading || isTesting" class="px-6 py-3 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2">
                            <span v-if="isLoading" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                            {{ isLoading ? 'Saving...' : 'Save Credentials' }}
                        </button>
                    </div>
                </form>
            </div>

            <div v-else class="flex flex-wrap gap-3 mt-5">
                <button v-if="!isConfigured" @click="toggleForm" class="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-sm">Configure Threads</button>
                <template v-else>
                    <button @click="testConnection" :disabled="isTesting" class="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2">
                        <span v-if="isTesting" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                        <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        {{ isTesting ? 'Testing...' : 'Test' }}
                    </button>
                    <button @click="toggleForm" class="px-5 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600 transition-all shadow-sm">Edit</button>
                    <button @click="removeCredentials" :disabled="isLoading" class="px-5 py-2.5 text-sm font-semibold text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm flex items-center gap-2">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                        Remove
                    </button>
                </template>
            </div>
        </div>
    `
};

// ============================================================================
// Main Application
// ============================================================================

createApp({
    components: {
        TwitterConfigCard,
        LinkedInConfigCard,
        ThreadsConfigCard,
        LoadingSkeleton
    },
    data() {
        return {
            toast: {
                show: false,
                type: 'success',
                message: '',
                description: ''
            },
            statusMessage: '',
            isAdmin: false,
            isLoading: true,
            platformStatus: {
                twitter: false,
                linkedin: false,
                threads: false
            }
        };
    },
    computed: {
        configuredCount() {
            return Object.values(this.platformStatus).filter(Boolean).length;
        }
    },
    methods: {
        showToast({ type, message, description = '' }) {
            this.toast = { show: true, type, message, description };
            this.statusMessage = `${message}. ${description}`;
            setTimeout(() => {
                this.toast.show = false;
            }, type === 'success' ? 3000 : 5000);
        },
        handleStatusUpdate({ platform, configured }) {
            this.platformStatus[platform] = configured;
        },
        async checkAdminAccess() {
            try {
                const response = await fetch(`${API_BASE_URL}/api/admin/oauth-credentials`, {
                    withCredentials: true
                });
                if (response.status === 403) {
                    this.isAdmin = false;
                    const friendlyMessage = getUserFriendlyError(new Error('403'));
                    this.showToast({
                        type: 'error',
                        message: 'Access Denied',
                        description: friendlyMessage
                    });
                } else if (response.ok) {
                    this.isAdmin = true;
                } else if (response.status === 401) {
                    window.location.href = '/login.html?return=' + encodeURIComponent(window.location.pathname);
                }
            } catch (error) {
                devError('Failed to verify admin access:', error);
                const friendlyMessage = getUserFriendlyError(error);
                this.showToast({
                    type: 'error',
                    message: 'Connection Error',
                    description: friendlyMessage
                });
            } finally {
                this.isLoading = false;
            }
        }
    },
    mounted() {
        if (!isAuthenticated()) {
            window.location.href = '/login.html?return=' + encodeURIComponent(window.location.pathname);
            return;
        }
        this.checkAdminAccess();
    }
}).mount('#app');
