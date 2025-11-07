import { createApp } from 'vue'
import axios from 'axios'
import '/src/style.css'

/**
 * Social Media Connection Management
 * Handles OAuth flows, connection status, and platform integration
 */

// API Configuration
const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api`;

// Axios request interceptor to add auth token
axios.interceptors.request.use(
    config => {
        if (token) {
            config.withCredentials = true;
        }
        return config;
    },
    error => Promise.reject(error)
);

// Axios response interceptor for error handling
axios.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            // Redirect to auth page if unauthorized
            window.location.href = 'auth.html?view=login&return=' + encodeURIComponent(window.location.pathname);
        }
        return Promise.reject(error);
    }
);

createApp({
    data() {
        return {
            loading: true,
            globalError: null,
            connections: {
                linkedin: {
                    connected: false,
                    account_name: null,
                    account_id: null,
                    last_used: null,
                    expires_at: null,
                    error: null
                },
                twitter: {
                    connected: false,
                    account_name: null,
                    account_id: null,
                    last_used: null,
                    expires_at: null,
                    error: null
                },
                threads: {
                    connected: false,
                    account_name: null,
                    account_id: null,
                    last_used: null,
                    expires_at: null,
                    error: null
                }
            },
            loading: {
                linkedin: false,
                twitter: false,
                threads: false
            },
            showToast: false,
            toastMessage: '',
            toastType: 'success',
            oauthWindow: null,
            oauthCheckInterval: null
        };
    },

    computed: {
        /**
         * Count of connected platforms
         */
        connectedCount() {
            return Object.values(this.connections).filter(c => c.connected).length;
        },

        /**
         * Last activity text
         */
        lastActivityText() {
            const lastUsedDates = Object.values(this.connections)
                .filter(c => c.connected && c.last_used)
                .map(c => new Date(c.last_used));

            if (lastUsedDates.length === 0) {
                return 'Never';
            }

            const mostRecent = new Date(Math.max(...lastUsedDates));
            return this.formatRelativeTime(mostRecent);
        }
    },

    async mounted() {
        // Configure axios to send httpOnly cookies
        axios.defaults.withCredentials = true;

        // Check authentication

        // Load connection statuses
        await this.loadConnections();

        // Check if returning from OAuth callback
        this.handleOAuthCallback();

        // Listen for OAuth messages from popup
        window.addEventListener('message', this.handleOAuthMessage);
    },

    beforeUnmount() {
        // Clean up OAuth polling
        if (this.oauthCheckInterval) {
            clearInterval(this.oauthCheckInterval);
        }
        // Clean up message listener
        window.removeEventListener('message', this.handleOAuthMessage);
    },

    methods: {
        /**
         * Load connection statuses from backend
         */
        async loadConnections() {
            this.loading = true;
            this.globalError = null;

            try {
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });
                const data = response.data;

                // Update connection states
                ['linkedin', 'twitter', 'threads'].forEach(platform => {
                    if (data[platform]) {
                        this.connections[platform] = {
                            connected: data[platform].connected || false,
                            account_name: data[platform].account_name || data[platform].username || null,
                            account_id: data[platform].account_id || null,
                            last_used: data[platform].last_used || null,
                            expires_at: data[platform].expires_at || null,
                            error: null
                        };
                    }
                });

                // Store in local storage for quick access
                localStorage.setItem('social_connections', JSON.stringify(this.connections));

            } catch (error) {
                console.error('Error loading connections:', error);
                this.globalError = this.getErrorMessage(error);

                // Try to load from cache
                this.loadFromCache();
            } finally {
                this.loading = false;
            }
        },

        /**
         * Load connections from cache
         */
        loadFromCache() {
            const cached = localStorage.getItem('social_connections');
            if (cached) {
                try {
                    const data = JSON.parse(cached);
                    this.connections = { ...this.connections, ...data };
                } catch (error) {
                    console.error('Error parsing cached connections:', error);
                }
            }
        },

        /**
         * Connect to a platform via OAuth
         * @param {string} platform - Platform name (linkedin, twitter, threads)
         */
        async connectPlatform(platform) {
            this.loading[platform] = true;
            this.connections[platform].error = null;

            try {
                // Get OAuth authorization URL from backend
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });

                const authUrl = response.data.authorization_url || response.data.auth_url;

                if (!authUrl) {
                    throw new Error('No authorization URL received from server');
                }

                // Store platform in session for callback
                sessionStorage.setItem('oauth_platform', platform);
                sessionStorage.setItem('oauth_start_time', Date.now().toString());

                // Open OAuth window
                this.openOAuthWindow(authUrl, platform);

            } catch (error) {
                console.error(`Error connecting to ${platform}:`, error);
                this.connections[platform].error = this.getErrorMessage(error);
                this.showErrorToast(`Failed to connect to ${platform}`);
                this.loading[platform] = false;
            }
        },

        /**
         * Open OAuth authorization window
         * @param {string} url - OAuth URL
         * @param {string} platform - Platform name
         */
        openOAuthWindow(url, platform) {
            const width = 600;
            const height = 700;
            const left = window.screen.width / 2 - width / 2;
            const top = window.screen.height / 2 - height / 2;

            // Open popup window
            this.oauthWindow = window.open(
                url,
                `oauth_${platform}`,
                `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
            );

            // Check if popup was blocked
            if (!this.oauthWindow || this.oauthWindow.closed) {
                this.showErrorToast('Please allow popups to connect your account');
                this.loading[platform] = false;
                return;
            }

            // Focus the popup
            if (this.oauthWindow.focus) {
                this.oauthWindow.focus();
            }

            // Poll for window closure
            this.startOAuthPolling(platform);
        },

        /**
         * Start polling for OAuth window closure
         * @param {string} platform - Platform name
         */
        startOAuthPolling(platform) {
            // Clear any existing interval
            if (this.oauthCheckInterval) {
                clearInterval(this.oauthCheckInterval);
            }

            // Poll every 500ms
            this.oauthCheckInterval = setInterval(() => {
                if (!this.oauthWindow || this.oauthWindow.closed) {
                    clearInterval(this.oauthCheckInterval);
                    this.oauthCheckInterval = null;

                    // Check if OAuth was successful
                    setTimeout(() => {
                        this.checkOAuthSuccess(platform);
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
                    this.loading[platform] = false;
                    this.showErrorToast('OAuth authorization timed out');
                }
            }, 300000); // 5 minutes
        },

        /**
         * Check if OAuth was successful
         * @param {string} platform - Platform name
         */
        async checkOAuthSuccess(platform) {
            const oauthSuccess = sessionStorage.getItem('oauth_success');
            const oauthPlatform = sessionStorage.getItem('oauth_platform');

            if (oauthSuccess === 'true' && oauthPlatform === platform) {
                // Clear session storage
                sessionStorage.removeItem('oauth_success');
                sessionStorage.removeItem('oauth_platform');
                sessionStorage.removeItem('oauth_start_time');

                // Reload connections
                await this.loadConnections();
                this.showSuccessToast(`Successfully connected to ${platform}!`);
            } else {
                // Check if there was an error
                const oauthError = sessionStorage.getItem('oauth_error');
                if (oauthError) {
                    this.connections[platform].error = oauthError;
                    sessionStorage.removeItem('oauth_error');
                }
            }

            this.loading[platform] = false;
        },

        /**
         * Handle OAuth callback from popup
         */
        handleOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const code = urlParams.get('code');
            const state = urlParams.get('state');
            const error = urlParams.get('error');

            if (error) {
                sessionStorage.setItem('oauth_error', error);
                return;
            }

            if (code) {
                // OAuth successful - let the parent window handle it
                sessionStorage.setItem('oauth_success', 'true');
            }
        },

        /**
         * Handle OAuth messages from popup window
         * @param {MessageEvent} event - Message event
         */
        handleOAuthMessage(event) {
            // Verify origin
            if (event.origin !== window.location.origin) {
                return;
            }

            const { type, platform, success, error } = event.data;

            if (type === 'oauth_complete') {
                if (success) {
                    sessionStorage.setItem('oauth_success', 'true');
                    sessionStorage.setItem('oauth_platform', platform);
                    this.loadConnections();
                    this.showSuccessToast(`Successfully connected to ${platform}!`);
                } else if (error) {
                    this.connections[platform].error = error;
                    this.showErrorToast(`Failed to connect to ${platform}`);
                }
                this.loading[platform] = false;
            }
        },

        /**
         * Disconnect from a platform
         * @param {string} platform - Platform name
         */
        async disconnectPlatform(platform) {
            if (!confirm(`Are you sure you want to disconnect from ${platform}? You will need to reconnect to publish posts.`)) {
                return;
            }

            this.loading[platform] = true;
            this.connections[platform].error = null;

            try {
                await axios.delete("/api/sessions/revoke", {
                withCredentials: true
            });

                // Update connection state
                this.connections[platform] = {
                    connected: false,
                    account_name: null,
                    account_id: null,
                    last_used: null,
                    expires_at: null,
                    error: null
                };

                // Update cache
                localStorage.setItem('social_connections', JSON.stringify(this.connections));

                this.showSuccessToast(`Disconnected from ${platform}`);

            } catch (error) {
                console.error(`Error disconnecting from ${platform}:`, error);
                this.connections[platform].error = this.getErrorMessage(error);
                this.showErrorToast(`Failed to disconnect from ${platform}`);
            } finally {
                this.loading[platform] = false;
            }
        },

        /**
         * Refresh connection token
         * @param {string} platform - Platform name
         */
        async refreshConnection(platform) {
            this.loading[platform] = true;
            this.connections[platform].error = null;

            try {
                const response = await axios.post("/api/sessions/revoke", {
                withCredentials: true
            });

                // Update connection data
                if (response.data) {
                    this.connections[platform] = {
                        ...this.connections[platform],
                        expires_at: response.data.expires_at || null,
                        last_used: response.data.last_used || null,
                        error: null
                    };

                    // Update cache
                    localStorage.setItem('social_connections', JSON.stringify(this.connections));

                    this.showSuccessToast(`Refreshed ${platform} connection`);
                }

            } catch (error) {
                console.error(`Error refreshing ${platform}:`, error);
                this.connections[platform].error = this.getErrorMessage(error);
                this.showErrorToast(`Failed to refresh ${platform} connection`);
            } finally {
                this.loading[platform] = false;
            }
        },

        /**
         * Test platform connection
         * @param {string} platform - Platform name
         */
        async testConnection(platform) {
            this.loading[platform] = true;
            this.connections[platform].error = null;

            try {
                const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });

                if (response.data.success) {
                    this.showSuccessToast(`${platform} connection is working!`);
                } else {
                    throw new Error(response.data.error || 'Connection test failed');
                }

            } catch (error) {
                console.error(`Error testing ${platform}:`, error);
                this.connections[platform].error = this.getErrorMessage(error);
                this.showErrorToast(`${platform} connection test failed`);
            } finally {
                this.loading[platform] = false;
            }
        },

        /**
         * Check if token is expiring soon (within 7 days)
         * @param {string} platform - Platform name
         * @returns {boolean} True if expiring soon
         */
        isTokenExpiringSoon(platform) {
            const expiresAt = this.connections[platform].expires_at;
            if (!expiresAt) return false;

            const expiryDate = new Date(expiresAt);
            const now = new Date();
            const daysUntilExpiry = Math.ceil((expiryDate - now) / (1000 * 60 * 60 * 24));

            return daysUntilExpiry <= 7 && daysUntilExpiry > 0;
        },

        /**
         * Format date to readable string
         * @param {string|Date} date - Date to format
         * @returns {string} Formatted date
         */
        formatDate(date) {
            if (!date) return 'Never';

            const d = new Date(date);
            const now = new Date();
            const diffMs = now - d;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;

            return d.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        },

        /**
         * Format relative time
         * @param {string|Date} date - Date to format
         * @returns {string} Relative time
         */
        formatRelativeTime(date) {
            if (!date) return 'Never';

            const d = new Date(date);
            const now = new Date();
            const diffMs = now - d;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins} minutes ago`;
            if (diffHours < 24) return `${diffHours} hours ago`;
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 30) return `${diffDays} days ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
            return `${Math.floor(diffDays / 365)} years ago`;
        },

        /**
         * Show success toast
         * @param {string} message - Message to display
         */
        showSuccessToast(message) {
            this.toastMessage = message;
            this.toastType = 'success';
            this.showToast = true;

            setTimeout(() => {
                this.showToast = false;
            }, 3000);
        },

        /**
         * Show error toast
         * @param {string} message - Message to display
         */
        showErrorToast(message) {
            this.toastMessage = message;
            this.toastType = 'error';
            this.showToast = true;

            setTimeout(() => {
                this.showToast = false;
            }, 5000);
        },

        /**
         * Get error message from axios error
         * @param {Error} error - Axios error
         * @returns {string} Error message
         */
        getErrorMessage(error) {
            if (error.response?.data?.detail) {
                return error.response.data.detail;
            }
            if (error.response?.data?.message) {
                return error.response.data.message;
            }
            if (error.response?.data?.error) {
                return error.response.data.error;
            }
            if (error.message) {
                return error.message;
            }
            return 'An unexpected error occurred';
        }
    }
}).mount('#social-app');

