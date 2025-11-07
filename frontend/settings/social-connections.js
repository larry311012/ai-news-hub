/**
 * Social Media Connections - Settings Page
 *
 * Modern component-based implementation following the design specifications.
 * Handles OAuth flows (OAuth 1.0a for Twitter, OAuth 2.0 for others),
 * connection management, and real-time status updates.
 */

const { createApp } = Vue;

// API Configuration
const API_BASE_URL = window.location.origin.includes('localhost')
    ? 'http://localhost:8000/api'
    : '/api';

// =============================================================================
// Platform Icon Component
// =============================================================================
const PlatformIcon = {
    name: 'PlatformIcon',
    props: {
        platform: {
            type: String,
            required: true,
            validator: (value) => ['linkedin', 'twitter', 'threads'].includes(value)
        },
        connected: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        iconColor() {
            if (!this.connected) return 'text-gray-600 dark:text-gray-400';

            switch (this.platform) {
                case 'linkedin':
                    return 'text-blue-600 dark:text-blue-400';
                case 'twitter':
                    return 'text-gray-900 dark:text-gray-100';
                case 'threads':
                    return 'text-gray-900 dark:text-gray-100';
                default:
                    return 'text-gray-600 dark:text-gray-400';
            }
        },
        backgroundColor() {
            if (!this.connected) return 'bg-gray-100 dark:bg-slate-700';

            switch (this.platform) {
                case 'linkedin':
                    return 'bg-blue-50 dark:bg-blue-900/20';
                case 'twitter':
                    return 'bg-gray-100 dark:bg-gray-800';
                case 'threads':
                    return 'bg-gray-100 dark:bg-gray-800';
                default:
                    return 'bg-gray-100 dark:bg-slate-700';
            }
        }
    },
    template: `
        <div :class="[\`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0\`, backgroundColor]">
            <!-- LinkedIn Icon -->
            <svg v-if="platform === 'linkedin'" viewBox="0 0 24 24" fill="currentColor" :class="[\`w-6 h-6\`, iconColor]">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
            </svg>

            <!-- Twitter/X Icon -->
            <svg v-else-if="platform === 'twitter'" viewBox="0 0 24 24" fill="currentColor" :class="[\`w-6 h-6\`, iconColor]">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>

            <!-- Threads Icon -->
            <svg v-else-if="platform === 'threads'" viewBox="0 0 24 24" fill="currentColor" :class="[\`w-6 h-6\`, iconColor]">
                <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.704-1.488 0-2.743-.546-3.625-1.577a5.688 5.688 0 0 1-1.081-2.174c-.288-.901-.438-1.886-.438-2.936 0-1.043.156-2.03.465-2.935.29-.852.703-1.613 1.226-2.26.924-1.132 2.141-1.706 3.614-1.706 1.493 0 2.718.573 3.644 1.705.488.598.853 1.326 1.086 2.167l1.01-.548c-.34-.876-.82-1.647-1.429-2.29-1.17-1.238-2.707-1.914-4.562-2.009-.025-.02-.05-.041-.075-.06l-.023-.023c-.878-.834-1.898-1.255-3.034-1.255-1.137 0-2.156.423-3.032 1.258-.866.826-1.313 1.904-1.313 3.203v.989c.032 2.015.827 3.51 2.37 4.45.916.56 1.996.844 3.208.844 1.208 0 2.283-.285 3.197-.845.492-.3.948-.69 1.358-1.163.37-.429.676-.92.91-1.465l.022.012c.01.005.018.012.028.018.464.315.84.693 1.117 1.122.397.614.617 1.34.654 2.157.023.485.012.97-.031 1.452-.095 1.032-.38 1.977-.849 2.813-.698 1.244-1.784 2.202-3.23 2.85-.967.43-2.07.65-3.275.65h-.001z"/>
            </svg>
        </div>
    `
};

