import { createApp } from 'vue'
import api from './utils/api-client.js'
import { showToast } from './utils/toast.js'
import logger from './utils/logger.js'
import '/src/style.css'

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api`;

const app = createApp({
    data() {
        return {
            currentStep: 1,
            totalSteps: 6,
            expandedSteps: {
                1: true,
                2: false,
                3: false,
                4: false,
                5: false,
                6: false
            },
            stepCompleted: {
                1: false,
                2: false,
                3: false,
                4: false,
                5: false,
                6: false
            },

            // Step titles for progress bar
            stepTitles: ['Account', 'Project', 'Keys', 'Callback', 'Enter Keys', 'Connect'],

            // Step 4: Callback URL
            callbackUrl: `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/social-media/twitter/callback`,
            callbackCopied: false,

            // Step 5: Credentials
            apiKeys: {
                apiKey: '',
                apiSecret: ''
            },
            apiKeyValidation: {
                apiKey: null,  // null = not validated, true = valid, false = invalid
                apiSecret: null
            },
            showApiSecret: false,
            savingCredentials: false,
            deletingCredentials: false,
            testingConnection: false,
            keyValidationError: '',
            credentialsSaved: false,
            connectionTestResult: null, // null = not tested, 'success' = passed, 'failed' = failed
            connectionTestError: '',

            // Step 6: OAuth Connection
            isConnected: false,
            oauthUsername: '',
            connectingTwitter: false,

            setupComplete: false,

            // Toast notification state
            toast: {
                show: false,
                message: '',
                type: 'info'
            }
        };
    },
    computed: {
        progress() {
            const completedCount = Object.values(this.stepCompleted).filter(Boolean).length;
            return (completedCount / this.totalSteps) * 100;
        }
    },
    mounted() {
        // Load saved progress from localStorage
        this.loadProgress();

        // Check for OAuth callback
        this.checkForOAuthCallback();
    },
    methods: {
        toggleStep(step) {
            // Only allow opening if previous steps are completed (except step 1)
            if (step > 1 && !this.stepCompleted[step - 1]) {
                return;
            }

            this.expandedSteps[step] = !this.expandedSteps[step];

            // Update current step when expanding
            if (this.expandedSteps[step]) {
                this.currentStep = step;
            }
        },

        completeStep(step) {
            this.stepCompleted[step] = true;
            this.expandedSteps[step] = false;

            // Auto-expand next step
            if (step < this.totalSteps) {
                this.currentStep = step + 1;
                this.expandedSteps[step + 1] = true;
            } else {
                // All steps complete
                this.setupComplete = true;
                this.celebrateCompletion();
            }

            // Save progress
            this.saveProgress();
        },

        // Step 4: Copy callback URL
        copyCallbackUrl() {
            navigator.clipboard.writeText(this.callbackUrl).then(() => {
                this.callbackCopied = true;
                this.showToastNotification('Callback URL copied to clipboard!', 'success');
                setTimeout(() => {
                    this.callbackCopied = false;
                }, 3000);
            }).catch(err => {
                logger.error('Failed to copy callback URL:', err);
                this.showToastNotification('Failed to copy URL', 'error');
            });
        },

        // Step 5: Credential validation
        validateApiKeyFormat() {
            const key = this.apiKeys.apiKey;
            if (!key) {
                this.apiKeyValidation.apiKey = null;
                return;
            }
            // Twitter API keys are typically 25 characters
            this.apiKeyValidation.apiKey = key.length >= 20 && key.length <= 30;
        },

        validateApiSecretFormat() {
            const secret = this.apiKeys.apiSecret;
            if (!secret) {
                this.apiKeyValidation.apiSecret = null;
                return;
            }
            // Twitter API secrets are typically 50 characters
            this.apiKeyValidation.apiSecret = secret.length >= 40 && secret.length <= 60;
        },

        async saveCredentials() {
            if (this.savingCredentials) return;

            this.validateApiKeyFormat();
            this.validateApiSecretFormat();

            if (!this.apiKeyValidation.apiKey || !this.apiKeyValidation.apiSecret) {
                this.keyValidationError = 'Please enter valid API Key and API Secret';
                return;
            }

            this.savingCredentials = true;
            this.keyValidationError = '';

            try {
                logger.debug('[Twitter Setup] Saving credentials to backend...');

                // Save credentials to backend with encryption
                const response = await api.post('/api/oauth-setup/twitter/credentials', {
                    api_key: this.apiKeys.apiKey,
                    api_secret: this.apiKeys.apiSecret,
                    callback_url: this.callbackUrl
                });

                logger.debug('[Twitter Setup] Credentials saved successfully:', response.data);

                if (response.data.success) {
                    this.credentialsSaved = true;
                    this.connectionTestResult = null; // Reset test result
                    this.saveProgress();
                    // Don't show toast - the UI already shows "Credentials Configured" status
                } else {
                    throw new Error(response.data.message || 'Failed to save credentials');
                }
            } catch (error) {
                logger.error('[Twitter Setup] Error saving credentials:', error);

                // Extract error message from response
                let errorMessage = 'Failed to save credentials. Please check your keys and try again.';

                if (error.response) {
                    // Backend returned an error response
                    const { status, data } = error.response;

                    if (status === 403) {
                        errorMessage = 'Authentication required. Please log in and try again.';
                    } else if (status === 400) {
                        errorMessage = data.detail || data.message || 'Invalid credentials format';
                    } else if (data && (data.detail || data.message)) {
                        errorMessage = data.detail || data.message;
                    }
                } else if (error.message) {
                    errorMessage = error.message;
                }

                this.keyValidationError = errorMessage;
                this.showToastNotification(errorMessage, 'error', 5000);
            } finally {
                this.savingCredentials = false;
            }
        },

        async testConnection() {
            if (this.testingConnection) return;

            this.testingConnection = true;
            this.connectionTestResult = null;
            this.connectionTestError = '';
            this.keyValidationError = '';

            try {
                logger.debug('[Twitter Setup] Testing connection and decryption...');

                // Call backend endpoint to test credential decryption
                const response = await api.get('/api/oauth-setup/twitter/test-credentials');

                logger.debug('[Twitter Setup] Connection test response:', response.data);

                if (response.data.success) {
                    this.connectionTestResult = 'success';
                    this.saveProgress();
                    this.showToastNotification('Connection test successful!', 'success');
                } else {
                    throw new Error(response.data.message || 'Connection test failed');
                }
            } catch (error) {
                logger.error('[Twitter Setup] Connection test failed:', error);

                this.connectionTestResult = 'failed';

                // Extract error message
                let errorMessage = 'Failed to verify credentials. Please check and try again.';

                if (error.response) {
                    const { status, data } = error.response;

                    if (status === 404) {
                        errorMessage = 'No credentials found. Please save your credentials first.';
                    } else if (status === 500) {
                        errorMessage = 'Decryption failed. The credentials may be corrupted. Please re-enter them.';
                    } else if (data && (data.detail || data.message)) {
                        errorMessage = data.detail || data.message;
                    }
                } else if (error.message) {
                    errorMessage = error.message;
                }

                this.connectionTestError = errorMessage;
                this.showToastNotification(errorMessage, 'error', 5000);
            } finally {
                this.testingConnection = false;
            }
        },

        resetCredentials() {
            // Clear credentials and allow user to re-enter them
            this.credentialsSaved = false;
            this.connectionTestResult = null;
            this.connectionTestError = '';
            this.keyValidationError = '';
            this.apiKeys.apiKey = '';
            this.apiKeys.apiSecret = '';
            this.apiKeyValidation.apiKey = null;
            this.apiKeyValidation.apiSecret = null;

            // Save updated state
            this.saveProgress();

            this.showToastNotification('Credentials reset. Please re-enter your API keys.', 'info');

            logger.debug('[Twitter Setup] Credentials reset for re-entry');
        },

        async deleteCredentials() {
            if (this.deletingCredentials) return;

            // Confirm deletion
            if (!confirm('Are you sure you want to delete your Twitter API credentials? This action cannot be undone.')) {
                return;
            }

            this.deletingCredentials = true;

            try {
                logger.debug('[Twitter Setup] Deleting credentials from backend...');

                // Delete credentials from backend
                const response = await api.delete('/api/oauth-setup/twitter/credentials');

                logger.debug('[Twitter Setup] Credentials deleted successfully:', response.data);

                if (response.data.success) {
                    // Clear local state
                    this.credentialsSaved = false;
                    this.connectionTestResult = null;
                    this.connectionTestError = '';
                    this.keyValidationError = '';
                    this.apiKeys.apiKey = '';
                    this.apiKeys.apiSecret = '';
                    this.apiKeyValidation.apiKey = null;
                    this.apiKeyValidation.apiSecret = null;

                    // Save updated state
                    this.saveProgress();

                    this.showToastNotification('Twitter credentials deleted successfully', 'success');
                } else {
                    throw new Error(response.data.message || 'Failed to delete credentials');
                }
            } catch (error) {
                logger.error('[Twitter Setup] Error deleting credentials:', error);
                this.showToastNotification(
                    error.message || 'Failed to delete credentials. Please try again.',
                    'error'
                );
            } finally {
                this.deletingCredentials = false;
            }
        },

        // Step 6: OAuth connection using per-user credentials
        async connectTwitterWithUserCredentials() {
            // Prevent multiple simultaneous connection attempts
            if (this.connectingTwitter) return;

            this.connectingTwitter = true;

            try {
                logger.debug('[Twitter Setup] Initiating per-user OAuth connection...');

                const response = await api.get('/api/social-media/twitter/connect', {
                    params: {
                        return_url: encodeURIComponent(window.location.href)
                    }
                });

                logger.debug('[Twitter Setup] OAuth response:', response.data);

                if (response.data.success && response.data.authorization_url) {
                    // Open OAuth popup
                    const width = 600;
                    const height = 700;
                    const left = (window.screen.width / 2) - (width / 2);
                    const top = (window.screen.height / 2) - (height / 2);

                    window.open(
                        response.data.authorization_url,
                        'twitter_oauth',
                        `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
                    );

                    this.showToastNotification('Opening Twitter authorization window...', 'info');
                } else {
                    throw new Error('No authorization URL received');
                }
            } catch (error) {
                logger.error('[Twitter Setup] Error connecting Twitter:', error);

                // Enhanced error handling with specific messages
                let errorMessage = 'Failed to connect Twitter. Please try again.';
                let errorDuration = 5000;

                if (error.response) {
                    const { status, data = {} } = error.response;

                    switch (status) {
                        case 428:
                            // Precondition Required - No credentials saved
                            errorMessage = 'Please complete Step 5 first to save your Twitter API credentials before connecting.';
                            errorDuration = 7000;

                            // Scroll to Step 5 and expand it
                            this.currentStep = 5;
                            this.expandedSteps[5] = true;
                            this.expandedSteps[6] = false;

                            // Scroll to step 5 smoothly
                            setTimeout(() => {
                                const step5Element = document.querySelector('[data-step="5"]');
                                if (step5Element) {
                                    step5Element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                }
                            }, 100);
                            break;

                        case 500:
                            // Server error - show detailed message if available
                            errorMessage = data?.detail
                                ? `Server error: ${data.detail}`
                                : 'Internal server error. Please check your API credentials and try again.';
                            break;

                        case 401:
                            // Unauthorized - user not logged in
                            errorMessage = 'Your session has expired. Please log in again and retry.';
                            setTimeout(() => {
                                window.location.href = '/auth.html';
                            }, 3000);
                            break;

                        case 403:
                            // Forbidden - insufficient permissions
                            errorMessage = 'Access denied. Please check your account permissions.';
                            break;

                        case 404:
                            // Not found - endpoint doesn't exist
                            errorMessage = 'Connection endpoint not found. Please contact support.';
                            break;

                        default:
                            // Other HTTP errors
                            errorMessage = data?.detail || data?.message || `Connection failed with status ${status}`;
                            break;
                    }
                } else if (error.request) {
                    // Network error - no response received
                    errorMessage = 'Unable to reach the server. Please check your internet connection and try again.';
                } else if (error.message) {
                    // Other errors
                    errorMessage = error.message;
                }

                this.showToastNotification(errorMessage, 'error', errorDuration);
            } finally {
                this.connectingTwitter = false;
            }
        },

        // Check for OAuth callback parameters in URL
        checkForOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const success = urlParams.get('success');
            const platform = urlParams.get('platform');
            const username = urlParams.get('username');
            const error = urlParams.get('error');

            if (platform === 'twitter') {
                if (success === 'true' && username) {
                    this.isConnected = true;
                    this.oauthUsername = username;
                    this.completeStep(6);
                    this.showToastNotification(`Twitter connected successfully as @${username}!`, 'success');
                } else if (error) {
                    let errorMessage = 'Failed to connect Twitter account.';
                    if (error === 'user_denied') {
                        errorMessage = 'You cancelled the Twitter authorization.';
                    } else if (error === 'oauth_failed') {
                        errorMessage = 'Twitter authorization failed. Please check your API credentials.';
                    }
                    this.showToastNotification(errorMessage, 'error', 5000);
                }

                // Clean up URL parameters
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        },

        // Handle OAuth callback from Twitter (legacy, kept for compatibility)
        handleConnectionStatus(event) {
            if (event.success) {
                this.isConnected = true;
                this.oauthUsername = event.username || '';
                this.completeStep(6);
                this.showToastNotification(`Twitter connected successfully as @${event.username}!`, 'success');
            }
        },

        celebrateCompletion() {
            // Create confetti effect
            const colors = ['#818cf8', '#34d399', '#fbbf24', '#f87171', '#a78bfa'];

            for (let i = 0; i < 50; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.className = 'confetti';
                    confetti.style.left = Math.random() * 100 + '%';
                    confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.animationDelay = Math.random() * 0.5 + 's';
                    document.body.appendChild(confetti);

                    setTimeout(() => confetti.remove(), 3000);
                }, i * 30);
            }

            this.showToastNotification('Twitter setup complete! You can now publish tweets.', 'success');
        },

        showToastNotification(message, type = 'info', duration = 3000) {
            // Use the utility function
            showToast(message, type, duration);

            // Also update internal state for template
            this.toast.show = true;
            this.toast.message = message;
            this.toast.type = type;

            // Auto-hide after duration
            setTimeout(() => {
                this.toast.show = false;
            }, duration);
        },

        saveProgress() {
            const progress = {
                stepCompleted: this.stepCompleted,
                currentStep: this.currentStep,
                setupComplete: this.setupComplete,
                isConnected: this.isConnected,
                oauthUsername: this.oauthUsername,
                credentialsSaved: this.credentialsSaved,
                connectionTestResult: this.connectionTestResult
            };
            localStorage.setItem('twitter_setup_progress', JSON.stringify(progress));
        },

        loadProgress() {
            const saved = localStorage.getItem('twitter_setup_progress');
            if (saved) {
                try {
                    const progress = JSON.parse(saved);
                    this.stepCompleted = progress.stepCompleted || { 1: false, 2: false, 3: false, 4: false, 5: false, 6: false };
                    this.currentStep = progress.currentStep || 1;
                    this.setupComplete = progress.setupComplete || false;
                    this.isConnected = progress.isConnected || false;
                    this.oauthUsername = progress.oauthUsername || '';
                    this.credentialsSaved = progress.credentialsSaved || false;
                    this.connectionTestResult = progress.connectionTestResult || null;

                    // Expand current step
                    if (this.currentStep <= this.totalSteps) {
                        this.expandedSteps[this.currentStep] = true;
                    }
                } catch (error) {
                    logger.error('Error loading Twitter setup progress:', error);
                }
            }
        },

        goBack() {
            window.location.href = 'profile.html#social-connections';
        },

        goToNewsFeed() {
            window.location.href = 'index.html';
        }
    }
});

app.mount('#setup-app');
