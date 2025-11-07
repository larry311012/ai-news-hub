// API Key Manager Component
const ApiKeyManager = {
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
                <!-- AI Provider Selection -->
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-3">Select AI Provider</label>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <button v-for="provider in providers"
                                :key="provider.id"
                                @click="selectProvider(provider.id)"
                                :class="selectedProvider === provider.id ? 'ring-2 ring-indigo-500 border-indigo-500' : 'border-gray-200 hover:border-gray-300'"
                                class="relative flex items-center p-4 border rounded-lg transition-all cursor-pointer group">
                            <div class="flex-shrink-0">
                                <div class="h-10 w-10 rounded-lg flex items-center justify-center"
                                     :class="provider.bgColor">
                                    <span class="text-lg font-bold" :class="provider.textColor">{{ provider.icon }}</span>
                                </div>
                            </div>
                            <div class="ml-4 flex-1 text-left">
                                <p class="text-sm font-medium text-gray-900">{{ provider.name }}</p>
                                <p class="text-xs text-gray-500">{{ provider.description }}</p>
                            </div>
                            <div v-if="apiKeys[provider.id]"
                                 class="absolute top-2 right-2">
                                <div class="h-2 w-2 rounded-full bg-green-500"></div>
                            </div>
                        </button>
                    </div>
                </div>

                <!-- API Key Form -->
                <div v-if="selectedProvider" class="bg-gray-50 rounded-lg p-6 border border-gray-200">
                    <div class="flex items-center justify-between mb-4">
                        <h4 class="text-sm font-medium text-gray-900">
                            {{ getProviderName(selectedProvider) }} API Key
                        </h4>
                        <div v-if="apiKeys[selectedProvider]" class="flex items-center text-xs text-green-600">
                            <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                            </svg>
                            Key Configured
                        </div>
                    </div>

                    <form @submit.prevent="saveApiKey" class="space-y-4">
                        <!-- API Key Input -->
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">
                                API Key
                            </label>
                            <div class="relative">
                                <input v-model="apiKeyForm.key"
                                       :type="showKey ? 'text' : 'password'"
                                       :placeholder="getPlaceholder(selectedProvider)"
                                       required
                                       class="w-full px-3 py-2 pr-20 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm">
                                <div class="absolute inset-y-0 right-0 flex items-center pr-3 space-x-2">
                                    <button type="button"
                                            @click="showKey = !showKey"
                                            class="text-gray-400 hover:text-gray-600 transition-colors"
                                            :aria-label="showKey ? 'Hide API key' : 'Show API key'">
                                        <svg v-if="showKey" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                        </svg>
                                        <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            <!-- Format Hints -->
                            <div class="mt-2 bg-blue-50 border border-blue-200 rounded-md p-3">
                                <div class="flex">
                                    <svg class="h-5 w-5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                                    </svg>
                                    <div class="ml-3">
                                        <p class="text-xs font-medium text-blue-800">Required Format:</p>
                                        <div class="mt-1 text-xs text-blue-700">
                                            <div v-if="selectedProvider === 'openai'">
                                                <p class="font-mono">✓ sk-proj-abc123def456...</p>
                                                <p class="font-mono">✓ sk-abc123def456...</p>
                                                <p class="text-red-600 font-mono mt-1">✗ k-abc123... (missing 's')</p>
                                            </div>
                                            <div v-if="selectedProvider === 'anthropic'">
                                                <p class="font-mono">✓ sk-ant-abc123def456...</p>
                                                <p class="text-red-600 font-mono mt-1">✗ k-ant-abc123... (missing 's')</p>
                                                <p class="text-red-600 font-mono">✗ sk-abc123... (use OpenAI provider)</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="mt-2 flex items-start">
                                <svg class="h-4 w-4 text-green-500 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                </svg>
                                <p class="text-xs text-gray-500">
                                    Your API key is encrypted with AES-256 before being stored. It is never logged or transmitted in plain text.
                                </p>
                            </div>
                        </div>

                        <!-- Key Name (Optional) -->
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">
                                Key Name (Optional)
                            </label>
                            <input v-model="apiKeyForm.name"
                                   type="text"
                                   placeholder="e.g., Production Key"
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
                        </div>

                        <!-- Success Message -->
                        <div v-if="successMessage" class="bg-green-50 border border-green-200 rounded-md p-3 flex items-start" role="alert">
                            <svg class="h-5 w-5 text-green-400 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                            </svg>
                            <p class="text-sm text-green-800">{{ successMessage }}</p>
                        </div>

                        <!-- Error Message (Enhanced for multi-line) -->
                        <div v-if="errorMessage" class="bg-red-50 border border-red-200 rounded-md p-3 flex items-start" role="alert">
                            <svg class="h-5 w-5 text-red-400 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                            </svg>
                            <p class="text-sm text-red-800 whitespace-pre-line">{{ errorMessage }}</p>
                        </div>

                        <!-- Actions -->
                        <div class="flex space-x-3 pt-2">
                            <button type="submit"
                                    :disabled="saving"
                                    class="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                <span v-if="!saving">{{ apiKeys[selectedProvider] ? 'Update Key' : 'Save Key' }}</span>
                                <span v-else class="flex items-center">
                                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Saving...
                                </span>
                            </button>

                            <button v-if="apiKeys[selectedProvider]"
                                    type="button"
                                    @click="testApiKey"
                                    :disabled="testing"
                                    class="px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                <span v-if="!testing">Test Key</span>
                                <span v-else class="flex items-center">
                                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Testing...
                                </span>
                            </button>

                            <button v-if="apiKeys[selectedProvider]"
                                    type="button"
                                    @click="confirmDeleteApiKey"
                                    :disabled="deleting"
                                    class="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
                                Delete
                            </button>
                        </div>
                    </form>
                </div>

                <!-- Saved Keys List -->
                <div v-if="Object.keys(apiKeys).length > 0" class="border-t border-gray-200 pt-6">
                    <h4 class="text-sm font-medium text-gray-900 mb-4">Configured API Keys</h4>
                    <div class="space-y-3">
                        <div v-for="(key, provider) in apiKeys"
                             :key="provider"
                             class="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
                            <div class="flex items-center space-x-3">
                                <div class="h-8 w-8 rounded-lg flex items-center justify-center"
                                     :class="getProviderBgColor(provider)">
                                    <span class="text-sm font-bold" :class="getProviderTextColor(provider)">
                                        {{ getProviderIcon(provider) }}
                                    </span>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-900">{{ getProviderName(provider) }}</p>
                                    <div class="flex items-center space-x-2">
                                        <p class="text-xs text-gray-500 font-mono">
                                            {{ maskApiKey(key.api_key_preview || provider) }}
                                        </p>
                                        <button v-if="copiedKey === provider"
                                                class="text-xs text-green-600 flex items-center"
                                                disabled>
                                            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                                            </svg>
                                            Copied!
                                        </button>
                                    </div>
                                    <p class="text-xs text-gray-500 mt-1">
                                        {{ key.name || 'No name' }} • Last updated {{ formatDate(key.updated_at) }}
                                    </p>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                    <span class="h-1.5 w-1.5 rounded-full bg-green-400 mr-1"></span>
                                    Active
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Help Section -->
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div class="flex">
                        <svg class="h-5 w-5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                        <div class="ml-3 flex-1">
                            <h3 class="text-sm font-medium text-blue-800">How to get your API key</h3>
                            <div class="mt-2 text-sm text-blue-700">
                                <ul class="list-disc pl-5 space-y-1">
                                    <li>OpenAI: Visit <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" class="underline hover:text-blue-900">platform.openai.com/api-keys</a></li>
                                    <li>Anthropic: Visit <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" class="underline hover:text-blue-900">console.anthropic.com</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Delete Confirmation Modal -->
            <div v-if="showDeleteConfirm" class="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50" @click.self="showDeleteConfirm = false">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
                    <div class="flex items-start">
                        <div class="flex-shrink-0">
                            <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <div class="ml-3 flex-1">
                            <h3 class="text-lg font-medium text-gray-900">Delete API Key</h3>
                            <p class="mt-2 text-sm text-gray-500">
                                Are you sure you want to delete this API key for {{ getProviderName(selectedProvider) }}? This action cannot be undone.
                            </p>
                            <div class="mt-4 flex space-x-3">
                                <button @click="deleteApiKey"
                                        :disabled="deleting"
                                        class="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium disabled:opacity-50 transition-colors">
                                    {{ deleting ? 'Deleting...' : 'Delete' }}
                                </button>
                                <button @click="showDeleteConfirm = false"
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
            providers: [
                {
                    id: 'openai',
                    name: 'OpenAI',
                    icon: '🤖',
                    description: 'GPT-4, GPT-3.5, and more',
                    bgColor: 'bg-green-100',
                    textColor: 'text-green-700'
                },
                {
                    id: 'anthropic',
                    name: 'Anthropic',
                    icon: '🧠',
                    description: 'Claude 3 Opus, Sonnet, Haiku',
                    bgColor: 'bg-purple-100',
                    textColor: 'text-purple-700'
                }
            ],
            selectedProvider: null,
            apiKeys: {},
            apiKeyForm: {
                key: '',
                name: ''
            },
            showKey: false,
            saving: false,
            testing: false,
            deleting: false,
            loading: true,
            successMessage: '',
            errorMessage: '',
            showDeleteConfirm: false,
            copiedKey: null,
            newKeyToShow: null
        };
    },
    mounted() {
        this.loadApiKeys();
    },
    methods: {
        async loadApiKeys() {
            this.loading = true;
            try {
                // Use the api client which handles credentials automatically
                const apiClient = await import('../utils/api-client.js');
                const response = await apiClient.default.get("/api/auth/api-keys");

                // Convert array to object keyed by provider
                // Filter out non-AI providers (twitter is OAuth, not API key)
                this.apiKeys = response.data
                    .filter(key => key.provider !== 'twitter')
                    .reduce((acc, key) => {
                        acc[key.provider] = key;
                        return acc;
                    }, {});
            } catch (error) {
                console.error('Error loading API keys:', error);
                this.handleError(error, 'Failed to load API keys');
            } finally {
                this.loading = false;
            }
        },

        selectProvider(providerId) {
            this.selectedProvider = providerId;
            this.successMessage = '';
            this.errorMessage = '';
            this.newKeyToShow = null;

            // Load existing key if available
            if (this.apiKeys[providerId]) {
                this.apiKeyForm.name = this.apiKeys[providerId].name || '';
                this.apiKeyForm.key = ''; // Don't show the actual key
            } else {
                this.apiKeyForm = { key: '', name: '' };
            }
        },

        async saveApiKey() {
            this.successMessage = '';
            this.errorMessage = '';

            // Frontend validation before submission
            const validationError = this.validateApiKey(this.apiKeyForm.key, this.selectedProvider);
            if (validationError) {
                this.showErrorToast(validationError);
                return;
            }

            this.saving = true;

            try {
                // Trim whitespace before sending
                const trimmedKey = this.apiKeyForm.key.trim();

                // Use the api client
                const apiClient = await import('../utils/api-client.js');
                const response = await apiClient.default.post("/api/auth/api-keys", {
                    provider: this.selectedProvider,
                    api_key: trimmedKey,
                    name: this.apiKeyForm.name
                });

                // Store the full key temporarily for copying
                if (response.data.api_key) {
                    this.newKeyToShow = response.data.api_key;
                }

                // Enhanced success message with masked preview
                const maskedKey = this.maskApiKey(trimmedKey);
                this.showSuccessToast(`API key saved successfully! Your key: ${maskedKey}`);
                this.apiKeyForm.key = '';
                await this.loadApiKeys();

            } catch (error) {
                console.error('Error saving API key:', error);
                this.handleError(error, 'Failed to save API key');
            } finally {
                this.saving = false;
            }
        },

        validateApiKey(key, provider) {
            if (!key || key.trim().length === 0) {
                return 'Please enter an API key';
            }

            const trimmedKey = key.trim();

            if (key !== trimmedKey) {
                return 'Your API key has extra spaces. Please remove them.';
            }

            if (provider === 'openai') {
                if (!trimmedKey.startsWith('sk-')) {
                    if (trimmedKey.startsWith('k-')) {
                        return 'Your key is missing the "s" at the beginning!\n\nValid format: sk-proj-... or sk-...\nYour format: k-...';
                    }
                    return 'Invalid OpenAI API key format\n\nValid format: Must start with "sk-" or "sk-proj-"\nYour key starts with: "' + trimmedKey.substring(0, 5) + '..."\n\nGet a valid key from: https://platform.openai.com/api-keys';
                }

                if (trimmedKey.length < 20) {
                    return 'This OpenAI key looks too short\n\nValid OpenAI keys are typically 50+ characters\nYour key is only ' + trimmedKey.length + ' characters\n\nMake sure you copied the entire key';
                }
            } else if (provider === 'anthropic') {
                if (!trimmedKey.startsWith('sk-ant-')) {
                    if (trimmedKey.startsWith('k-ant-')) {
                        return 'Your key is missing the "s" at the beginning!\n\nValid format: sk-ant-...\nYour format: k-ant-...';
                    } else if (trimmedKey.startsWith('sk-')) {
                        return 'This looks like an OpenAI key, not Anthropic\n\nAnthropic keys start with: sk-ant-...\nYour key starts with: sk-...\n\nMake sure you\'re using the correct provider';
                    }
                    return 'Invalid Anthropic API key format\n\nValid format: Must start with "sk-ant-"\nYour key starts with: "' + trimmedKey.substring(0, 7) + '..."\n\nGet a valid key from: https://console.anthropic.com/settings/keys';
                }

                if (trimmedKey.length < 30) {
                    return 'This Anthropic key looks too short\n\nValid Anthropic keys are typically 100+ characters\nYour key is only ' + trimmedKey.length + ' characters\n\nMake sure you copied the entire key';
                }
            }

            return null;
        },

        async testApiKey() {
            this.testing = true;
            this.successMessage = '';
            this.errorMessage = '';

            try {
                const apiClient = await import('../utils/api-client.js');
                const response = await apiClient.default.post(`/api/auth/api-keys/${this.selectedProvider}/test`, {});

                const isValid = response.data.valid === true ||
                               response.data.success === true ||
                               response.status === 200;

                const responseMessage = response.data.message ||
                                       response.data.detail ||
                                       'API key test completed';

                if (isValid) {
                    this.showSuccessToast(responseMessage || 'API key is valid and working!');
                } else {
                    this.showErrorToast(responseMessage || 'API key is invalid or not working');
                }

            } catch (error) {
                console.error('[API Key Test] Error:', error);

                if (error.response && error.response.status === 200) {
                    const message = error.response.data?.message || 'API key is valid and working!';
                    this.showSuccessToast(message);
                } else {
                    this.handleError(error, 'Failed to test API key');
                }
            } finally {
                this.testing = false;
            }
        },

        confirmDeleteApiKey() {
            this.showDeleteConfirm = true;
        },

        async deleteApiKey() {
            this.deleting = true;

            try {
                const apiClient = await import('../utils/api-client.js');
                await apiClient.default.delete(`/api/auth/api-keys/${this.selectedProvider}`);

                this.showSuccessToast('API key deleted successfully');
                this.apiKeyForm = { key: '', name: '' };
                this.showDeleteConfirm = false;
                await this.loadApiKeys();

            } catch (error) {
                console.error('Error deleting API key:', error);
                this.handleError(error, 'Failed to delete API key');
            } finally {
                this.deleting = false;
            }
        },

        copyToClipboard(text, provider) {
            navigator.clipboard.writeText(text).then(() => {
                this.copiedKey = provider;
                setTimeout(() => {
                    this.copiedKey = null;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                this.showErrorToast('Failed to copy to clipboard');
            });
        },

        maskApiKey(key) {
            if (!key) return 'sk-...';

            if (key.length > 15) {
                return `${key.substring(0, 7)}...${key.substring(key.length - 4)}`;
            }

            return key;
        },

        getProviderName(providerId) {
            const provider = this.providers.find(p => p.id === providerId);
            return provider ? provider.name : providerId;
        },

        getProviderIcon(providerId) {
            const provider = this.providers.find(p => p.id === providerId);
            return provider ? provider.icon : '🔑';
        },

        getProviderBgColor(providerId) {
            const provider = this.providers.find(p => p.id === providerId);
            return provider ? provider.bgColor : 'bg-gray-100';
        },

        getProviderTextColor(providerId) {
            const provider = this.providers.find(p => p.id === providerId);
            return provider ? provider.textColor : 'text-gray-700';
        },

        getPlaceholder(providerId) {
            const placeholders = {
                openai: 'sk-...',
                anthropic: 'sk-ant-...'
            };
            return placeholders[providerId] || 'Enter your API key';
        },

        formatDate(dateString) {
            if (!dateString) return 'Recently';
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays}d ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
            return date.toLocaleDateString();
        },

        handleError(error, defaultMessage) {
            if (error.response) {
                const status = error.response.status;
                const detail = error.response.data?.detail;

                if (status === 401) {
                    this.showErrorToast('Session expired. Please login again.');
                    setTimeout(() => {
                        window.location.href = 'auth.html';
                    }, 2000);
                } else if (status === 404) {
                    this.showErrorToast(detail || 'Resource not found');
                } else if (status === 422) {
                    this.showErrorToast(detail || 'Please check your input and try again');
                } else {
                    this.showErrorToast(detail || defaultMessage);
                }
            } else if (error.request) {
                this.showErrorToast('Cannot connect to server. Please check if the backend is running.');
            } else {
                this.showErrorToast(defaultMessage);
            }
        },

        showSuccessToast(message) {
            this.successMessage = message;
            setTimeout(() => {
                this.successMessage = '';
            }, 3000);
        },

        showErrorToast(message) {
            this.errorMessage = message;
            setTimeout(() => {
                this.errorMessage = '';
            }, 5000);
        }
    }
};

// Export as ES6 module default export
export default ApiKeyManager;