// =============================================================================
// Status Badge Component
// =============================================================================
const StatusBadge = {
    name: 'StatusBadge',
    props: {
        status: {
            type: String,
            required: true,
            validator: (value) => ['connected', 'error', 'expired', 'loading'].includes(value)
        }
    },
    computed: {
        config() {
            const configs = {
                connected: {
                    bg: 'bg-green-50 dark:bg-green-900/20',
                    text: 'text-green-700 dark:text-green-400',
                    icon: 'M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z',
                    label: 'Connected'
                },
                error: {
                    bg: 'bg-red-50 dark:bg-red-900/20',
                    text: 'text-red-700 dark:text-red-400',
                    icon: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
                    label: 'Failed'
                },
                expired: {
                    bg: 'bg-amber-50 dark:bg-amber-900/20',
                    text: 'text-amber-700 dark:text-amber-400',
                    icon: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
                    label: 'Action Required'
                },
                loading: {
                    bg: 'bg-blue-50 dark:bg-blue-900/20',
                    text: 'text-blue-700 dark:text-blue-400',
                    icon: null,
                    label: 'Connecting'
                }
            };
            return configs[this.status] || configs.error;
        }
    },
    template: `
        <span :class="[\`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full animate-fadeIn\`, config.bg, config.text]">
            <svg v-if="config.icon" class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" :d="config.icon" clip-rule="evenodd"/>
            </svg>
            <span v-if="status === 'loading'" class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
            {{ config.label }}
        </span>
    `
};

// =============================================================================
// Connection Card Component
// =============================================================================
const ConnectionCard = {
    name: 'ConnectionCard',
    components: {
        PlatformIcon,
        StatusBadge
    },
    props: {
        connection: {
            type: Object,
            required: true
        }
    },
    computed: {
        platformName() {
            const names = {
                linkedin: 'LinkedIn',
                twitter: 'Twitter/X',
                threads: 'Threads'
            };
            return names[this.connection.platform] || this.connection.platform;
        },
        buttonVariant() {
            switch (this.connection.status) {
                case 'loading':
                    return 'disabled';
                case 'error':
                    return 'danger';
                case 'expired':
                    return 'warning';
                case 'connected':
                    return 'secondary';
                default:
                    return 'primary';
            }
        },
        buttonLabel() {
            switch (this.connection.status) {
                case 'loading':
                    return 'Connecting';
                case 'error':
                    return 'Retry';
                case 'expired':
                    return 'Reconnect';
                case 'connected':
                    return 'Disconnect';
                default:
                    return 'Connect';
            }
        },
        buttonClasses() {
            const base = 'px-4 py-2 text-sm font-medium rounded-lg transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 flex-shrink-0';
            const variants = {
                primary: 'bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500',
                secondary: 'border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-300 focus:ring-gray-400',
                danger: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500',
                warning: 'bg-amber-600 hover:bg-amber-700 text-white focus:ring-amber-500',
                disabled: 'bg-gray-300 dark:bg-slate-700 text-gray-500 dark:text-gray-500 cursor-not-allowed'
            };
            return `${base} ${variants[this.buttonVariant]}`;
        },
        showErrorMessage() {
            return this.connection.status === 'error' && this.connection.error_message;
        },
        showExpiredWarning() {
            return this.connection.status === 'expired';
        }
    },
    methods: {
        handleClick() {
            if (this.connection.status === 'loading') return;

            if (this.connection.connected && this.connection.status !== 'expired') {
                this.$emit('disconnect');
            } else {
                this.$emit('connect');
            }
        },
        formatDate(dateString) {
            if (!dateString) return 'Never';

            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;

            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        }
    },
    template: `
        <div :class="[
            'bg-white dark:bg-slate-800 border rounded-xl p-4 hover:shadow-md transition-shadow duration-200',
            connection.connected ? 'border-gray-200 dark:border-slate-700' : 'border-gray-200 dark:border-slate-700'
        ]">
            <div class="flex items-start justify-between gap-4">
                <div class="flex items-start gap-4 flex-1 min-w-0">
                    <!-- Platform Icon -->
                    <platform-icon
                        :platform="connection.platform"
                        :connected="connection.connected">
                    </platform-icon>

                    <!-- Platform Info -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-2">
                            <h3 class="text-base font-semibold text-gray-900 dark:text-gray-50">
                                {{ platformName }}
                            </h3>
                            <status-badge
                                v-if="connection.status && connection.status !== 'disconnected'"
                                :status="connection.status">
                            </status-badge>
                        </div>

                        <!-- Connected State -->
                        <template v-if="connection.connected && connection.username">
                            <div class="flex items-center gap-2 mb-1">
                                <img v-if="connection.avatar"
                                     :src="connection.avatar"
                                     :alt="connection.username + ' profile'"
                                     class="w-6 h-6 rounded-full">
                                <span class="text-sm text-gray-700 dark:text-gray-300 font-medium truncate">
                                    @{{ connection.username }}
                                </span>
                            </div>
                            <p v-if="connection.connectedAt" class="text-xs text-gray-500 dark:text-gray-400">
                                Connected {{ formatDate(connection.connectedAt) }}
                            </p>
                        </template>

                        <!-- Disconnected State -->
                        <template v-else-if="!connection.connected && connection.status !== 'loading'">
                            <p class="text-sm text-gray-600 dark:text-gray-400">
                                Not connected
                            </p>
                        </template>

                        <!-- Loading State -->
                        <template v-else-if="connection.status === 'loading'">
                            <div class="flex items-center gap-2">
                                <div class="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                                <p class="text-sm text-gray-600 dark:text-gray-400">
                                    Opening Twitter...
                                </p>
                            </div>
                        </template>

                        <!-- Error State -->
                        <p v-if="showErrorMessage" class="text-sm text-red-600 dark:text-red-400 mt-2">
                            {{ connection.error_message }}
                        </p>

                        <!-- Expired State -->
                        <p v-if="showExpiredWarning" class="text-sm text-amber-700 dark:text-amber-400 mt-2">
                            Connection expired. Please reconnect your account.
                        </p>
                    </div>
                </div>

                <!-- Action Button -->
                <div class="flex-shrink-0">
                    <button
                        @click="handleClick"
                        :disabled="connection.status === 'loading'"
                        :class="buttonClasses"
                        :aria-label="buttonLabel + ' ' + platformName + ' account'">
                        <span v-if="connection.status === 'loading'" class="flex items-center gap-2">
                            <span class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
                            {{ buttonLabel }}
                        </span>
                        <span v-else>{{ buttonLabel }}</span>
                    </button>
                </div>
            </div>
        </div>
    `
};

