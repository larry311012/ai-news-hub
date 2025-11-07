import { createApp } from 'vue'
import api from './utils/api-client.js'
import { showToast } from './utils/toast.js'
import logger from './utils/logger.js'
import '/src/style.css'

console.log('[LinkedIn Setup] All modules imported successfully');

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api`;

console.log('[LinkedIn Setup] Creating Vue app...');

try {
const app = createApp({
    data() {
        return {
            // Toast notification state
            toast: {
                show: false,
                type: 'info',
                message: ''
            },

            currentStep: 1,
            totalSteps: 7,
            expandedSteps: {
                1: true,
                2: false,
                3: false,
                4: false,
                5: false,
                6: false,
                7: false
            },
            stepCompleted: {
                1: false,
                2: false,
                3: false,
                4: false,
                5: false,
                6: false,
                7: false
            },

            // Step titles for progress bar
            stepTitles: ['Account', 'Create App', 'Enable Products', 'Copy Keys', 'Redirect URI', 'Enter Keys', 'Connect'],

            // Step 3 - Products enabled checkbox
            productsEnabled: false,

            // Step 5: Redirect URI
            redirectUri: `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/oauth-setup/linkedin/callback`,
            redirectUriCopied: false,

            // Step 6: Credentials
            credentials: {
                clientId: '',
                clientSecret: ''
            },
            credentialValidation: {
                clientId: null,
                clientSecret: null
            },
            showClientSecret: false,
            savingCredentials: false,
            deletingCredentials: false,
            credentialSaveError: '',
            credentialsSaved: false,

            // Step 7: OAuth Connection
            isConnected: false,
            connecting: false,
            connectionAbortController: null,
            connectionTimeoutId: null,
            testing: false,
            testResult: null,
            showOAuthError: false,

            // Configuration test results
            configTestResult: null,
            testingConfig: false,

            // Debug mode
            debugMode: false,
            debugInfo: [],

            setupComplete: false
        };
    },
    computed: {
        progress() {
            const completedCount = Object.values(this.stepCompleted).filter(Boolean).length;
            return (completedCount / this.totalSteps) * 100;
        }
    },
    mounted() {
        console.log('[LinkedIn Setup] Vue app mounted successfully!');

        // Signal that Vue mounted successfully (for error detection)
        window.__vueAppMounted = true;

        // Load saved progress from localStorage
        this.loadProgress();

        // Check if already connected
        this.checkConnectionStatus();

        // Handle OAuth callback
        this.handleOAuthCallback();

        // Enable debug mode if URL has ?debug=true
        const urlParams = new URLSearchParams(window.location.search);
        this.debugMode = urlParams.get('debug') === 'true';

        if (this.debugMode) {
            logger.debug('Debug mode enabled for LinkedIn setup');
        }
    },
    beforeUnmount() {
        // Clean up timeouts and abort controllers
        this.cleanupConnection();
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
            console.log('[LinkedIn Setup] Complete step called:', step);
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

        // Go back to specific step
        goBackToStep(step) {
            if (step < 1 || step > this.totalSteps) {
                logger.error('Invalid step number:', step);
                return;
            }

            // Close current step
            this.expandedSteps[this.currentStep] = false;

            // Open target step
            this.currentStep = step;
            this.expandedSteps[step] = true;

            // Hide OAuth error section
            this.showOAuthError = false;

            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });

            showToast(`Navigating back to Step ${step}`, 'info');
        },

        // Step 5: Copy redirect URI
        copyRedirectUri() {
            navigator.clipboard.writeText(this.redirectUri).then(() => {
                this.redirectUriCopied = true;
                showToast('Redirect URI copied!', 'success');
                setTimeout(() => {
                    this.redirectUriCopied = false;
                }, 3000);
            }).catch(err => {
                logger.error('Failed to copy redirect URI:', err);
                showToast('Failed to copy URL', 'error');
            });
        },

        // Step 6: Credential validation
        validateClientIdFormat() {
            const id = this.credentials.clientId;
            if (!id) {
                this.credentialValidation.clientId = null;
                return;
            }
            // LinkedIn Client IDs are typically alphanumeric strings
            this.credentialValidation.clientId = id.length >= 10 && /^[a-zA-Z0-9]+$/.test(id);
        },

        validateClientSecretFormat() {
            const secret = this.credentials.clientSecret;
            if (!secret) {
                this.credentialValidation.clientSecret = null;
                return;
            }
            // LinkedIn Client Secrets are typically long alphanumeric strings
            this.credentialValidation.clientSecret = secret.length >= 16;
        },

        // Test LinkedIn app configuration
        async testConfiguration() {
            if (this.testingConfig) return;

            this.testingConfig = true;
            this.configTestResult = null;

            try {
                // Validation checks
                const issues = [];
                const warnings = [];

                if (!this.credentials.clientId) {
                    issues.push('Client ID is not set');
                } else if (this.credentialValidation.clientId === false) {
                    warnings.push('Client ID format looks invalid (should be 10+ alphanumeric characters)');
                }

                if (!this.credentials.clientSecret) {
                    issues.push('Client Secret is not set');
                } else if (this.credentialValidation.clientSecret === false) {
                    warnings.push('Client Secret format looks invalid (should be 16+ characters)');
                }

                if (!this.redirectUri) {
                    issues.push('Redirect URI is not set');
                }

                if (issues.length > 0) {
                    this.configTestResult = {
                        success: false,
                        title: 'Configuration Incomplete',
                        message: 'Please fix the following issues:',
                        items: issues,
                        type: 'error'
                    };
                    showToast('Configuration test failed - see details below', 'error');
                    return;
                }

                if (warnings.length > 0) {
                    this.configTestResult = {
                        success: false,
                        title: 'Configuration Warnings',
                        message: 'Please review the following warnings:',
                        items: warnings,
                        type: 'warning'
                    };
                    showToast('Configuration test passed with warnings', 'warning');
                    return;
                }

                // All checks passed
                this.configTestResult = {
                    success: true,
                    title: 'Configuration Looks Good!',
                    message: 'Your settings appear to be configured correctly:',
                    items: [
                        `Client ID: ${this.credentials.clientId.substring(0, 8)}...`,
                        `Client Secret: ***${this.credentials.clientSecret.slice(-4)}`,
                        `Redirect URI: ${this.redirectUri}`
                    ],
                    type: 'success'
                };
                showToast('Configuration test passed!', 'success');

            } catch (error) {
                logger.error('Configuration test error:', error);
                this.configTestResult = {
                    success: false,
                    title: 'Test Error',
                    message: 'An error occurred while testing configuration',
                    items: [error.message],
                    type: 'error'
                };
            } finally {
                this.testingConfig = false;
            }
        },

        // Verify settings before saving
        verifySettings() {
            // Validation checks
            const warnings = [];

            if (!this.credentials.clientId) {
                warnings.push('Client ID is not set');
            } else if (this.credentialValidation.clientId === false) {
                warnings.push('Client ID format looks invalid');
            }

            if (!this.credentials.clientSecret) {
                warnings.push('Client Secret is not set');
            } else if (this.credentialValidation.clientSecret === false) {
                warnings.push('Client Secret format looks invalid');
            }

            if (!this.redirectUri) {
                warnings.push('Redirect URI is not set');
            }

            if (warnings.length > 0) {
                logger.warn('LinkedIn credentials warnings:', warnings);
                showToast(`Settings have ${warnings.length} warning(s)`, 'warning');
            } else {
                logger.debug('LinkedIn credentials verified');
                showToast('Settings verified successfully', 'success');
            }
        },

        async saveCredentials() {
            if (this.savingCredentials) return;

            this.validateClientIdFormat();
            this.validateClientSecretFormat();

            if (!this.credentialValidation.clientId || !this.credentialValidation.clientSecret) {
                this.credentialSaveError = 'Please enter valid Client ID and Client Secret';
                return;
            }

            this.savingCredentials = true;
            this.credentialSaveError = '';

            try {
                this.logDebug('Saving LinkedIn credentials', {
                    redirectUri: this.redirectUri
                });

                // Save credentials to backend
                // Endpoint must start with /api to be proxied by Vite dev server
                const response = await api.post('/api/oauth-setup/linkedin/credentials', {
                    client_id: this.credentials.clientId,
                    client_secret: this.credentials.clientSecret,
                    redirect_uri: this.redirectUri
                });

                this.logDebug('Credentials saved successfully', response.data);

                if (response.data.success) {
                    this.credentialsSaved = true;
                    this.saveProgress();
                    showToast('Credentials saved successfully!', 'success');
                } else {
                    throw new Error(response.data.message || 'Failed to save credentials');
                }
            } catch (error) {
                logger.error('Error saving LinkedIn credentials:', error);

                this.logDebug('Error saving credentials', {
                    status: error.status,
                    message: error.message
                });

                // Handle specific error codes
                if (error.status === 401) {
                    this.credentialSaveError = 'Your session has expired. Please log in again.';
                    showToast('Session expired. Redirecting to login...', 'error');
                    setTimeout(() => {
                        const returnUrl = encodeURIComponent(window.location.href);
                        window.location.href = `auth.html?return=${returnUrl}`;
                    }, 2000);
                } else if (error.status === 403) {
                    this.credentialSaveError = 'You do not have permission to save credentials. Please check your account permissions.';
                } else if (error.status === 400) {
                    this.credentialSaveError = 'Invalid credentials format. Please check your input.';
                } else {
                    this.credentialSaveError = 'Failed to save credentials. Please check your keys and try again.';
                }
            } finally {
                this.savingCredentials = false;
            }
        },

        resetCredentials() {
            // Clear credentials and allow user to re-enter them
            this.credentialsSaved = false;
            this.credentials.clientId = '';
            this.credentials.clientSecret = '';
            this.credentialValidation.clientId = null;
            this.credentialValidation.clientSecret = null;
            this.credentialSaveError = '';

            // Save updated state
            this.saveProgress();

            showToast('Credentials reset. Please re-enter your client keys.', 'info');
            this.logDebug('Credentials reset for re-entry');
        },

        async deleteCredentials() {
            if (this.deletingCredentials) return;

            // Confirm deletion
            if (!confirm('Are you sure you want to delete your LinkedIn app credentials? This action cannot be undone.')) {
                return;
            }

            this.deletingCredentials = true;

            try {
                this.logDebug('Deleting LinkedIn credentials from backend');

                // Delete credentials from backend
                const response = await api.delete('/api/oauth-setup/linkedin/credentials');

                this.logDebug('Credentials deleted successfully', response.data);

                if (response.data.success) {
                    // Clear local state
                    this.credentialsSaved = false;
                    this.credentials.clientId = '';
                    this.credentials.clientSecret = '';
                    this.credentialValidation.clientId = null;
                    this.credentialValidation.clientSecret = null;
                    this.credentialSaveError = '';

                    // Save updated state
                    this.saveProgress();

                    showToast('LinkedIn credentials deleted successfully', 'success');
                } else {
                    throw new Error(response.data.message || 'Failed to delete credentials');
                }
            } catch (error) {
                logger.error('Error deleting LinkedIn credentials:', error);

                this.logDebug('Error deleting credentials', {
                    status: error.status,
                    message: error.message
                });

                showToast(
                    error.message || 'Failed to delete credentials. Please try again.',
                    'error'
                );
            } finally {
                this.deletingCredentials = false;
            }
        },

        // Clean up connection resources
        cleanupConnection() {
            if (this.connectionAbortController) {
                this.connectionAbortController.abort();
                this.connectionAbortController = null;
            }
            if (this.connectionTimeoutId) {
                clearTimeout(this.connectionTimeoutId);
                this.connectionTimeoutId = null;
            }
        },

        // Cancel connection attempt
        cancelConnection() {
            this.logDebug('User cancelled connection attempt');

            this.cleanupConnection();
            this.connecting = false;
            showToast('Connection cancelled', 'info');
        },

        // Show LinkedIn app configuration help
        showLinkedInConfigHelp() {
            const clientId = this.credentials.clientId || '[YOUR_CLIENT_ID]';
            const message = `
