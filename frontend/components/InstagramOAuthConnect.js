/**
 * Instagram OAuth Connection Component
 *
 * Complete frontend implementation for Instagram Business Account OAuth flow
 * Requires Facebook OAuth for Instagram Graph API access
 *
 * Features:
 * - Instagram Business account connection
 * - OAuth via Facebook Graph API
 * - Connection status display
 * - Test and disconnect functionality
 *
 * Usage in profile.html:
 * <instagram-oauth-connect></instagram-oauth-connect>
 */

const InstagramOAuthConnect = {
    name: 'InstagramOAuthConnect',
    template: `
        <div class="space-y-4">
            <!-- Loading State -->
            <div v-if="loading" class="flex justify-center items-center py-8">
                <svg class="animate-spin h-8 w-8 text-pink-600" fill="none" viewBox="0 0 24 24">
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
                <div v-if="errorMessage" class="bg-red-50 border border-red-200 rounded-md p-4 mb-4" role="alert">
                    <div class="flex items-start">
                        <svg class="h-5 w-5 text-red-400 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                        <div class="flex-1">
                            <h3 class="text-sm font-medium text-red-800 mb-1">{{ errorTitle }}</h3>
                            <p class="text-sm text-red-700">{{ errorMessage }}</p>
                        </div>
                    </div>
                </div>

                <!-- Instagram Connection Card -->
                <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg border-2 border-gray-200 overflow-hidden">
                    <!-- Card Header -->
                    <div class="p-4 flex items-center justify-between bg-white bg-opacity-90 backdrop-blur">
                        <div class="flex items-center gap-3">
                            <!-- Instagram Icon -->
                            <div :class="[
                                'w-12 h-12 rounded-xl flex items-center justify-center',
                                connection.connected ? 'bg-gradient-to-br from-purple-600 via-pink-600 to-orange-600' : 'bg-gray-200'
                            ]">
                                <svg :class="[
                                    'w-6 h-6',
                                    connection.connected ? 'text-white' : 'text-gray-600'
                                ]" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z"/>
                                </svg>
                            </div>

                            <div>
                                <h4 class="text-sm font-medium text-gray-900">Instagram Business</h4>
                                <p class="text-xs text-gray-500">Publish photos & carousels (requires Facebook)</p>
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
                    <div v-if="connection.connected" class="px-4 pb-4 bg-white bg-opacity-90 backdrop-blur border-t border-gray-200 pt-4">
                        <!-- User Info -->
                        <div class="mb-4">
                            <div class="flex items-center gap-3">
                                <img v-if="connection.profile_picture"
                                     :src="connection.profile_picture"
                                     :alt="connection.username"
                                     class="w-10 h-10 rounded-full ring-2 ring-pink-500">
                                <div v-else class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">
                                    {{ connection.username ? connection.username[0].toUpperCase() : 'I' }}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="text-sm font-medium text-gray-900">{{ connection.display_name || connection.username }}</p>
                                    <p class="text-xs text-gray-500">@{{ connection.username }}</p>
                                </div>
                            </div>
                            <div class="mt-3 grid grid-cols-2 gap-4 text-center">
                                <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-2">
                                    <p class="text-xs text-gray-500">Connected</p>
                                    <p class="text-sm font-semibold text-gray-900">{{ formatDate(connection.connected_at) }}</p>
                                </div>
                                <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-2">
                                    <p class="text-xs text-gray-500">Posts Published</p>
                                    <p class="text-sm font-semibold text-gray-900">{{ connection.posts_count || 0 }}</p>
                                </div>
                            </div>
                        </div>

                        <!-- Actions -->
                        <div class="flex gap-2">
                            <button @click="testConnection"
                                    :disabled="testing"
                                    class="flex-1 px-4 py-2 border-2 border-pink-600 text-pink-600 rounded-md hover:bg-pink-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm">
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
                    <div v-else class="px-4 pb-4 bg-white bg-opacity-90 backdrop-blur border-t border-gray-200 pt-4">
                        <!-- Info Box -->
                        <div class="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
                            <div class="flex">
                                <svg class="h-5 w-5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                                </svg>
                                <div class="ml-3">
                                    <h3 class="text-sm font-medium text-blue-800">Requirements</h3>
                                    <div class="mt-2 text-xs text-blue-700">
                                        <ul class="list-disc list-inside space-y-1">
                                            <li>Instagram Business or Creator account</li>
                                            <li>Account must be linked to a Facebook Page</li>
                                            <li>Facebook account to authorize</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Configuration Status -->
                        <div v-if="!isConfigured" class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                            <div class="flex">
                                <svg class="h-5 w-5 text-yellow-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                                </svg>
                                <div class="ml-3">
                                    <h4 class="text-sm font-medium text-yellow-800">Instagram OAuth Not Configured</h4>
                                    <p class="text-sm text-yellow-700 mt-1">Contact your administrator to enable Instagram integration.</p>
                                </div>
                            </div>
                        </div>

                        <!-- Connect Button -->
                        <button @click="initiateConnection"
                                :disabled="isConnecting || !isConfigured"
                                class="w-full px-4 py-2 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-600 text-white rounded-md hover:from-purple-700 hover:via-pink-700 hover:to-orange-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm flex items-center justify-center gap-2 shadow-md">
                            <span v-if="!isConnecting">
                                <svg class="w-5 h-5 inline mr-1" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z"/>
                                </svg>
                                Connect Instagram
                            </span>
                            <span v-else class="flex items-center gap-2">
                                <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Opening Facebook...
                            </span>
                        </button>

                        <p class="mt-2 text-xs text-gray-500 text-center">
                            You'll be redirected to Facebook to authorize Instagram access
                        </p>
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
                            <h3 class="text-lg font-medium text-gray-900">Disconnect Instagram</h3>
                            <p class="mt-2 text-sm text-gray-500">
                                Are you sure you want to disconnect your Instagram account? You won't be able to publish posts until you reconnect.
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
            showDisconnectModal: false,
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
                await this.checkOAuthStatus();
                await this.loadConnection();
                this.handleOAuthCallback();
                window.addEventListener('message', this.handleOAuthMessage);
            } catch (error) {
                console.error('Initialization error:', error);
                this.setError('Initialization Failed', 'Failed to initialize Instagram connection. Please refresh the page.');
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
            } catch (error) {
                console.error('Error checking OAuth status:', error);
                this.isConfigured = error.response?.status !== 404;
            }
        },

        async loadConnection() {
            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                const instagramConnection = response.data.find(conn => conn.platform === 'instagram');

                if (instagramConnection && instagramConnection.is_active) {
                    this.connection = {
                        connected: true,
                        username: instagramConnection.platform_username,
                        display_name: instagramConnection.metadata?.name || instagramConnection.platform_username,
                        profile_picture: instagramConnection.metadata?.profile_picture_url || null,
                        connected_at: instagramConnection.created_at,
                        posts_count: 0
                    };
                }
            } catch (error) {
                console.error('Error loading connection:', error);
            }
        },

        async initiateConnection() {
            if (this.isConnecting || !this.isConfigured) return;

            this.isConnecting = true;
            this.clearMessages();

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';
                const returnUrl = encodeURIComponent(window.location.href);

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                if (response.data.oauth_url) {
                    this.openOAuthPopup(response.data.oauth_url);
                } else {
                    throw new Error('No authorization URL received');
                }
            } catch (error) {
                console.error('Error initiating Instagram connection:', error);
                this.isConnecting = false;
                this.handleConnectionError(error);
            }
        },

        handleConnectionError(error) {
            const status = error.response?.status;
            const detail = error.response?.data?.detail;

            if (status === 503) {
                this.setError('Instagram OAuth Not Configured', 'Instagram OAuth is not configured on this server. Contact your administrator.');
            } else if (status === 401) {
                this.setError('Invalid Credentials', 'The Instagram/Facebook API credentials configured on this server are invalid.');
            } else if (status === 429) {
                this.setError('Rate Limit Exceeded', 'Too many connection attempts. Please wait a few minutes and try again.');
            } else if (detail) {
                this.setError('Connection Failed', detail);
            } else {
                this.setError('Connection Failed', 'Failed to connect to Instagram. Please try again.');
            }
        },

        openOAuthPopup(url) {
            const width = 600;
            const height = 700;
            const left = (window.screen.width / 2) - (width / 2);
            const top = (window.screen.height / 2) - (height / 2);

            this.oauthWindow = window.open(
                url,
                'instagram_oauth',
                `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
            );

            if (!this.oauthWindow || this.oauthWindow.closed || typeof this.oauthWindow.closed === 'undefined') {
                this.isConnecting = false;
                this.setError('Popup Blocked', 'The OAuth popup was blocked by your browser. Please allow popups for this website.');
                return;
            }

            if (this.oauthWindow.focus) {
                this.oauthWindow.focus();
            }

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

                    setTimeout(() => {
                        this.checkOAuthCallback();
                    }, 1000);
                }
            }, 500);

            setTimeout(() => {
                if (this.oauthCheckInterval) {
                    clearInterval(this.oauthCheckInterval);
                    this.oauthCheckInterval = null;

                    if (this.oauthWindow && !this.oauthWindow.closed) {
                        this.oauthWindow.close();
                    }

                    this.isConnecting = false;
                    this.setError('Authorization Timeout', 'The authorization process timed out. Please try again.');
                }
            }, 300000);
        },

        handleOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const instagram = urlParams.get('instagram');
            const username = urlParams.get('username');

            if (instagram === 'connected') {
                this.isConnecting = false;
                this.successMessage = `Successfully connected your Instagram account${username ? ' (@' + username + ')' : ''}!`;
                this.loadConnection();

                if (this.oauthWindow && !this.oauthWindow.closed) {
                    this.oauthWindow.close();
                }

                window.history.replaceState({}, document.title, window.location.pathname);
            } else if (instagram === 'error') {
                this.isConnecting = false;
                this.setError('Connection Failed', 'Failed to connect Instagram account. Please try again.');
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        },

        handleOAuthMessage(event) {
            if (event.origin !== window.location.origin) return;

            const { type, platform, success, username } = event.data;

            if (type === 'instagram_oauth_complete' && platform === 'instagram') {
                this.isConnecting = false;

                if (success) {
                    this.successMessage = `Successfully connected your Instagram account${username ? ' (@' + username + ')' : ''}!`;
                    this.loadConnection();
                } else {
                    this.setError('Connection Failed', 'Failed to connect Instagram account.');
                }

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

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                if (response.data.connected) {
                    this.successMessage = 'Instagram connection is working correctly!';
                } else {
                    throw new Error('Connection test failed');
                }
            } catch (error) {
                console.error('Error testing connection:', error);
                this.setError('Connection Test Failed', 'Unable to verify your Instagram connection. Try disconnecting and reconnecting.');
            } finally {
                this.testing = false;

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

                await axios.delete("/api/user/twitter", {
                withCredentials: true
            });

                this.connection = {
                    connected: false,
                    username: null,
                    display_name: null,
                    profile_picture: null,
                    connected_at: null,
                    posts_count: 0
                };

                this.successMessage = 'Successfully disconnected your Instagram account.';
                this.showDisconnectModal = false;
            } catch (error) {
                console.error('Error disconnecting Instagram:', error);
                this.setError('Disconnect Failed', error.response?.data?.detail || 'Failed to disconnect. Please try again.');
            } finally {
                this.disconnecting = false;
            }
        },

        setError(title, message) {
            this.errorTitle = title;
            this.errorMessage = message;
        },

        clearMessages() {
            this.successMessage = '';
            this.errorMessage = '';
            this.errorTitle = '';
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
            if (!this.connection.connected && this.isConnecting) {
                this.isConnecting = false;
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

// Register component globally if Vue is available
if (typeof window !== 'undefined' && window.Vue) {
    const app = window.Vue.createApp({});
    app.component('instagram-oauth-connect', InstagramOAuthConnect);
}