// =============================================================================
// Main App
// =============================================================================
createApp({
    components: {
        ConnectionCard
    },
    data() {
        return {
            connections: {
                linkedin: {
                    platform: 'linkedin',
                    connected: false,
                    status: 'disconnected',
                    username: null,
                    avatar: null,
                    connectedAt: null,
                    error_message: null
                },
                twitter: {
                    platform: 'twitter',
                    connected: false,
                    status: 'disconnected',
                    username: null,
                    avatar: null,
                    connectedAt: null,
                    error_message: null
                },
                threads: {
                    platform: 'threads',
                    connected: false,
                    status: 'disconnected',
                    username: null,
                    avatar: null,
                    connectedAt: null,
                    error_message: null
                }
            },
            toast: {
                show: false,
                type: 'success',
                message: '',
                description: ''
            },
            oauthWindow: null,
            oauthCheckInterval: null,
            isConfigCheckDone: false
        };
    },
    computed: {
        connectedCount() {
            return Object.values(this.connections).filter(c => c.connected).length;
        },
        totalCount() {
            return Object.keys(this.connections).length;
        }
    },
    async mounted() {

        // Check Twitter OAuth 1.0a configuration status
        await this.checkTwitterOAuthConfig();

        // Load connections
        await this.loadConnections();

        // Listen for OAuth messages
        window.addEventListener('message', this.handleOAuthMessage);

        // Check for OAuth callback
        this.checkOAuthCallback();
    },
    beforeUnmount() {
        if (this.oauthCheckInterval) {
            clearInterval(this.oauthCheckInterval);
        }
        window.removeEventListener('message', this.handleOAuthMessage);
    },
    methods: {
        /**
         * Check if Twitter OAuth 1.0a is configured on the backend
         */
        async checkTwitterOAuthConfig() {
            try {
                const response = await fetch(`${API_BASE_URL}/social-media/twitter-oauth1/status`);

                if (response.ok) {
                    const data = await response.json();

                    if (!data.configured) {
                        // Twitter OAuth 1.0a not configured on server
                        this.connections.twitter.status = 'error';
                        this.connections.twitter.error_message = 'Twitter OAuth is not configured on this server. Please contact support.';
                    }

                    this.isConfigCheckDone = true;
                } else if (response.status === 404) {
                    // Endpoint doesn't exist - old OAuth 2.0 setup
                    console.info('Twitter OAuth 1.0a endpoints not available, using OAuth 2.0');
                    this.isConfigCheckDone = true;
                }
            } catch (error) {
                console.error('Error checking Twitter OAuth config:', error);
                // Don't show error to user - fail silently and try connection anyway
                this.isConfigCheckDone = true;
            }
        },

        async loadConnections() {
            try {
                const response = await fetch(`${API_BASE_URL}/social-media/connections`, {
                    credentials: 'include'
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/auth.html?return=' + encodeURIComponent(window.location.pathname);
                        return;
                    }
                    throw new Error('Failed to load connections');
                }

                const data = await response.json();

                // Update connections with backend data
                data.forEach(conn => {
                    if (this.connections[conn.platform]) {
                        this.connections[conn.platform] = {
                            ...this.connections[conn.platform],
                            connected: conn.is_active,
                            status: conn.is_expired ? 'expired' : (conn.is_active ? 'connected' : 'disconnected'),
                            username: conn.platform_username,
                            avatar: null, // TODO: Add avatar support
                            connectedAt: conn.created_at,
                            error_message: conn.error_message
                        };
                    }
                });

            } catch (error) {
                console.error('Error loading connections:', error);
                this.showToast('error', 'Failed to load connections', error.message);
            }
        },

        async handleConnect(platform) {
            this.connections[platform].status = 'loading';
            this.connections[platform].error_message = null;

            try {
                // Determine which endpoint to use based on platform
                let endpoint;

                if (platform === 'twitter') {
                    // Twitter uses OAuth 1.0a
                    endpoint = `${API_BASE_URL}/social-media/twitter-oauth1/connect`;
                } else {
                    // LinkedIn and Threads use OAuth 2.0
                    endpoint = `${API_BASE_URL}/social-media/${platform}/connect`;
                }

                const response = await fetch(endpoint, {
                    credentials: 'include'
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));

                    if (response.status === 503) {
                        // Service unavailable - OAuth not configured
                        throw new Error('Twitter connection is not configured on this server. Please contact support.');
                    }

                    throw new Error(errorData.detail || 'Failed to initiate connection');
                }

                const data = await response.json();
                const authUrl = data.authorization_url;

                if (!authUrl) throw new Error('No authorization URL received');

                // Store platform for callback
                sessionStorage.setItem('oauth_platform', platform);

                // Open OAuth window
                this.openOAuthWindow(authUrl, platform);

            } catch (error) {
                console.error(`Error connecting to ${platform}:`, error);
                this.connections[platform].status = 'error';

                // Friendly error messages
                let errorMessage = 'Connection failed. Please try again.';

                if (error.message.includes('not configured')) {
                    errorMessage = 'Twitter is not set up on this server. Please contact support.';
                } else if (error.message.includes('network') || error.message.includes('fetch')) {
                    errorMessage = 'Network error. Check your internet connection.';
                }

                this.connections[platform].error_message = errorMessage;
                this.showToast('error', `Failed to connect to ${this.getPlatformName(platform)}`, errorMessage);
            }
        },

        async handleDisconnect(platform) {
            const platformName = this.getPlatformName(platform);

            if (!confirm(`Are you sure you want to disconnect from ${platformName}?`)) {
                return;
            }

            this.connections[platform].status = 'loading';

            try {
                const response = await fetch(`${API_BASE_URL}/social-media/${platform}/disconnect`, {
                    method: 'DELETE',
                    credentials: 'include'
                });

                if (!response.ok) throw new Error('Failed to disconnect');

                this.connections[platform] = {
                    platform,
                    connected: false,
                    status: 'disconnected',
                    username: null,
                    avatar: null,
                    connectedAt: null,
                    error_message: null
                };

                this.showToast('success', `Disconnected from ${platformName}`);

            } catch (error) {
                console.error(`Error disconnecting from ${platform}:`, error);
                this.connections[platform].status = 'error';
                this.showToast('error', `Failed to disconnect from ${platformName}`, 'Please try again.');
            }
        },

        openOAuthWindow(url, platform) {
            const width = 600;
            const height = 700;
            const left = window.screen.width / 2 - width / 2;
            const top = window.screen.height / 2 - height / 2;

            this.oauthWindow = window.open(
                url,
                `oauth_${platform}`,
                `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
            );

            if (!this.oauthWindow || this.oauthWindow.closed) {
                this.showToast('error', 'Popup blocked', 'Please allow popups for this site and try again.');
                this.connections[platform].status = 'disconnected';
                return;
            }

            if (this.oauthWindow.focus) {
                this.oauthWindow.focus();
            }

            this.startOAuthPolling(platform);
        },

        startOAuthPolling(platform) {
            if (this.oauthCheckInterval) {
                clearInterval(this.oauthCheckInterval);
            }

            this.oauthCheckInterval = setInterval(() => {
                if (!this.oauthWindow || this.oauthWindow.closed) {
                    clearInterval(this.oauthCheckInterval);
                    this.oauthCheckInterval = null;

                    setTimeout(() => {
                        this.checkOAuthSuccess(platform);
                    }, 1000);
                }
            }, 500);

            // 5 minute timeout
            setTimeout(() => {
                if (this.oauthCheckInterval) {
                    clearInterval(this.oauthCheckInterval);
                    this.oauthCheckInterval = null;
                    if (this.oauthWindow && !this.oauthWindow.closed) {
                        this.oauthWindow.close();
                    }
                    this.connections[platform].status = 'disconnected';
                    this.showToast('error', 'Connection timeout', 'Authorization timed out. Please try again.');
                }
            }, 300000);
        },

        async checkOAuthSuccess(platform) {
            const urlParams = new URLSearchParams(window.location.search);
            const success = urlParams.get('success');
            const error = urlParams.get('error');
            const callbackPlatform = urlParams.get('platform');

            // OAuth 2.0 parameters
            const code = urlParams.get('code');
            const state = urlParams.get('state');

            // OAuth 1.0a parameters (Twitter)
            const oauthToken = urlParams.get('oauth_token');
            const oauthVerifier = urlParams.get('oauth_verifier');
            const denied = urlParams.get('denied');

            // Check if this is an OAuth callback
            const isOAuth2Callback = code && state;
            const isOAuth1Callback = oauthToken && oauthVerifier;
            const isOAuthDenied = denied;

            if (success === 'true' && callbackPlatform === platform) {
                await this.loadConnections();
                this.showToast('success', `Successfully connected to ${this.getPlatformName(platform)}!`);

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            } else if (error) {
                this.connections[platform].status = 'error';

                // Friendly error messages
                let errorMessage = 'Connection failed';

                if (error === 'user_denied' || isOAuthDenied) {
                    errorMessage = 'You cancelled the authorization. Click Connect to try again.';
                } else if (error === 'popup_blocked') {
                    errorMessage = 'Popup was blocked. Please enable popups and try again.';
                } else if (error === 'oauth_failed') {
                    errorMessage = 'Authorization failed. Please try again.';
                } else if (error === 'server_error') {
                    errorMessage = 'Server error. Please try again in a moment.';
                }

                this.connections[platform].error_message = errorMessage;
                this.showToast('error', `Failed to connect to ${this.getPlatformName(platform)}`, errorMessage);

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            } else if (isOAuthDenied) {
                // User explicitly denied OAuth 1.0a authorization
                this.connections[platform].status = 'disconnected';
                this.showToast('error', 'Authorization cancelled', 'You cancelled the authorization. Click Connect to try again.');

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            } else if (!isOAuth2Callback && !isOAuth1Callback) {
                // User closed popup without completing authorization
                this.connections[platform].status = 'disconnected';
            }
        },

        handleOAuthMessage(event) {
            if (event.origin !== window.location.origin) return;

            const { type, platform, success, error } = event.data;

            if (type === 'oauth_complete') {
                if (success) {
                    this.loadConnections();
                    this.showToast('success', `Successfully connected to ${this.getPlatformName(platform)}!`);
                } else if (error) {
                    this.connections[platform].status = 'error';

                    // Friendly error message
                    let errorMessage = 'Connection failed. Please try again.';
                    if (typeof error === 'string') {
                        if (error.includes('denied')) {
                            errorMessage = 'Authorization was cancelled.';
                        } else if (error.includes('network')) {
                            errorMessage = 'Network error. Check your connection.';
                        }
                    }

                    this.connections[platform].error_message = errorMessage;
                    this.showToast('error', `Failed to connect to ${this.getPlatformName(platform)}`, errorMessage);
                }
            }
        },

        checkOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const success = urlParams.get('success');
            const error = urlParams.get('error');
            const platform = urlParams.get('platform');

            if (success === 'true' && platform) {
                this.showToast('success', `Successfully connected to ${this.getPlatformName(platform)}!`);
                window.history.replaceState({}, document.title, window.location.pathname);
            } else if (error && platform) {
                // Friendly error messages
                let errorMessage = 'Connection failed';

                if (error === 'user_denied') {
                    errorMessage = 'You cancelled the authorization.';
                } else if (error === 'oauth_failed') {
                    errorMessage = 'Authorization failed. Please try again.';
                } else if (error === 'server_error') {
                    errorMessage = 'Server error. Please try again in a moment.';
                }

                this.showToast('error', `Failed to connect to ${this.getPlatformName(platform)}`, errorMessage);
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        },

        showToast(type, message, description = '') {
            this.toast = {
                show: true,
                type,
                message,
                description
            };

            setTimeout(() => {
                this.toast.show = false;
            }, type === 'success' ? 3000 : 5000);
        },

        getPlatformName(platform) {
            const names = {
                linkedin: 'LinkedIn',
                twitter: 'Twitter/X',
                threads: 'Threads'
            };
            return names[platform] || platform;
        }
    }
}).mount('#app');
