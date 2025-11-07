import { createApp } from 'vue'
import api from './utils/api-client.js'
import { showToast } from './utils/toast.js'
import logger from './utils/logger.js'
import '/src/style.css'

createApp({
    data() {
        return {
            pageLoading: true,
            refreshing: false,
            showOnboarding: false,

            // Platform states
            platforms: {
                linkedin: {
                    connected: false,
                    loading: false,
                    testing: false,
                    disconnecting: false,
                    error: null,
                    username: '',
                    email: '',
                    display_name: '',
                    profile_picture: '',
                    last_post: null,
                    total_posts: 0,
                    token_expires_soon: false
                },
                twitter: {
                    connected: false,
                    loading: false,
                    testing: false,
                    disconnecting: false,
                    error: null,
                    username: '',
                    display_name: '',
                    profile_picture: '',
                    last_post: null,
                    total_posts: 0,
                    token_expires_soon: false
                },
                threads: {
                    connected: false,
                    loading: false,
                    testing: false,
                    disconnecting: false,
                    error: null,
                    username: '',
                    display_name: '',
                    profile_picture: '',
                    last_post: null,
                    total_posts: 0,
                    token_expires_soon: false
                }
            },

            // Statistics
            totalPosts: 0,
            lastPublished: null,
            successRate: 0
        };
    },

    computed: {
        connectedCount() {
            let count = 0;
            if (this.platforms.linkedin.connected) count++;
            if (this.platforms.twitter.connected) count++;
            if (this.platforms.threads.connected) count++;
            return count;
        },

        lastPublishedText() {
            if (!this.lastPublished) return 'Never';
            return this.formatRelativeTime(this.lastPublished);
        }
    },

    mounted() {
        this.init();
    },

    methods: {
        async init() {
            try {
                // Check if first time (show onboarding)
                const hasSeenOnboarding = localStorage.getItem('social_onboarding_seen');
                if (!hasSeenOnboarding) {
                    this.showOnboarding = true;
                }

                // Load platform connections
                await this.loadConnections();

                // Check for OAuth callback
                this.handleOAuthCallback();

            } catch (error) {
                logger.error('Initialization error:', error);
                showToast('Failed to load connections. Please try again.', 'error');
            } finally {
                this.pageLoading = false;
            }
        },

        async loadConnections() {
            try {
                const response = await api.get('/social-media/connections');

                logger.debug('Social media connections loaded:', response.data);

                if (response.data.success) {
                    const connections = response.data.connections;

                    // Update platform states
                    Object.keys(connections).forEach(platform => {
                        if (this.platforms[platform]) {
                            this.platforms[platform] = {
                                ...this.platforms[platform],
                                ...connections[platform],
                                connected: connections[platform].is_connected
                            };
                        }
                    });

                    // Update statistics
                    this.updateStatistics(response.data.stats);
                }
            } catch (error) {
                logger.error('Error loading connections:', error);
                // If error is 404, connections might not exist yet (new feature)
                if (error.status !== 404) {
                    throw error;
                }
            }
        },

        updateStatistics(stats) {
            if (stats) {
                this.totalPosts = stats.total_posts || 0;
                this.lastPublished = stats.last_published || null;
                this.successRate = stats.success_rate || 0;
            }
        },

        handleOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const status = urlParams.get('status');
            const platform = urlParams.get('platform');
            const error = urlParams.get('error');

            if (status && platform) {
                if (status === 'success') {
                    showToast(`Successfully connected ${this.capitalize(platform)}!`, 'success');
                    this.platforms[platform].connected = true;
                    // Reload connection data
                    this.loadConnections();
                } else if (status === 'error') {
                    showToast(error || `Failed to connect ${this.capitalize(platform)}`, 'error');
                }

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
            }
        },

        async connect(platform) {
            try {
                this.platforms[platform].loading = true;
                this.platforms[platform].error = null;

                // Get OAuth authorization URL
                const response = await api.get(`/social-media/${platform}/connect`);

                logger.debug(`${platform} connect response:`, response.data);

                if (response.data.success && response.data.auth_url) {
                    // Redirect to OAuth provider
                    window.location.href = response.data.auth_url;
                } else {
                    throw new Error('Failed to get authorization URL');
                }
            } catch (error) {
                logger.error(`Error connecting ${platform}:`, error);
                this.platforms[platform].error = `Failed to connect ${this.capitalize(platform)}. Please try again.`;
                this.platforms[platform].loading = false;
            }
        },

        async disconnect(platform) {
            if (!confirm(`Are you sure you want to disconnect ${this.capitalize(platform)}? You will need to reconnect to publish posts.`)) {
                return;
            }

            try {
                this.platforms[platform].disconnecting = true;
                this.platforms[platform].error = null;

                const response = await api.post(`/social-media/${platform}/disconnect`);

                logger.debug(`${platform} disconnect response:`, response.data);

                if (response.data.success) {
                    this.platforms[platform].connected = false;
                    this.platforms[platform].username = '';
                    this.platforms[platform].email = '';
                    this.platforms[platform].display_name = '';
                    this.platforms[platform].profile_picture = '';
                    this.platforms[platform].last_post = null;
                    this.platforms[platform].total_posts = 0;

                    showToast(`Successfully disconnected ${this.capitalize(platform)}`, 'success');
                } else {
                    throw new Error('Failed to disconnect');
                }
            } catch (error) {
                logger.error(`Error disconnecting ${platform}:`, error);
                this.platforms[platform].error = `Failed to disconnect ${this.capitalize(platform)}`;
            } finally {
                this.platforms[platform].disconnecting = false;
            }
        },

        async testConnection(platform) {
            try {
                this.platforms[platform].testing = true;
                this.platforms[platform].error = null;

                const response = await api.post(`/social-media/${platform}/test`);

                logger.debug(`${platform} test response:`, response.data);

                if (response.data.success) {
                    showToast(`${this.capitalize(platform)} connection is working correctly!`, 'success');
                } else {
                    throw new Error('Connection test failed');
                }
            } catch (error) {
                logger.error(`Error testing ${platform}:`, error);
                const errorMsg = error.message || 'Connection test failed';
                this.platforms[platform].error = errorMsg;

                // If token expired, show reconnect message
                if (errorMsg.includes('expired') || errorMsg.includes('invalid')) {
                    this.platforms[platform].token_expires_soon = true;
                }
            } finally {
                this.platforms[platform].testing = false;
            }
        },

        async refreshConnections() {
            this.refreshing = true;
            try {
                await this.loadConnections();
                showToast('Connection status refreshed', 'success');
            } catch (error) {
                logger.error('Error refreshing connections:', error);
                showToast('Failed to refresh connections', 'error');
            } finally {
                this.refreshing = false;
            }
        },

        clearError(platform) {
            this.platforms[platform].error = null;
        },

        dismissOnboarding() {
            this.showOnboarding = false;
            localStorage.setItem('social_onboarding_seen', 'true');
        },

        goBack() {
            // Check if came from settings page
            if (document.referrer.includes('index.html')) {
                window.location.href = 'index.html';
            } else if (document.referrer.includes('profile.html')) {
                window.location.href = 'profile.html';
            } else {
                window.location.href = 'index.html';
            }
        },

        capitalize(str) {
            if (!str) return '';
            return str.charAt(0).toUpperCase() + str.slice(1);
        },

        formatRelativeTime(dateString) {
            if (!dateString) return 'Never';

            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffSec = Math.floor(diffMs / 1000);
            const diffMin = Math.floor(diffSec / 60);
            const diffHour = Math.floor(diffMin / 60);
            const diffDay = Math.floor(diffHour / 24);

            if (diffSec < 60) return 'Just now';
            if (diffMin < 60) return `${diffMin}m ago`;
            if (diffHour < 24) return `${diffHour}h ago`;
            if (diffDay < 7) return `${diffDay}d ago`;
            if (diffDay < 30) return `${Math.floor(diffDay / 7)}w ago`;
            if (diffDay < 365) return `${Math.floor(diffDay / 30)}mo ago`;
            return `${Math.floor(diffDay / 365)}y ago`;
        }
    }
}).mount('#social-app');
