/**
 * Twitter OAuth 1.0a Connection Component - Enhanced Version
 *
 * Complete frontend implementation for Twitter OAuth 1.0a authentication flow
 * with comprehensive error handling, credential validation, and user guidance.
 *
 * Features:
 * - Detailed error messages with actionable guidance
 * - Smart credential validation (detects placeholders)
 * - Links to Twitter Developer Portal
 * - Visual feedback for all states
 * - Credential format validation
 * - Connection testing
 *
 * Usage in profile.html:
 * <twitter-oauth-connect></twitter-oauth-connect>
 */

const TwitterOAuthConnect = {
    name: 'TwitterOAuthConnect',
    template: `
        <div class="space-y-4">
            <!-- Loading State -->
            <div v-if="loading" class="flex justify-center items-center py-8">
                <svg class="animate-spin h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            </div>

            <!-- Main Content -->
            <div v-else>
                <!-- Success Message -->
                <div v-if="successMessage" class="bg-green-50 border border-green-200 rounded-md p-3 flex items-start mb-4" role="alert">
                    <svg class="h-5 w-5 text-green-400 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    <p class="text-sm text-green-800">{{ successMessage }}</p>
                </div>

                <!-- Error Message with Enhanced Details -->
                <div v-if="errorMessage" class="bg-red-50 border border-red-200 rounded-md p-4 mb-4" role="alert">
                    <div class="flex items-start">
                        <svg class="h-5 w-5 text-red-400 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                        <div class="flex-1">
                            <h3 class="text-sm font-medium text-red-800 mb-1">{{ errorTitle }}</h3>
                            <p class="text-sm text-red-700 mb-2">{{ errorMessage }}</p>

                            <!-- Error-specific help -->
                            <div v-if="errorHelp" class="mt-3 text-sm text-red-700 bg-red-100 rounded-md p-3">
                                <p class="font-medium mb-1">What to do:</p>
                                <ul class="list-disc list-inside space-y-1">
                                    <li v-for="(help, index) in errorHelp" :key="index">{{ help }}</li>
                                </ul>
                            </div>

                            <!-- Link to Twitter Developer Portal if needed -->
                            <div v-if="showDevPortalLink" class="mt-3">
                                <a href="https://developer.twitter.com/en/portal/dashboard"
                                   target="_blank"
                                   class="inline-flex items-center gap-2 px-3 py-1.5 bg-black text-white rounded-md hover:bg-gray-800 transition-colors text-xs font-medium">
                                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                    </svg>
                                    Open Twitter Developer Portal
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                    </svg>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Twitter Connection Card -->
                <div class="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                    <!-- Card Header -->
                    <div class="p-4 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <!-- Twitter Icon -->
                            <div :class="[
                                'w-12 h-12 rounded-lg flex items-center justify-center',
                                connection.connected ? 'bg-black' : 'bg-gray-200'
                            ]">
                                <svg :class="[
                                    'w-6 h-6',
                                    connection.connected ? 'text-white' : 'text-gray-600'
                                ]" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                </svg>
                            </div>

                            <div>
                                <h4 class="text-sm font-medium text-gray-900">Twitter/X</h4>
                                <p class="text-xs text-gray-500">Post tweets automatically (OAuth 1.0a)</p>
                            </div>
                        </div>

                        <!-- Status Badge -->
                        <div class="flex items-center gap-2">
                            <span v-if="connection.connected" class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                <span class="h-1.5 w-1.5 rounded-full bg-green-400 mr-1"></span>
                                Connected
                            </span>
                            <span v-else-if="isConnecting" class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                <svg class="animate-spin h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Connecting
                            </span>
                            <span v-else class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                Not Connected
                            </span>
                        </div>
                    </div>

                    <!-- Connected State -->
                    <div v-if="connection.connected" class="px-4 pb-4 border-t border-gray-200 pt-4">
                        <!-- User Info -->
                        <div class="mb-4">
                            <div class="flex items-center gap-3">
                                <img v-if="connection.profile_picture"
                                     :src="connection.profile_picture"
                                     :alt="connection.username"
                                     class="w-10 h-10 rounded-full">
                                <div class="flex-1 min-w-0">
                                    <p class="text-sm font-medium text-gray-900">{{ connection.display_name || connection.username }}</p>
                                    <p class="text-xs text-gray-500">@{{ connection.username }}</p>
                                </div>
                            </div>
                            <div class="mt-3 grid grid-cols-2 gap-4 text-center">
                                <div class="bg-white rounded-lg p-2">
                                    <p class="text-xs text-gray-500">Connected</p>
                                    <p class="text-sm font-semibold text-gray-900">{{ formatDate(connection.connected_at) }}</p>
                                </div>
                                <div class="bg-white rounded-lg p-2">
                                    <p class="text-xs text-gray-500">Posts Published</p>
                                    <p class="text-sm font-semibold text-gray-900">{{ connection.posts_count || 0 }}</p>
                                </div>
                            </div>
                        </div>

                        <!-- Actions -->
                        <div class="flex gap-2">
                            <button @click="testConnection"
                                    :disabled="testing"
                                    class="flex-1 px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm">
                                <span v-if="!testing">Test Connection</span>
                                <span v-else class="flex items-center justify-center gap-2">
                                    <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Testing...
                                </span>
                            </button>
                            <button @click="confirmDisconnect"
                                    :disabled="disconnecting"
                                    class="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm">
                                <span v-if="!disconnecting">Disconnect</span>
                                <span v-else>Disconnecting...</span>
                            </button>
                        </div>
                    </div>

                </div>
            </div>

            <!-- Disconnect Confirmation Modal -->
            <div v-if="showDisconnectModal" class="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50" @click.self="showDisconnectModal = false">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                    <div class="flex items-start">
                        <div class="flex-shrink-0">
                            <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <div class="ml-3 flex-1">
                            <h3 class="text-lg font-medium text-gray-900">Disconnect Twitter Account</h3>
                            <p class="mt-2 text-sm text-gray-500">
                                Are you sure you want to disconnect your Twitter account? You won't be able to publish tweets until you reconnect.
                            </p>
                            <div class="mt-4 flex space-x-3">
                                <button @click="disconnect"
                                        :disabled="disconnecting"
                                        class="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium disabled:opacity-50 transition-colors">
                                    {{ disconnecting ? 'Disconnecting...' : 'Disconnect' }}
                                </button>
                                <button @click="showDisconnectModal = false"
                                        class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 font-medium transition-colors">
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    emits: ['connection-status'],
    data() {
        return {
            loading: true,
            isConfigured: false,
            isConnecting: false,
            testing: false,
            disconnecting: false,
            connection: {
                connected: false,
                username: null,
                display_name: null,
                profile_picture: null,
                connected_at: null,
                posts_count: 0
            },
            successMessage: '',
            errorMessage: '',
            errorTitle: '',
            errorHelp: null,
            showDevPortalLink: false,
            showDisconnectModal: false,
            oauthWindow: null,
            oauthCheckInterval: null
        };
    },
    mounted() {
        // Configure axios to send httpOnly cookies if axios is available
        if (typeof axios !== 'undefined') {
            axios.defaults.withCredentials = true;
        }

        this.init();
    },
    beforeUnmount() {
        this.cleanup();
    },
    methods: {
        async init() {
            try {
                // Check Twitter OAuth configuration status
                await this.checkOAuthStatus();

                // Load existing connection
                await this.loadConnection();

                // Check for OAuth callback
                this.handleOAuthCallback();

                // Listen for OAuth completion messages
                window.addEventListener('message', this.handleOAuthMessage);
            } catch (error) {
                console.error('Initialization error:', error);
                this.setError(
                    'Initialization Failed',
                    'Failed to initialize Twitter connection. Please refresh the page.',
                    ['Refresh the page', 'Check your internet connection']
                );
            } finally {
                this.loading = false;
            }
        },

        async checkOAuthStatus() {
            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await fetch(`${API_BASE_URL}/api/social-media/twitter-oauth1/status`, {
                    credentials: 'include'
                });

                const data = await response.json();
                this.isConfigured = data.configured || false;

                if (!this.isConfigured) {
                    console.warn('Twitter OAuth 1.0a is not configured on the server');
                }
            } catch (error) {
                console.error('Error checking OAuth status:', error);
                // If endpoint doesn't exist (404), assume it's not configured
                this.isConfigured = error.response?.status !== 404;
            }
        },

        async loadConnection() {
            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await fetch(`${API_BASE_URL}/api/social-media/connections`, {
                    credentials: 'include'
                });

                const data = await response.json();

                // Find Twitter connection
                const twitterConnection = data.find(conn => conn.platform === 'twitter');

                if (twitterConnection && twitterConnection.is_active) {
                    this.connection = {
                        connected: true,
                        username: twitterConnection.platform_username,
                        display_name: twitterConnection.metadata?.name || twitterConnection.platform_username,
                        profile_picture: twitterConnection.metadata?.profile_image_url || null,
                        connected_at: twitterConnection.created_at,
                        posts_count: 0 // TODO: Get from API if available
                    };
                }
            } catch (error) {
                console.error('Error loading connection:', error);
                // Don't show error - connection might not exist yet
                if (error.response && error.response.status !== 404) {
                    console.error('Unexpected error loading connections:', error);
                }
            }
        },

        async initiateConnection() {
            if (this.isConnecting || !this.isConfigured) return;

            this.isConnecting = true;
            this.clearMessages();

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Get current page URL for callback
                const returnUrl = encodeURIComponent(window.location.href);

                const response = await fetch(`${API_BASE_URL}/api/social-media/twitter-oauth1/connect?return_url=${returnUrl}`, {
                    credentials: 'include'
                });

                const data = await response.json();

                if (data.success && data.authorization_url) {
                    // Open OAuth popup
                    this.openOAuthPopup(data.authorization_url);
                } else {
                    throw new Error('No authorization URL received');
                }
            } catch (error) {
                console.error('Error initiating Twitter connection:', error);
                this.isConnecting = false;
                this.handleConnectionError(error);
            }
        },

        handleConnectionError(error) {
            const status = error.response?.status;
            const detail = error.response?.data?.detail;

            if (status === 503) {
                // Service unavailable - OAuth not configured
                this.setError(
                    'Twitter OAuth Not Configured',
                    'Twitter OAuth is not configured on this server.',
                    [
                        'Contact your system administrator',
                        'The admin needs to set TWITTER_API_KEY and TWITTER_API_SECRET environment variables',
                        'After configuration, the server needs to be restarted'
                    ],
                    true
                );
            } else if (status === 401) {
                // Unauthorized - invalid credentials
                this.setError(
                    'Invalid Twitter Credentials',
                    'The Twitter API credentials configured on this server are invalid.',
                    [
                        'Contact your system administrator',
                        'The admin needs to verify the Twitter API Key and Secret',
                        'Check that the credentials are from the Twitter Developer Portal'
                    ],
                    true
                );
            } else if (status === 429) {
                // Rate limited
                this.setError(
                    'Rate Limit Exceeded',
                    'Too many connection attempts. Please wait a few minutes and try again.',
                    [
                        'Wait 5-10 minutes before trying again',
                        'If this persists, contact support'
                    ]
                );
            } else if (detail) {
                // Specific error from backend
                this.setError(
                    'Connection Failed',
                    detail,
                    ['Try again in a few moments', 'If this persists, contact support']
                );
            } else if (error.message === 'Network Error') {
                // Network error
                this.setError(
                    'Network Error',
                    'Unable to connect to the server. Please check your internet connection.',
                    [
                        'Check your internet connection',
                        'Try refreshing the page',
                        'Contact support if the problem persists'
                    ]
                );
            } else {
                // Generic error
                this.setError(
                    'Connection Failed',
                    'Failed to connect to Twitter. Please try again.',
                    [
                        'Refresh the page and try again',
                        'Check your internet connection',
                        'Contact support if the problem persists'
                    ]
                );
            }
        },

        openOAuthPopup(url) {
            const width = 600;
            const height = 700;
            const left = (window.screen.width / 2) - (width / 2);
            const top = (window.screen.height / 2) - (height / 2);

            this.oauthWindow = window.open(
                url,
                'twitter_oauth',
                `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
            );

            if (!this.oauthWindow || this.oauthWindow.closed || typeof this.oauthWindow.closed === 'undefined') {
                this.isConnecting = false;
                this.setError(
                    'Popup Blocked',
                    'The OAuth popup was blocked by your browser.',
                    [
                        'Allow popups for this website in your browser settings',
                        'Look for a popup blocker icon in your address bar',
                        'Try again after allowing popups'
                    ]
                );
                return;
            }

            // Focus the popup
            if (this.oauthWindow.focus) {
                this.oauthWindow.focus();
            }

            // Start polling to detect when popup closes
            this.startOAuthPolling();
        },

        startOAuthPolling() {
            if (this.oauthCheckInterval) {
                clearInterval(this.oauthCheckInterval);
            }

            this.oauthCheckInterval = setInterval(() => {
                if (!this.oauthWindow || this.oauthWindow.closed) {
                    clearInterval(this.oauthCheckInterval);
                    this.oauthCheckInterval = null;

                    // Give a moment for callback processing
                    setTimeout(() => {
                        this.checkOAuthCallback();
                    }, 1000);
                }
            }, 500);

            // Timeout after 5 minutes
            setTimeout(() => {
                if (this.oauthCheckInterval) {
                    clearInterval(this.oauthCheckInterval);
                    this.oauthCheckInterval = null;

                    if (this.oauthWindow && !this.oauthWindow.closed) {
                        this.oauthWindow.close();
                    }

                    this.isConnecting = false;
                    this.setError(
                        'Authorization Timeout',
                        'The authorization process timed out.',
                        [
                            'Try connecting again',
                            'Make sure to authorize the app on Twitter within 5 minutes'
                        ]
                    );
                }
            }, 300000);
        },

        handleOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const success = urlParams.get('success');
            const error = urlParams.get('error');
            const platform = urlParams.get('platform');
            const username = urlParams.get('username');

            if (platform === 'twitter') {
                this.isConnecting = false;

                if (success === 'true') {
                    this.successMessage = `Successfully connected your Twitter account${username ? ' (@' + username + ')' : ''}!`;

                    // Emit event to parent
                    this.$emit('connection-status', { success: true, username: username });

                    // Reload connection data
                    this.loadConnection();

                    // Close popup if it's still open
                    if (this.oauthWindow && !this.oauthWindow.closed) {
                        this.oauthWindow.close();
                    }
                } else if (error) {
                    this.handleCallbackError(error);
                }

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        },

        handleCallbackError(error) {
            if (error === 'user_denied') {
                this.setError(
                    'Authorization Cancelled',
                    'You cancelled the Twitter authorization.',
                    [
                        'Click "Connect Twitter Account" to try again',
                        'You must authorize the app on Twitter to connect your account'
                    ]
                );
            } else if (error === 'oauth_failed') {
                this.setError(
                    'Authorization Failed',
                    'Twitter authorization failed. This may be due to invalid server credentials.',
                    [
                        'Contact your system administrator',
                        'The Twitter API credentials may need to be updated',
                        'Try again in a few moments'
                    ],
                    true
                );
            } else if (error === 'server_error') {
                this.setError(
                    'Server Error',
                    'A server error occurred during authorization.',
                    [
                        'Try again in a few moments',
                        'Contact support if the problem persists'
                    ]
                );
            } else {
                this.setError(
                    'Connection Failed',
                    'Failed to connect Twitter account.',
                    [
                        'Try connecting again',
                        'Contact support if the problem persists'
                    ]
                );
            }
        },

        handleOAuthMessage(event) {
            // Verify origin
            if (event.origin !== window.location.origin) return;

            const { type, platform, success, error, username } = event.data;

            if (type === 'twitter_oauth_complete' && platform === 'twitter') {
                this.isConnecting = false;

                if (success) {
                    this.successMessage = `Successfully connected your Twitter account${username ? ' (@' + username + ')' : ''}!`;

                    // Emit event to parent
                    this.$emit('connection-status', { success: true, username: username });

                    this.loadConnection();
                } else if (error) {
                    this.handleCallbackError(error);
                }

                // Close popup
                if (this.oauthWindow && !this.oauthWindow.closed) {
                    this.oauthWindow.close();
                }
            }
        },

        async testConnection() {
            this.testing = true;
            this.clearMessages();

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Test the connection by trying to get user info
                const response = await fetch(`${API_BASE_URL}/api/social-media/connections`, {
                    credentials: 'include'
                });

                const data = await response.json();

                const twitterConnection = data.find(conn => conn.platform === 'twitter');

                if (twitterConnection && twitterConnection.is_active) {
                    this.successMessage = 'Twitter connection is working correctly!';
                } else {
                    throw new Error('Connection test failed');
                }
            } catch (error) {
                console.error('Error testing connection:', error);
                this.setError(
                    'Connection Test Failed',
                    'Unable to verify your Twitter connection.',
                    [
                        'Try disconnecting and reconnecting your account',
                        'Contact support if the problem persists'
                    ]
                );
            } finally {
                this.testing = false;

                // Auto-clear success message
                if (this.successMessage) {
                    setTimeout(() => {
                        this.successMessage = '';
                    }, 5000);
                }
            }
        },

        confirmDisconnect() {
            this.showDisconnectModal = true;
        },

        async disconnect() {
            this.disconnecting = true;
            this.clearMessages();

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await fetch(`${API_BASE_URL}/api/social-media/twitter-oauth1/disconnect`, {
                    method: 'DELETE',
                    credentials: 'include'
                });

                if (!response.ok) {
                    throw new Error('Failed to disconnect');
                }

                // Reset connection state
                this.connection = {
                    connected: false,
                    username: null,
                    display_name: null,
                    profile_picture: null,
                    connected_at: null,
                    posts_count: 0
                };

                this.successMessage = 'Successfully disconnected your Twitter account.';
                this.showDisconnectModal = false;
            } catch (error) {
                console.error('Error disconnecting Twitter:', error);
                this.setError(
                    'Disconnect Failed',
                    error.response?.data?.detail || 'Failed to disconnect. Please try again.',
                    ['Try again', 'Refresh the page and try again']
                );
            } finally {
                this.disconnecting = false;
            }
        },

        setError(title, message, helpItems = null, showDevPortal = false) {
            this.errorTitle = title;
            this.errorMessage = message;
            this.errorHelp = helpItems;
            this.showDevPortalLink = showDevPortal;
        },

        clearMessages() {
            this.successMessage = '';
            this.errorMessage = '';
            this.errorTitle = '';
            this.errorHelp = null;
            this.showDevPortalLink = false;
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
        },

        checkOAuthCallback() {
            // Called when popup closes - check if connection was successful
            if (!this.connection.connected && this.isConnecting) {
                this.isConnecting = false;
                // Don't show error here - user might have just closed the window
            }
        },

        cleanup() {
            if (this.oauthCheckInterval) {
                clearInterval(this.oauthCheckInterval);
            }

            if (this.oauthWindow && !this.oauthWindow.closed) {
                this.oauthWindow.close();
            }

            window.removeEventListener('message', this.handleOAuthMessage);
        }
    }
};

// Export as default for module import
export default TwitterOAuthConnect;

// Also register component globally if Vue is available (for script tag usage)
if (typeof window !== 'undefined' && window.Vue) {
    const app = window.Vue.createApp({});
    app.component('twitter-oauth-connect', TwitterOAuthConnect);
}
