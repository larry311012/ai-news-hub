// OAuth Credentials Manager Component
// Simplified version for Profile page integration
const OAuthCredentialsManager = {
    name: 'OAuthCredentialsManager',
    template: `
        <div class="space-y-6">
            <!-- Loading State -->
            <div v-if="loading" class="flex justify-center items-center py-8">
                <svg class="animate-spin h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            </div>

            <div v-else>
                <!-- Platform Status Overview -->
                <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 mb-4">
                    <div class="flex items-center justify-between">
                        <span class="text-sm font-medium text-gray-700">Configured Platforms: {{ configuredCount }} of 3</span>
                        <div class="flex gap-4">
                            <div v-for="platform in platforms" :key="platform.id" class="flex items-center gap-1">
                                <div :class="platform.configured ? 'text-green-600' : 'text-gray-300'" class="text-lg">
                                    {{ platform.configured ? '✓' : '○' }}
                                </div>
                                <span class="text-xs text-gray-600">{{ platform.name }}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Success/Error Messages -->
                <div v-if="successMessage" class="bg-green-50 border border-green-200 rounded-md p-3 flex items-start" role="alert">
                    <svg class="h-5 w-5 text-green-400 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    <p class="text-sm text-green-800">{{ successMessage }}</p>
                </div>

                <div v-if="errorMessage" class="bg-red-50 border border-red-200 rounded-md p-3 flex items-start" role="alert">
                    <svg class="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                    </svg>
                    <p class="text-sm text-red-800">{{ errorMessage }}</p>
                </div>

                <!-- Platform Configuration Cards -->
                <div class="space-y-4">
                    <div v-for="platform in platforms" :key="platform.id" class="bg-gray-50 rounded-lg border border-gray-200">
                        <!-- Card Header -->
                        <div class="p-4 flex items-center justify-between cursor-pointer" @click="togglePlatform(platform.id)">
                            <div class="flex items-center gap-3">
                                <div :class="[
                                    'w-10 h-10 rounded-lg flex items-center justify-center',
                                    platform.configured ? platform.activeBg : 'bg-gray-200'
                                ]">
                                    <svg :class="[
                                        'w-5 h-5',
                                        platform.configured ? 'text-white' : 'text-gray-600'
                                    ]" fill="currentColor" viewBox="0 0 24 24" v-html="platform.icon">
                                    </svg>
                                </div>
                                <div>
                                    <h4 class="text-sm font-medium text-gray-900">{{ platform.name }}</h4>
                                    <p class="text-xs text-gray-500">{{ platform.description }}</p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <span v-if="platform.configured" class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                    <span class="h-1.5 w-1.5 rounded-full bg-green-400 mr-1"></span>
                                    Active
                                </span>
                                <span v-else class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                    Not Configured
                                </span>
                                <svg class="w-5 h-5 text-gray-400 transition-transform" :class="{ 'rotate-180': expandedPlatform === platform.id }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>
                        </div>

                        <!-- Card Body (Expandable) -->
                        <div v-if="expandedPlatform === platform.id" class="px-4 pb-4 border-t border-gray-200 pt-4">
                            <form @submit.prevent="savePlatform(platform.id)" class="space-y-4">
                                <!-- OAuth Version Info -->
                                <div class="bg-blue-50 border border-blue-200 rounded-md p-3">
                                    <p class="text-xs text-blue-800">
                                        <strong>OAuth {{ platform.oauthVersion }}</strong> - {{ platform.oauthInfo }}
                                    </p>
                                </div>

                                <!-- Platform-specific Fields -->
                                <div v-for="field in platform.fields" :key="field.key" class="space-y-1">
                                    <label class="block text-sm font-medium text-gray-700">
                                        {{ field.label }}
                                        <span v-if="field.required" class="text-red-500">*</span>
                                    </label>
                                    <input
                                        v-model="platform.formData[field.key]"
                                        :type="field.type || 'text'"
                                        :required="field.required"
                                        :placeholder="field.placeholder"
                                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono">
                                    <p v-if="field.help" class="text-xs text-gray-500">{{ field.help }}</p>
                                </div>

                                <!-- Actions -->
                                <div class="flex space-x-3 pt-2">
                                    <button type="submit"
                                            :disabled="saving[platform.id]"
                                            class="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                        <span v-if="!saving[platform.id]">{{ platform.configured ? 'Update Credentials' : 'Save Credentials' }}</span>
                                        <span v-else class="flex items-center">
                                            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Saving...
                                        </span>
                                    </button>

                                    <button v-if="platform.configured"
                                            type="button"
                                            @click="testConnection(platform.id)"
                                            :disabled="testing[platform.id]"
                                            class="px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm">
                                        <span v-if="!testing[platform.id]">Test Connection</span>
                                        <span v-else>Testing...</span>
                                    </button>

                                    <button v-if="platform.configured"
                                            type="button"
                                            @click="confirmDelete(platform.id)"
                                            class="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 font-medium transition-colors text-sm">
                                        Delete
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>

                <!-- Help Section -->
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div class="flex">
                        <svg class="h-5 w-5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-blue-800">How to get OAuth credentials</h3>
                            <div class="mt-2 text-xs text-blue-700 space-y-1">
                                <p>• <strong>Twitter:</strong> Visit developer.twitter.com and create an app</p>
                                <p>• <strong>LinkedIn:</strong> Visit linkedin.com/developers and create an OAuth app</p>
                                <p>• <strong>Threads:</strong> Visit developers.facebook.com and set up Threads API</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Delete Confirmation Modal -->
            <div v-if="showDeleteModal" class="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50" @click.self="showDeleteModal = false">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                    <div class="flex items-start">
                        <div class="flex-shrink-0">
                            <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <div class="ml-3 flex-1">
                            <h3 class="text-lg font-medium text-gray-900">Delete OAuth Credentials</h3>
                            <p class="mt-2 text-sm text-gray-500">
                                Are you sure you want to delete the {{ platformToDelete ? getPlatformName(platformToDelete) : '' }} OAuth credentials? This action cannot be undone.
                            </p>
                            <div class="mt-4 flex space-x-3">
                                <button @click="deletePlatform"
                                        :disabled="deleting"
                                        class="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium disabled:opacity-50 transition-colors">
                                    {{ deleting ? 'Deleting...' : 'Delete' }}
                                </button>
                                <button @click="showDeleteModal = false"
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
            expandedPlatform: null,
            successMessage: '',
            errorMessage: '',
            saving: {},
            testing: {},
            deleting: false,
            showDeleteModal: false,
            platformToDelete: null,
            platforms: [
                {
                    id: 'twitter',
                    name: 'Twitter/X',
                    description: 'OAuth 1.0a - Centralized authentication for all users',
                    oauthVersion: '1.0a',
                    oauthInfo: 'Requires API Key (Consumer Key), API Secret (Consumer Secret), and Callback URL',
                    icon: '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>',
                    activeBg: 'bg-black',
                    configured: false,
                    fields: [
                        { key: 'api_key', label: 'API Key (Consumer Key)', required: true, placeholder: 'Enter your Twitter API Key' },
                        { key: 'api_secret', label: 'API Secret (Consumer Secret)', required: true, type: 'password', placeholder: 'Enter your Twitter API Secret' },
                        { key: 'callback_url', label: 'Callback URL', required: true, placeholder: 'http://localhost:8000/api/social-media/twitter-oauth1/callback', help: 'Must match the URL configured in Twitter Developer Portal' }
                    ],
                    formData: {
                        api_key: '',
                        api_secret: '',
                        callback_url: 'http://localhost:8000/api/social-media/twitter-oauth1/callback'
                    }
                },
                {
                    id: 'linkedin',
                    name: 'LinkedIn',
                    description: 'OAuth 2.0 - Share professional updates',
                    oauthVersion: '2.0',
                    oauthInfo: 'Requires Client ID, Client Secret, and Access Token',
                    icon: '<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>',
                    activeBg: 'bg-blue-600',
                    configured: false,
                    fields: [
                        { key: 'client_id', label: 'Client ID', required: true, placeholder: 'Enter your LinkedIn Client ID' },
                        { key: 'client_secret', label: 'Client Secret', required: true, type: 'password', placeholder: 'Enter your LinkedIn Client Secret' },
                        { key: 'access_token', label: 'Access Token', required: true, placeholder: 'Enter your LinkedIn Access Token' }
                    ],
                    formData: {
                        client_id: '',
                        client_secret: '',
                        access_token: ''
                    }
                },
                {
                    id: 'threads',
                    name: 'Threads',
                    description: 'OAuth 2.0 - Post to Meta\'s text platform',
                    oauthVersion: '2.0',
                    oauthInfo: 'Requires User ID and Access Token',
                    icon: '<path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.704-1.488 0-2.743-.546-3.625-1.577a5.688 5.688 0 0 1-1.081-2.174c-.288-.901-.438-1.886-.438-2.936 0-1.043.156-2.03.465-2.935.29-.852.703-1.613 1.226-2.26.924-1.132 2.141-1.706 3.614-1.706 1.493 0 2.718.573 3.644 1.705.488.598.853 1.326 1.086 2.167l1.01-.548c-.34-.876-.82-1.647-1.429-2.29-1.17-1.238-2.707-1.914-4.562-2.009-.025-.02-.05-.041-.075-.06l-.023-.023c-.878-.834-1.898-1.255-3.034-1.255-1.137 0-2.156.423-3.032 1.258-.866.826-1.313 1.904-1.313 3.203v.989c.032 2.015.827 3.51 2.37 4.45.916.56 1.996.844 3.208.844 1.208 0 2.283-.285 3.197-.845.492-.3.948-.69 1.358-1.163.37-.429.676-.92.91-1.465l.022.012c.01.005.018.012.028.018.464.315.84.693 1.117 1.122.397.614.617 1.34.654 2.157.023.485.012.97-.031 1.452-.095 1.032-.38 1.977-.849 2.813-.698 1.244-1.784 2.202-3.23 2.85-.967.43-2.07.65-3.275.65h-.001z"/>',
                    activeBg: 'bg-black',
                    configured: false,
                    fields: [
                        { key: 'user_id', label: 'User ID', required: true, placeholder: 'Enter your Threads User ID' },
                        { key: 'access_token', label: 'Access Token', required: true, placeholder: 'Enter your Threads Access Token' }
                    ],
                    formData: {
                        user_id: '',
                        access_token: ''
                    }
                }
            ]
        };
    },
    computed: {
        configuredCount() {
            return this.platforms.filter(p => p.configured).length;
        }
    },
    mounted() {
        this.loadConfigurations();
    },
    methods: {
        async loadConfigurations() {
            this.loading = true;
            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Load each platform's configuration
                for (const platform of this.platforms) {
                    try {
                        const response = await axios.get(`${API_BASE_URL}/api/admin/oauth-credentials/${platform.id}`, {
                            withCredentials: true
                        });

                        if (response.data && response.data.platform === platform.id) {
                            platform.configured = true;
                            // Don't populate form with existing data for security
                        }
                    } catch (error) {
                        // Platform not configured - this is expected
                        if (error.response && error.response.status !== 404) {
                            console.error(`Error loading ${platform.id}:`, error);
                        }
                    }
                }
            } catch (error) {
                console.error('Error loading configurations:', error);
                this.handleError(error, 'Failed to load OAuth configurations');
            } finally {
                this.loading = false;
            }
        },

        togglePlatform(platformId) {
            this.expandedPlatform = this.expandedPlatform === platformId ? null : platformId;
            this.successMessage = '';
            this.errorMessage = '';
        },

        async savePlatform(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            if (!platform) return;

            this.saving[platformId] = true;
            this.successMessage = '';
            this.errorMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Prepare payload with oauth_version
                const payload = {
                    ...platform.formData,
                    oauth_version: platform.oauthVersion,
                    is_active: true
                };

                await axios.post(`${API_BASE_URL}/api/admin/oauth-credentials/${platform.id}`, payload, {
                    withCredentials: true
                });

                platform.configured = true;
                this.successMessage = `${platform.name} credentials saved successfully!`;

                // Clear sensitive form fields for security
                Object.keys(platform.formData).forEach(key => {
                    if (key.includes('secret') || key.includes('key')) {
                        platform.formData[key] = '';
                    }
                });

                // Collapse the card after save
                setTimeout(() => {
                    this.expandedPlatform = null;
                }, 1500);

            } catch (error) {
                console.error(`Error saving ${platformId}:`, error);
                this.handleError(error, `Failed to save ${platform.name} credentials`);
            } finally {
                this.saving[platformId] = false;
            }
        },

        async testConnection(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            if (!platform) return;

            this.testing[platformId] = true;
            this.successMessage = '';
            this.errorMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await axios.post(`${API_BASE_URL}/api/admin/oauth-credentials/${platform.id}/test`, {}, {
                    withCredentials: true
                });

                if (response.data.success || response.data.valid || response.status === 200) {
                    this.successMessage = `${platform.name} connection test successful!`;
                } else {
                    this.errorMessage = response.data.message || `${platform.name} connection test failed`;
                }

            } catch (error) {
                console.error(`Error testing ${platformId}:`, error);
                this.handleError(error, `Failed to test ${platform.name} connection`);
            } finally {
                this.testing[platformId] = false;
            }
        },

        confirmDelete(platformId) {
            this.platformToDelete = platformId;
            this.showDeleteModal = true;
        },

        async deletePlatform() {
            if (!this.platformToDelete) return;

            const platform = this.platforms.find(p => p.id === this.platformToDelete);
            this.deleting = true;

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                await axios.delete(`${API_BASE_URL}/api/admin/oauth-credentials/${platform.id}`, {
                    withCredentials: true
                });

                platform.configured = false;
                this.successMessage = `${platform.name} credentials deleted successfully`;
                this.showDeleteModal = false;
                this.platformToDelete = null;

            } catch (error) {
                console.error(`Error deleting ${this.platformToDelete}:`, error);
                this.handleError(error, `Failed to delete ${platform.name} credentials`);
            } finally {
                this.deleting = false;
            }
        },

        getPlatformName(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            return platform ? platform.name : platformId;
        },

        handleError(error, defaultMessage) {
            if (error.response) {
                const status = error.response.status;
                const detail = error.response.data?.detail || error.response.data?.message;

                if (status === 401) {
                    this.errorMessage = 'Session expired. Please login again.';
                    setTimeout(() => {
                        window.location.href = 'auth.html';
                    }, 2000);
                } else if (status === 403) {
                    this.errorMessage = 'You don\'t have permission to manage OAuth credentials.';
                } else {
                    this.errorMessage = detail || defaultMessage;
                }
            } else if (error.request) {
                this.errorMessage = 'Cannot connect to server. Please check if the backend is running.';
            } else {
                this.errorMessage = defaultMessage;
            }

            // Auto-clear error after 5 seconds
            setTimeout(() => {
                this.errorMessage = '';
            }, 5000);
        }
    }
};

// Export as ES6 module default export
export default OAuthCredentialsManager;
