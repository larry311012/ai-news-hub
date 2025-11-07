/**
 * Threads OAuth Connection Component
 *
 * Complete frontend implementation for Threads (Meta) OAuth authentication flow
 * with comprehensive error handling, credential validation, and user guidance.
 *
 * Features:
 * - Seamless OAuth popup flow
 * - Detailed error messages with actionable guidance
 * - Connection status and token expiry tracking
 * - Profile display with username and stats
 * - Test connection functionality
 * - Visual feedback for all states
 *
 * Usage in profile.html:
 * <threads-oauth-connect></threads-oauth-connect>
 */

import axios from 'axios';

const ThreadsOAuthConnect = {
    name: 'ThreadsOAuthConnect',
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

                            <!-- Link to Meta Developers if needed -->
                            <div v-if="showDevPortalLink" class="mt-3">
                                <a href="https://developers.facebook.com/apps"
                                   target="_blank"
                                   class="inline-flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-md hover:from-purple-700 hover:to-pink-700 transition-colors text-xs font-medium">
                                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.781 3.631 2.695 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 013.02.142l-.126 1.974a11.881 11.881 0 00-2.58-.123c-1.018.056-1.84.344-2.446.855-.583.493-.87 1.12-.834 1.814.036.683.388 1.217.99 1.502.539.255 1.277.354 2.101.28 1.15-.093 2.059-.535 2.702-1.315.646-.784.972-1.858.972-3.197V8.033c0-.458-.006-.916-.02-1.373l2.04-.057c.013.457.02.915.02 1.373v1.78c.598-.421 1.3-.758 2.092-.998 1.004-.304 2.085-.457 3.212-.457l.126 1.99c-.905 0-1.766.123-2.562.366-.796.243-1.47.6-2.004 1.062v1.304c.54.694.97 1.49 1.28 2.369.726 2.057.746 4.753-1.44 6.993-1.817 1.869-4.138 2.82-7.106 2.848z"/>
                                    </svg>
                                    Open Meta Developers Portal
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                    </svg>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Token Expiry Warning -->
                <div v-if="connection.connected && tokenExpiryWarning" class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                    <div class="flex items-start">
                        <svg class="h-5 w-5 text-yellow-400 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                        </svg>
                        <div class="flex-1">
                            <p class="text-sm font-medium text-yellow-900">Access token expiring soon</p>
                            <p class="text-xs text-yellow-700 mt-1">Your Threads connection expires {{ tokenExpiryText }}. Please reconnect to continue publishing.</p>
                            <button @click="refreshToken"
                                    :disabled="refreshing"
                                    class="mt-2 inline-flex items-center px-3 py-1 bg-yellow-600 text-white text-xs font-medium rounded hover:bg-yellow-700 disabled:opacity-50">
                                {{ refreshing ? 'Refreshing...' : 'Refresh Token Now' }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Threads Connection Card -->
                <div class="bg-gray-50 rounded-lg border border-gray-200 overflow-hidden">
                    <!-- Card Header -->
                    <div class="p-4 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <!-- Threads Icon -->
                            <div :class="[
                                'w-12 h-12 rounded-lg flex items-center justify-center',
                                connection.connected ? 'bg-gradient-to-br from-purple-600 to-pink-600' : 'bg-gray-200'
                            ]">
                                <svg :class="[
                                    'w-6 h-6',
                                    connection.connected ? 'text-white' : 'text-gray-600'
                                ]" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.781 3.631 2.695 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 013.02.142l-.126 1.974a11.881 11.881 0 00-2.58-.123c-1.018.056-1.84.344-2.446.855-.583.493-.87 1.12-.834 1.814.036.683.388 1.217.99 1.502.539.255 1.277.354 2.101.28 1.15-.093 2.059-.535 2.702-1.315.646-.784.972-1.858.972-3.197V8.033c0-.458-.006-.916-.02-1.373l2.04-.057c.013.457.02.915.02 1.373v1.78c.598-.421 1.3-.758 2.092-.998 1.004-.304 2.085-.457 3.212-.457l.126 1.99c-.905 0-1.766.123-2.562.366-.796.243-1.47.6-2.004 1.062v1.304c.54.694.97 1.49 1.28 2.369.726 2.057.746 4.753-1.44 6.993-1.817 1.869-4.138 2.82-7.106 2.848z"/>
                                </svg>
                            </div>

                            <div>
                                <h4 class="text-sm font-medium text-gray-900">Threads (Meta)</h4>
                                <p class="text-xs text-gray-500">Share posts on Threads automatically</p>
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
                                <div v-else class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center text-white font-bold text-sm">
                                    {{ connection.username ? connection.username[0].toUpperCase() : 'T' }}
                                </div>
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
                                    <p class="text-xs text-gray-500">Token Expires</p>
                                    <p class="text-sm font-semibold" :class="tokenExpiryWarning ? 'text-yellow-600' : 'text-gray-900'">
                                        {{ formatDate(connection.token_expires_at) }}
                                    </p>
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
                        <!-- Connect Button -->
                        <button @click="initiateConnection"
                                :disabled="isConnecting || !isConfigured"
                                class="w-full px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-md hover:from-purple-700 hover:to-pink-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm flex items-center justify-center gap-2">
                            <span v-if="!isConnecting">
                                <svg class="w-5 h-5 inline mr-1" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.781 3.631 2.695 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 013.02.142l-.126 1.974a11.881 11.881 0 00-2.58-.123c-1.018.056-1.84.344-2.446.855-.583.493-.87 1.12-.834 1.814.036.683.388 1.217.99 1.502.539.255 1.277.354 2.101.28 1.15-.093 2.059-.535 2.702-1.315.646-.784.972-1.858.972-3.197V8.033c0-.458-.006-.916-.02-1.373l2.04-.057c.013.457.02.915.02 1.373v1.78c.598-.421 1.3-.758 2.092-.998 1.004-.304 2.085-.457 3.212-.457l.126 1.99c-.905 0-1.766.123-2.562.366-.796.243-1.47.6-2.004 1.062v1.304c.54.694.97 1.49 1.28 2.369.726 2.057.746 4.753-1.44 6.993-1.817 1.869-4.138 2.82-7.106 2.848z"/>
                                </svg>
                                Connect Threads Account
                            </span>
                            <span v-else class="flex items-center gap-2">
                                <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Opening Threads...
                            </span>
                        </button>

                        <p class="mt-2 text-xs text-gray-500 text-center">
                            You'll be redirected to Meta to authorize this application
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
                            <h3 class="text-lg font-medium text-gray-900">Disconnect Threads Account</h3>
                            <p class="mt-2 text-sm text-gray-500">
                                Are you sure you want to disconnect your Threads account? You won't be able to publish to Threads until you reconnect.
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
            refreshing: false,
            connection: {
                connected: false,
                username: null,
                display_name: null,
                profile_picture: null,
                connected_at: null,
                token_expires_at: null,
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
    computed: {
        tokenExpiryWarning() {
            if (!this.connection.token_expires_at) return false;

            const expiryDate = new Date(this.connection.token_expires_at);
            const now = new Date();
            const daysUntilExpiry = Math.floor((expiryDate - now) / (1000 * 60 * 60 * 24));

            return daysUntilExpiry <= 7; // Warn if expiring within 7 days
        },
        tokenExpiryText() {
            if (!this.connection.token_expires_at) return 'soon';

            const expiryDate = new Date(this.connection.token_expires_at);
            const now = new Date();
            const daysUntilExpiry = Math.floor((expiryDate - now) / (1000 * 60 * 60 * 24));

            if (daysUntilExpiry < 0) return 'expired';
            if (daysUntilExpiry === 0) return 'today';
            if (daysUntilExpiry === 1) return 'tomorrow';
            return `in ${daysUntilExpiry} days`;
        }
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
                // Check Threads OAuth configuration status
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
                    'Failed to initialize Threads connection. Please refresh the page.',
                    ['Refresh the page', 'Check your internet connection']
                );
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
                    console.warn('Threads OAuth is not configured on the server');
                }
            } catch (error) {
                console.error('Error checking Threads OAuth status:', error);
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

                // Find Threads connection
                const threadsConnection = response.data.find(conn => conn.platform === 'threads');

                if (threadsConnection && threadsConnection.is_active) {
                    this.connection = {
                        connected: true,
                        username: threadsConnection.platform_username,
                        display_name: threadsConnection.metadata?.name || threadsConnection.platform_username,
                        profile_picture: threadsConnection.metadata?.profile_picture_url || null,
                        connected_at: threadsConnection.created_at,
                        token_expires_at: threadsConnection.metadata?.expires_at || null,
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

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                if (response.data.authorization_url) {
                    // Open OAuth popup
                    this.openOAuthPopup(response.data.authorization_url);
                } else {
                    throw new Error('No authorization URL received');
                }
            } catch (error) {
                console.error('Error initiating Threads connection:', error);
                this.isConnecting = false;
                this.handleConnectionError(error);
            }
        },

        handleConnectionError(error) {
            const status = error.response?.status;
            const detail = error.response?.data?.detail;

            if (status === 503) {
                this.setError(
                    'Threads API Not Configured',
                    'Threads integration is not configured on this server.',
                    [
                        'Contact your system administrator',
                        'The admin needs to set THREADS_APP_ID and THREADS_APP_SECRET',
                        'Redirect URI must be configured in Meta app settings',
                        'After configuration, restart the server'
                    ],
                    true
                );
            } else if (status === 401) {
                this.setError(
                    'Invalid Threads Credentials',
                    'The Threads API credentials configured on this server are invalid.',
                    [
                        'Contact your system administrator',
                        'Verify the App ID and App Secret in Meta Developers Portal',
                        'Check that the app has Threads permissions enabled'
                    ],
                    true
                );
            } else if (status === 429) {
                this.setError(
                    'Rate Limit Exceeded',
                    'Too many connection attempts. Please wait and try again.',
                    [
                        'Wait 5-10 minutes before trying again',
                        'If this persists, contact support'
                    ]
                );
            } else if (detail) {
                this.setError(
                    'Connection Failed',
                    detail,
                    ['Try again in a few moments', 'If this persists, contact support']
                );
            } else if (error.message === 'Network Error') {
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
                this.setError(
                    'Connection Failed',
                    'Failed to connect to Threads. Please try again.',
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
                'threads_oauth',
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
                        if (this.isConnecting) {
                            this.isConnecting = false;
                        }
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
                            'Make sure to authorize the app on Threads within 5 minutes'
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

            if (platform === 'threads') {
                this.isConnecting = false;

                if (success === 'true') {
                    this.successMessage = `Successfully connected your Threads account${username ? ' (@' + username + ')' : ''}!`;
                    this.loadConnection();

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
                    'You cancelled the Threads authorization.',
                    [
                        'Click "Connect Threads Account" to try again',
                        'You must authorize the app to connect your Threads account'
                    ]
                );
            } else if (error === 'oauth_failed') {
                this.setError(
                    'Authorization Failed',
                    'Threads authorization failed. This may be due to invalid server credentials.',
                    [
                        'Contact your system administrator',
                        'The Threads API credentials may need to be updated',
                        'Try again in a few moments'
                    ],
                    true
                );
            } else {
                this.setError(
                    'Connection Failed',
                    'Failed to connect Threads account.',
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

            if (type === 'threads-oauth-success' && platform === 'threads') {
                this.isConnecting = false;
                this.successMessage = `Successfully connected your Threads account${username ? ' (@' + username + ')' : ''}!`;
                this.loadConnection();

                if (this.oauthWindow && !this.oauthWindow.closed) {
                    this.oauthWindow.close();
                }
            } else if (type === 'threads-oauth-error') {
                this.isConnecting = false;
                this.handleCallbackError(error);

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

                const threadsConnection = response.data.find(conn => conn.platform === 'threads');

                if (threadsConnection && threadsConnection.is_active) {
                    this.successMessage = 'Threads connection is working correctly!';
                } else {
                    throw new Error('Connection test failed');
                }
            } catch (error) {
                console.error('Error testing connection:', error);
                this.setError(
                    'Connection Test Failed',
                    'Unable to verify your Threads connection.',
                    [
                        'Try disconnecting and reconnecting your account',
                        'Contact support if the problem persists'
                    ]
                );
            } finally {
                this.testing = false;

                if (this.successMessage) {
                    setTimeout(() => {
                        this.successMessage = '';
                    }, 5000);
                }
            }
        },

        async refreshToken() {
            this.refreshing = true;
            this.clearMessages();

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                await axios.post("/api/user/twitter", {
                withCredentials: true
            });

                this.successMessage = 'Access token refreshed successfully!';
                await this.loadConnection();
            } catch (error) {
                console.error('Error refreshing token:', error);
                this.setError(
                    'Token Refresh Failed',
                    'Failed to refresh your Threads access token. You may need to reconnect.',
                    [
                        'Try disconnecting and reconnecting your account',
                        'Make sure your Threads account is still accessible'
                    ]
                );
            } finally {
                this.refreshing = false;
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
                    token_expires_at: null,
                    posts_count: 0
                };

                this.successMessage = 'Successfully disconnected your Threads account.';
                this.showDisconnectModal = false;
            } catch (error) {
                console.error('Error disconnecting Threads:', error);
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
    app.component('threads-oauth-connect', ThreadsOAuthConnect);
}


export default ThreadsOAuthConnect;
