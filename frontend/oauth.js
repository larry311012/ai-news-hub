import { createApp } from 'vue'
import api from './utils/api-client.js'
import { showToast } from './utils/toast.js'
import logger from './utils/logger.js'
import '/src/style.css'

/**
 * OAuth Callback Handler
 * Handles OAuth redirect callbacks and token processing
 */

createApp({
    data() {
        return {
            loading: true,
            error: null,
            provider: null,
            message: 'Processing authentication...'
        };
    },
    mounted() {
        this.handleOAuthCallback();
    },
    methods: {
        async handleOAuthCallback() {
            try {
                // Get URL parameters
                const params = new URLSearchParams(window.location.search);
                const token = params.get('token');
                const error = params.get('error');
                const provider = params.get('provider');
                const needsLinking = params.get('needs_linking') === 'true';
                const email = params.get('email');

                this.provider = provider;

                logger.debug('OAuth callback parameters:', { provider, hasToken: !!token, error, needsLinking });

                // Handle error from OAuth provider
                if (error) {
                    this.handleError(error);
                    return;
                }

                // Handle account linking scenario
                if (needsLinking && email) {
                    this.handleAccountLinking(email, provider);
                    return;
                }

                // Handle successful authentication
                if (token) {
                    await this.handleSuccess(token);
                    return;
                }

                // No valid parameters
                this.error = 'Invalid authentication response. Please try again.';
                this.loading = false;

            } catch (err) {
                logger.error('OAuth callback error:', err);
                this.error = 'An unexpected error occurred. Please try again.';
                this.loading = false;
            }
        },

        async handleSuccess(token) {
            this.message = 'Authentication successful! Redirecting...';

            // Store token
            localStorage.setItem('auth_token', token);

            // Parse token to get user info
            const payload = this.parseJWT(token);
            if (payload) {
                logger.debug('JWT payload parsed:', payload);

                // Fetch user profile
                try {
                    const response = await api.get('/auth/profile');

                    logger.debug('User profile fetched:', response.data);

                    localStorage.setItem('auth_user', JSON.stringify(response.data));
                } catch (error) {
                    logger.error('Error fetching user profile:', error);
                }
            }

            // Show success message
            showToast(`Successfully logged in with ${this.provider}!`, 'success');

            // Redirect to main app after short delay
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1500);
        },

        handleError(error) {
            const errorMessages = {
                'access_denied': 'You denied access to your account. Please try again if this was a mistake.',
                'invalid_credentials': 'Invalid credentials provided by the OAuth provider.',
                'email_required': 'Email permission is required to continue. Please grant access and try again.',
                'server_error': 'A server error occurred. Please try again later.',
                'unknown_error': 'An unknown error occurred. Please try again.'
            };

            this.error = errorMessages[error] || errorMessages['unknown_error'];
            this.loading = false;

            logger.error('OAuth error:', error);

            // Show error toast
            showToast(this.error, 'error', 5000);
        },

        handleAccountLinking(email, provider) {
            this.loading = false;

            logger.debug('Account linking required:', { email, provider });

            // Store linking info in session storage
            sessionStorage.setItem('oauth_linking', JSON.stringify({
                email,
                provider,
                timestamp: Date.now()
            }));

            // Redirect to auth page with linking prompt
            this.message = 'An account with this email already exists. Redirecting to link accounts...';

            setTimeout(() => {
                window.location.href = `auth.html?linking=true&email=${encodeURIComponent(email)}&provider=${provider}`;
            }, 2000);
        },

        parseJWT(token) {
            try {
                const base64Url = token.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(
                    atob(base64)
                        .split('')
                        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                        .join('')
                );
                return JSON.parse(jsonPayload);
            } catch (e) {
                logger.error('Error parsing JWT:', e);
                return null;
            }
        },

        retryAuth() {
            window.location.href = 'auth.html';
        },

        goToLogin() {
            window.location.href = 'auth.html';
        }
    }
}).mount('#oauth-app');
