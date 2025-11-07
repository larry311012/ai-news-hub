/**
 * Twitter OAuth 1.0a Connection Component (UPDATED WITH WIZARD INTEGRATION)
 *
 * Complete frontend implementation for Twitter OAuth 1.0a authentication flow.
 * Now includes integration with the TwitterOAuthSetupWizard for user-owned credentials.
 *
 * Integrates with the profile page and handles:
 * - Connection initiation (centralized or user-owned)
 * - OAuth callback handling
 * - Connection status display
 * - Disconnect functionality
 * - Setup wizard for user-owned Twitter apps
 * - Error handling with user-friendly messages
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

                <!-- Error Message -->
                <div v-if="errorMessage" class="bg-red-50 border border-red-200 rounded-md p-3 flex items-start mb-4" role="alert">
                    <svg class="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                    <div class="flex-1">
                        <p class="text-sm text-red-800">{{ errorMessage }}</p>
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

                    <!-- Disconnected State -->
                    <div v-else class="px-4 pb-4 border-t border-gray-200 pt-4">
                        <!-- Setup Choice Info -->
                        <div class="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
                            <div class="flex">
                                <svg class="h-5 w-5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                                </svg>
                                <div class="ml-3">
                                    <h3 class="text-sm font-medium text-blue-800">Two Ways to Connect</h3>
                                    <div class="mt-2 text-xs text-blue-700 space-y-1">
                                        <p><strong>Option 1:</strong> Use centralized OAuth (if configured by admin)</p>
                                        <p><strong>Option 2:</strong> Set up your own Twitter developer account</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Centralized OAuth Not Available -->
                        <div v-if="!isConfigured" class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                            <div class="flex">
                                <svg class="h-5 w-5 text-yellow-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                                </svg>
                                <div class="ml-3">
                                    <p class="text-sm text-yellow-800">Centralized Twitter OAuth is not configured. You can still set up your own Twitter app below!</p>
                                </div>
                            </div>
                        </div>

                        <!-- Connection Buttons -->
                        <div class="space-y-3">
                            <!-- Centralized OAuth Button (if configured) -->
                            <button v-if="isConfigured"
                                    @click="initiateConnection"
                                    :disabled="isConnecting"
                                    class="w-full px-4 py-2 bg-black text-white rounded-md hover:bg-gray-800 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm flex items-center justify-center gap-2">
                                <span v-if="!isConnecting">
                                    <svg class="w-5 h-5 inline mr-1" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                    </svg>
                                    Quick Connect (Centralized)
                                </span>
                                <span v-else class="flex items-center gap-2">
                                    <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Opening Twitter...
                                </span>
                            </button>

                            <!-- Divider (only if centralized OAuth is configured) -->
                            <div v-if="isConfigured" class="relative">
                                <div class="absolute inset-0 flex items-center">
                                    <div class="w-full border-t border-gray-300"></div>
                                </div>
                                <div class="relative flex justify-center text-xs">
                                    <span class="px-2 bg-gray-50 text-gray-500">OR</span>
                                </div>
                            </div>

                            <!-- Setup Your Own Button -->
                            <button @click="openSetupWizard"
                                    class="w-full px-4 py-3 bg-gradient-to-r from-indigo-600 to-blue-600 text-white rounded-md hover:from-indigo-700 hover:to-blue-700 font-medium transition-all text-sm flex items-center justify-center gap-2 shadow-sm">
                                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                                </svg>
                                <span>Set Up Your Own Twitter App</span>
                            </button>

                            <p class="text-xs text-gray-500 text-center">
                                Recommended: More control over your Twitter credentials
                            </p>
                        </div>

                        <!-- Benefits of Own Setup -->
                        <div class="mt-4 bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-3">
                            <p class="text-xs font-medium text-purple-900 mb-2">Why set up your own Twitter app?</p>
                            <ul class="text-xs text-purple-800 space-y-1">
                                <li class="flex items-start gap-1">
                                    <svg class="w-3 h-3 text-purple-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                    </svg>
                                    <span>Full control over your API keys</span>
                                </li>
                                <li class="flex items-start gap-1">
                                    <svg class="w-3 h-3 text-purple-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                    </svg>
                                    <span>No dependency on server configuration</span>
                                </li>
                                <li class="flex items-start gap-1">
                                    <svg class="w-3 h-3 text-purple-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                    </svg>
                                    <span>Easy 5-minute guided setup</span>
                                </li>
                            </ul>
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

            <!-- Setup Wizard -->
            <twitter-oauth-setup-wizard
                :open="showSetupWizard"
                @close="showSetupWizard = false"
                @completed="handleSetupComplete">
            </twitter-oauth-setup-wizard>
        </div>
    `,
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
            showDisconnectModal: false,
            showSetupWizard: false,
            oauthWindow: null,
            oauthCheckInterval: null
        };
    },
    mounted() {
        // Configure axios to send httpOnly cookies
        axios.defaults.withCredentials = true;

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
                this.errorMessage = 'Failed to initialize Twitter connection. Please refresh the page.';
            } finally {
                this.loading = false;
            }
        },

        async checkOAuthStatus() {
            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                this.isConfigured = response.data.configured || false;

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

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                // Find Twitter connection
                const twitterConnection = response.data.find(conn => conn.platform === 'twitter');

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

        openSetupWizard() {
            this.showSetupWizard = true;
            this.errorMessage = '';
            this.successMessage = '';
        },

        async handleSetupComplete(data) {
            this.successMessage = `Successfully connected Twitter account @${data.username}!`;

            // Reload connection status
            await this.loadConnection();

            // Clear success message after 5 seconds
            setTimeout(() => {
                this.successMessage = '';
            }, 5000);
        },

        async initiateConnection() {
            if (this.isConnecting || !this.isConfigured) return;

            this.isConnecting = true;
            this.errorMessage = '';
            this.successMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Get current page URL for callback
                const returnUrl = encodeURIComponent(window.location.href);

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                if (response.data.success && response.data.authorization_url) {
                    // Open OAuth popup
                    this.openOAuthPopup(response.data.authorization_url);
                } else {
                    throw new Error('No authorization URL received');
                }
            } catch (error) {
                console.error('Error initiating Twitter connection:', error);
                this.isConnecting = false;

                if (error.response?.status === 503) {
                    this.errorMessage = 'Twitter OAuth is not configured on this server. Please use "Set Up Your Own Twitter App" instead.';
                } else if (error.response?.data?.detail) {
                    this.errorMessage = error.response.data.detail;
                } else {
                    this.errorMessage = 'Failed to connect to Twitter. Please try the "Set Up Your Own Twitter App" option.';
                }
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
                this.errorMessage = 'Popup was blocked. Please allow popups for this site and try again.';
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
                    this.errorMessage = 'Authorization timed out. Please try again.';
                }
            }, 300000);
        },

        async checkOAuthCallback() {
            // Check if connection was established
            await this.loadConnection();

            if (!this.connection.connected) {
                this.isConnecting = false;
            }
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
                    this.successMessage = 'Successfully connected your Twitter account!';

                    // Reload connection data
                    this.loadConnection();

                    // Close popup if it's still open
                    if (this.oauthWindow && !this.oauthWindow.closed) {
                        this.oauthWindow.close();
                    }
                } else if (error) {
                    let errorMsg = 'Failed to connect Twitter account.';

                    if (error === 'user_denied') {
                        errorMsg = 'You cancelled the authorization. Please try again if you want to connect.';
                    } else if (error === 'oauth_failed') {
                        errorMsg = 'Twitter authorization failed. Please try again.';
                    } else if (error === 'server_error') {
                        errorMsg = 'Server error occurred. Please try again in a moment.';
                    }

                    this.errorMessage = errorMsg;
                }

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        },

        handleOAuthMessage(event) {
            // Verify origin
            if (event.origin !== window.location.origin) return;

            const { type, platform, success, error, username } = event.data;

            if (type === 'twitter_oauth_complete' && platform === 'twitter') {
                this.isConnecting = false;

                if (success) {
                    this.successMessage = 'Successfully connected your Twitter account!';
                    this.loadConnection();
                } else if (error) {
                    this.errorMessage = typeof error === 'string' ? error : 'Failed to connect Twitter account.';
                }

                // Close popup
                if (this.oauthWindow && !this.oauthWindow.closed) {
                    this.oauthWindow.close();
                }
            }
        },

        async testConnection() {
            this.testing = true;
            this.errorMessage = '';
            this.successMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Test the connection by trying to get user info
                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                const twitterConnection = response.data.find(conn => conn.platform === 'twitter');

                if (twitterConnection && twitterConnection.is_active) {
                    this.successMessage = 'Twitter connection is working correctly!';
                } else {
                    throw new Error('Connection test failed');
                }
            } catch (error) {
                console.error('Error testing connection:', error);
                this.errorMessage = error.response?.data?.detail || 'Connection test failed. Please try reconnecting.';
            } finally {
                this.testing = false;

                // Auto-clear success message
                if (this.successMessage) {
                    setTimeout(() => {
                        this.successMessage = '';
                    }, 3000);
                }
            }
        },

        confirmDisconnect() {
            this.showDisconnectModal = true;
        },

        async disconnect() {
            this.disconnecting = true;
            this.errorMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                await axios.delete("/api/user/twitter", {
                withCredentials: true
            });

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
                this.errorMessage = error.response?.data?.detail || 'Failed to disconnect. Please try again.';
            } finally {
                this.disconnecting = false;
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

// Register component globally if Vue is available
if (typeof window !== 'undefined' && window.Vue) {
    const app = window.Vue.createApp({});
    app.component('twitter-oauth-connect', TwitterOAuthConnect);
}