/**
 * Export connection checking functions for use in other pages
 */
window.SocialMediaAPI = {
    /**
     * Check if all connections are loaded
     * @returns {Promise<Object>} Connection statuses
     */
    async checkConnections() {
        try {
            if (!token) {
                return { linkedin: false, twitter: false, threads: false };
            }

            const response = await axios.get("/api/sessions/active", {
                withCredentials: true
            });
            const data = response.data;

            const statuses = {
                linkedin: data.linkedin?.connected || false,
                twitter: data.twitter?.connected || false,
                threads: data.threads?.connected || false
            };

            // Cache the results
            localStorage.setItem('social_connections', JSON.stringify(statuses));

            return statuses;
        } catch (error) {
            console.error('Error checking connections:', error);

            // Try to load from cache
            const cached = localStorage.getItem('social_connections');
            if (cached) {
                try {
                    return JSON.parse(cached);
                } catch (e) {
                    return { linkedin: false, twitter: false, threads: false };
                }
            }

            return { linkedin: false, twitter: false, threads: false };
        }
    },

    /**
     * Get connected platforms list
     * @returns {Promise<string[]>} Array of connected platform names
     */
    async getConnectedPlatforms() {
        const connections = await this.checkConnections();
        return Object.keys(connections).filter(platform => connections[platform]);
    },

    /**
     * Check if any platform is connected
     * @returns {Promise<boolean>} True if at least one platform is connected
     */
    async hasAnyConnection() {
        const platforms = await this.getConnectedPlatforms();
        return platforms.length > 0;
    }
};