LinkedIn OAuth Error - Check Your App Configuration:

1. Go to: https://www.linkedin.com/developers/apps
2. Find your app (Client ID: ${clientId})
3. Verify:
   ✓ App status is "Active" (not deleted/suspended)
   ✓ Redirect URI added: ${this.redirectUri}
   ✓ Products enabled: "Sign In with LinkedIn using OpenID Connect" and "Share on LinkedIn"
   ✓ Scopes authorized: openid, profile, email, w_member_social

Common issues:
- Redirect URI must match EXACTLY (no extra slashes)
- App must be in Development mode for localhost
- Products must be approved (not just requested)
- Check app is not suspended or deleted
            `;
            logger.error(message);
            showToast('LinkedIn app configuration issue. Check console for help.', 'error');
            this.showOAuthError = true;
        },

        // Step 7: OAuth connection
        async connectLinkedIn() {
            // Prevent multiple simultaneous connection attempts
            if (this.connecting) {
                return;
            }

            this.connecting = true;
            this.testResult = null;
            this.showOAuthError = false;

            // Clean up any existing connection resources
            this.cleanupConnection();

            // Set up loading state timeout (auto-reset after 15 seconds)
            this.connectionTimeoutId = setTimeout(() => {
                if (this.connecting) {
                    logger.error('Loading state timeout - resetting');
                    this.logDebug('Loading state timeout - auto-resetting', {
                        duration: '15 seconds'
                    });
                    this.connecting = false;
                    showToast('Connection attempt timed out. Please check your internet connection and try again.', 'error');
                    this.showOAuthError = true;
                }
            }, 15000);

            try {
                const returnUrl = encodeURIComponent(window.location.href);

                this.logDebug('Initiating LinkedIn OAuth connection', {
                    returnUrl: window.location.href
                });

                // Make API call
                const response = await api.get(`/api/oauth-setup/linkedin/connect?return_url=${returnUrl}`);

                this.logDebug('OAuth connect response received', {
                    success: response.data.success,
                    hasAuthUrl: !!response.data.authorization_url,
                    platform: response.data.platform
                });

                if (response.data.redirect_uri || response.data.debug_info?.redirect_uri) {
                    const redirectUri = response.data.redirect_uri || response.data.debug_info?.redirect_uri;
                    this.logDebug('IMPORTANT: Redirect URI Check', {
                        redirectUri: redirectUri,
                        message: 'This must match EXACTLY with your LinkedIn app settings'
                    });
                }

                if (response.data.success && response.data.authorization_url) {
                    // Open OAuth popup
                    const width = 600;
                    const height = 700;
                    const left = (window.screen.width / 2) - (width / 2);
                    const top = (window.screen.height / 2) - (height / 2);

                    this.logDebug('Opening OAuth popup', {
                        dimensions: `${width}x${height}`
                    });

                    const popup = window.open(
                        response.data.authorization_url,
                        'linkedin_oauth',
                        `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
                    );

                    if (!popup) {
                        this.logDebug('Popup blocked');
                        showToast('Please enable popups and try again', 'error');
                        this.connecting = false;
                        clearTimeout(this.connectionTimeoutId);
                        this.connectionTimeoutId = null;
                        this.showLinkedInConfigHelp();
                        return;
                    }

                    // Monitor popup closure
                    const checkPopup = setInterval(() => {
                        if (popup.closed) {
                            clearInterval(checkPopup);
                            this.connecting = false;
                            clearTimeout(this.connectionTimeoutId);
                            this.connectionTimeoutId = null;
                            this.logDebug('OAuth popup closed');
                            // Check connection status after popup closes
                            setTimeout(() => {
                                this.checkConnectionStatus();
                            }, 1000);
                        }
                    }, 500);
                } else {
                    throw new Error('No authorization URL received');
                }
            } catch (error) {
                // Clear timeout
                clearTimeout(this.connectionTimeoutId);
                this.connectionTimeoutId = null;

                logger.error('Error connecting LinkedIn:', error);

                this.logDebug('Error connecting LinkedIn', {
                    status: error.status,
                    message: error.message
                });

                let errorMessage = 'Failed to connect LinkedIn. Please try again.';

                // Handle specific error cases
                if (error.status === 401) {
                    errorMessage = 'Your session has expired. Please log in again.';
                    showToast(errorMessage, 'error');
                    setTimeout(() => {
                        const returnUrl = encodeURIComponent(window.location.href);
                        window.location.href = `auth.html?return=${returnUrl}`;
                    }, 2000);
                } else if (error.status === 403) {
                    const detail = error.message || '';

                    if (detail.toLowerCase().includes('credential') ||
                        detail.toLowerCase().includes('not configured') ||
                        detail.toLowerCase().includes('client id') ||
                        detail.toLowerCase().includes('client secret')) {
                        errorMessage = 'LinkedIn credentials not configured. Please complete Step 6 first.';
                        this.goBackToStep(6);
                    } else {
                        errorMessage = 'Authentication error. Please check your credentials in Step 6.';
                    }
                    this.showLinkedInConfigHelp();
                } else if (error.status === 400) {
                    errorMessage = 'Invalid credentials. Please check your Client ID and Secret in Step 6.';
                    this.goBackToStep(6);
                    this.showLinkedInConfigHelp();
                } else if (error.status === 503) {
                    errorMessage = 'LinkedIn OAuth is not configured on the server. Please contact support.';
                } else if (error.status === 500) {
                    errorMessage = 'Server error occurred. Please try again later or contact support.';
                    this.showLinkedInConfigHelp();
                } else if (!navigator.onLine) {
                    errorMessage = 'Connection failed. Please check your internet connection.';
                } else {
                    this.showLinkedInConfigHelp();
                }

                showToast(errorMessage, 'error');
                this.showOAuthError = true;
            } finally {
                // Always reset loading state in finally block
                this.connecting = false;

                // Clean up timeout
                if (this.connectionTimeoutId) {
                    clearTimeout(this.connectionTimeoutId);
                    this.connectionTimeoutId = null;
                }
            }
        },

        async checkConnectionStatus() {
            try {
                this.logDebug('Checking LinkedIn connection status');

                const response = await api.get('/api/oauth-setup/linkedin/status');

                this.logDebug('Connection status response', response.data);

                this.isConnected = response.data.connected && !response.data.is_expired;

                if (this.isConnected && !this.stepCompleted[7]) {
                    this.stepCompleted[7] = true;
                    this.saveProgress();
                }
            } catch (error) {
                logger.error('Error checking LinkedIn connection status:', error);

                this.logDebug('Error checking connection status', {
                    status: error.status,
                    message: error.message
                });
            }
        },

        handleOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const success = urlParams.get('success');
            const platform = urlParams.get('platform');
            const error = urlParams.get('error');

            if (platform === 'linkedin') {
                this.logDebug('Handling OAuth callback', { success, platform, error });

                if (success === 'true') {
                    this.isConnected = true;
                    this.stepCompleted[7] = true;
                    this.currentStep = 7;
                    this.expandedSteps[6] = false;
                    this.expandedSteps[7] = true;
                    this.saveProgress();
                    showToast('LinkedIn connected successfully!', 'success');

                    // Clean up URL
                    window.history.replaceState({}, document.title, window.location.pathname);

                    // Recheck status
                    setTimeout(() => {
                        this.checkConnectionStatus();
                    }, 1000);
                } else if (error) {
                    let errorMessage = 'Connection failed. Please try again.';

                    switch(error) {
                        case 'access_denied':
                            errorMessage = 'You denied access. Please try again and click "Allow".';
                            break;
                        case 'oauth_failed':
                            errorMessage = 'OAuth authentication failed. Please check your credentials in Step 6.';
                            this.showLinkedInConfigHelp();
                            break;
                        case 'incomplete_data':
                            errorMessage = 'Could not retrieve your LinkedIn profile. Please try again.';
                            break;
                        case 'server_error':
                            errorMessage = 'Server error occurred. Please try again later.';
                            break;
                        case 'redirect_uri_mismatch':
                            errorMessage = 'Redirect URI mismatch error. Please go back to Step 5 and verify the exact URL in your LinkedIn app.';
                            this.showOAuthError = true;
                            this.showLinkedInConfigHelp();
                            break;
                        case 'unauthorized_scope':
                            errorMessage = 'OAuth scope error. Please go back to Step 3 and ensure you have enabled BOTH required LinkedIn Products.';
                            this.showOAuthError = true;
                            this.goBackToStep(3);
                            break;
                    }

                    showToast(errorMessage, 'error');
                    this.showOAuthError = true;

                    // Clean up URL
                    window.history.replaceState({}, document.title, window.location.pathname);
                }
            }
        },

        async testConnection() {
            this.testing = true;
            this.testResult = null;

            try {
                this.logDebug('Testing LinkedIn connection');

                const response = await api.get('/oauth-setup/linkedin/status');

                this.logDebug('Connection test response', response.data);

                if (response.data.connected && !response.data.is_expired) {
                    this.testResult = {
                        success: true,
                        message: `Perfect! Your LinkedIn account is connected and ready to use. Connected as: ${response.data.name || 'LinkedIn User'}`
                    };
                    showToast('Connection test passed!', 'success');
                } else if (response.data.connected && response.data.is_expired) {
                    this.testResult = {
                        success: false,
                        message: 'Your LinkedIn connection has expired. Please reconnect your account.'
                    };
                    this.showOAuthError = true;
                } else {
                    this.testResult = {
                        success: false,
                        message: 'No LinkedIn connection found. Please connect your account first.'
                    };
                    this.showOAuthError = true;
                }
            } catch (error) {
                logger.error('Error testing LinkedIn connection:', error);

                this.logDebug('Connection test failed', {
                    status: error.status,
                    message: error.message
                });

                this.testResult = {
                    success: false,
                    message: 'Unable to test connection. Please check your internet connection and try again.'
                };
                this.showOAuthError = true;
            } finally {
                this.testing = false;
            }
        },

        completeSetup() {
            this.setupComplete = true;
            this.celebrateCompletion();

            // Show success message and redirect to profile
            setTimeout(() => {
                showToast('LinkedIn setup complete! Redirecting to profile...', 'success');
                setTimeout(() => {
                    this.goBack();
                }, 2000);
            }, 1000);
        },

        celebrateCompletion() {
            // Create confetti effect with LinkedIn blue colors
            const colors = ['#0077B5', '#00A0DC', '#0A7A8A', '#10b981', '#3b82f6'];

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

            showToast('LinkedIn setup complete! You can now publish to LinkedIn.', 'success');
        },

        saveProgress() {
            const progress = {
                stepCompleted: this.stepCompleted,
                currentStep: this.currentStep,
                setupComplete: this.setupComplete,
                isConnected: this.isConnected,
                credentialsSaved: this.credentialsSaved,
                productsEnabled: this.productsEnabled
            };
            localStorage.setItem('linkedin_setup_progress', JSON.stringify(progress));
        },

        loadProgress() {
            const saved = localStorage.getItem('linkedin_setup_progress');
            if (saved) {
                try {
                    const progress = JSON.parse(saved);
                    this.stepCompleted = progress.stepCompleted || { 1: false, 2: false, 3: false, 4: false, 5: false, 6: false, 7: false };
                    this.currentStep = progress.currentStep || 1;
                    this.setupComplete = progress.setupComplete || false;
                    this.isConnected = progress.isConnected || false;
                    this.credentialsSaved = progress.credentialsSaved || false;
                    this.productsEnabled = progress.productsEnabled || false;

                    // Expand current step
                    if (this.currentStep <= this.totalSteps) {
                        this.expandedSteps[this.currentStep] = true;
                    }
                } catch (error) {
                    logger.error('Error loading LinkedIn setup progress:', error);
                }
            }
        },

        goBack() {
            window.location.href = 'profile.html#social-connections';
        },

        goToNewsFeed() {
            window.location.href = 'index.html';
        },

        logDebug(message, data = null) {
            if (this.debugMode) {
                const timestamp = new Date().toISOString();
                const logEntry = {
                    timestamp,
                    message,
                    data
                };

                // Store in debug info array
                this.debugInfo.push(logEntry);

                // Keep only last 50 entries
                if (this.debugInfo.length > 50) {
                    this.debugInfo.shift();
                }

                logger.debug(`[LinkedIn Setup] ${message}`, data);
            }
        },

        toggleDebugMode() {
            this.debugMode = !this.debugMode;
            if (this.debugMode) {
                showToast('Debug mode enabled. Check browser console for detailed logs.', 'info');
            } else {
                showToast('Debug mode disabled.', 'info');
                this.debugInfo = [];
            }
        },

        exportDebugLogs() {
            if (this.debugInfo.length === 0) {
                showToast('No debug logs to export. Enable debug mode first.', 'warning');
                return;
            }

            const debugData = {
                exported_at: new Date().toISOString(),
                user_agent: navigator.userAgent,
                page_url: window.location.href,
                logs: this.debugInfo
            };

            const blob = new Blob([JSON.stringify(debugData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `linkedin-setup-debug-${Date.now()}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast('Debug logs exported successfully!', 'success');
        }
    }
});

console.log('[LinkedIn Setup] Vue app configuration complete');
console.log('[LinkedIn Setup] Attempting to mount Vue app...');
app.mount('#setup-app');
console.log('[LinkedIn Setup] Vue app mounted successfully!');

} catch (error) {
    console.error('[LinkedIn Setup] FATAL ERROR during initialization:', error);
    console.error('[LinkedIn Setup] Error name:', error.name);
    console.error('[LinkedIn Setup] Error message:', error.message);
    console.error('[LinkedIn Setup] Error stack:', error.stack);

    // Show user-friendly error on page
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        max-width: 400px;
        background: #fee;
        border: 2px solid #c00;
        color: #900;
        padding: 20px;
        border-radius: 8px;
        font-family: monospace;
        font-size: 12px;
        z-index: 99999;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    `;
    errorDiv.innerHTML = `
        <strong>Initialization Error:</strong><br>
        ${error.message}<br><br>
        <small>Check console (F12) for details</small>
    `;
    document.body.appendChild(errorDiv);
}
