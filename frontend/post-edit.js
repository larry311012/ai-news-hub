import { createApp } from 'vue'
import '/src/style.css'
import api from '/utils/api-client.js'
import { showToast } from '/utils/toast.js'
import logger from '/utils/logger.js'

const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api`;

const app = createApp({
    data() {
        return {
            postId: null,
            loading: true,
            saving: false,
            error: null,
            post: {},
            originalContent: {},
            editableContent: {
                twitter: '',
                linkedin: '',
                threads: ''
            },
            selectedPlatform: 'twitter',
            selectedPlatforms: [],
            platformConnections: {
                twitter: { connected: false, status: 'checking', username: null },
                linkedin: { connected: false, status: 'checking', username: null },
                threads: { connected: false, status: 'checking', username: null },
                instagram: { connected: false, status: 'checking', username: null }
            },
            // NEW: Track if we're refreshing connection status
            refreshingConnections: false,
            platforms: [
                {
                    id: 'twitter',
                    name: 'Twitter',
                    maxLength: 280,
                    icon: '<svg fill="currentColor" viewBox="0 0 24 24"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/></svg>'
                },
                {
                    id: 'linkedin',
                    name: 'LinkedIn',
                    maxLength: 3000,
                    icon: '<svg fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>'
                },
                {
                    id: 'threads',
                    name: 'Threads',
                    maxLength: 500,
                    disabled: true, // Coming soon - in development
                    icon: '<svg fill="currentColor" viewBox="0 0 24 24"><path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.781 3.631 2.695 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 013.02.142l-.126 1.974a11.881 11.881 0 00-2.58-.123c-1.018.056-1.84.344-2.446.855-.583.493-.87 1.12-.834 1.814.036.683.388 1.217.99 1.502.539.255 1.277.354 2.101.28 1.15-.093 2.059-.535 2.702-1.315.646-.784.972-1.858.972-3.197V8.033c0-.458-.006-.916-.02-1.373l2.04-.057c.013.457.02.915.02 1.373v1.78c.598-.421 1.3-.758 2.092-.998 1.004-.304 2.085-.457 3.212-.457l.126 1.99c-.905 0-1.766.123-2.562.366-.796.243-1.47.6-2.004 1.062v1.304c.54.694.97 1.49 1.28 2.369.726 2.057.746 4.753-1.44 6.993-1.817 1.869-4.138 2.82-7.106 2.848z"/></svg>'
                },
                {
                    id: 'instagram',
                    name: 'Instagram',
                    maxLength: 2200, // Caption limit
                    disabled: true, // Coming soon - in development
                    icon: '<svg fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z"/></svg>'
                }
            ],
            // Instagram-specific data
            instagramImage: null,
            instagramImageLoading: false,
            instagramCaption: '',
            instagramHashtags: [],
            imageGenerationError: null,
            imageGenerationProgress: 0,
            imageGenerationStep: '',
            // Other state
            hasUnsavedChanges: false,
            showPublishModal: false,
            showPublishingModal: false,
            showSuccessModal: false,
            showUnsavedWarning: false,
            publishing: false,
            regenerating: false,
            publishingStatus: {},
            publishedLinks: [],
            publishedCount: 0,
            schedulePost: false,
            userName: 'User',
            userInitials: 'U',
            validationErrors: {}
        };
    },
    computed: {
        canPublish() {
            // Instagram requires an image to be generated
            if (this.selectedPlatforms.includes('instagram') && !this.instagramImage) {
                return false;
            }

            return this.selectedPlatforms.length > 0 &&
                   this.selectedPlatforms.every(p => {
                       if (p === 'instagram') {
                           return this.instagramImage !== null;
                       }
                       return this.editableContent[p]?.trim().length > 0;
                   }) &&
                   !this.hasValidationErrors();
        },
        hasConnectedPlatforms() {
            return Object.values(this.platformConnections).some(p => p.connected);
        },
        publishButtonTooltip() {
            if (this.selectedPlatforms.length === 0) {
                return 'Select at least one platform to publish';
            }
            if (this.selectedPlatforms.includes('instagram') && !this.instagramImage) {
                return 'Instagram requires an image to be generated';
            }
            const errors = this.getAllValidationErrors();
            if (errors.length > 0) {
                return `Fix errors in: ${errors.map(e => e.platform).join(', ')}`;
            }
            return '';
        }
    },
    async mounted() {

        // CRITICAL FAILSAFE: Set timeout to force loading to false after 15 seconds
        const loadingTimeout = setTimeout(() => {
            if (this.loading) {
                logger.error('CRITICAL: Loading timeout reached after 15 seconds');
                this.loading = false;
                if (!this.error) {
                    this.error = 'Loading timed out. Please refresh the page and try again. If the problem persists, check your network connection.';
                }
            }
        }, 15000);

        try {
            // Get post_id from URL
            const urlParams = new URLSearchParams(window.location.search);
            this.postId = urlParams.get('post_id');

            if (!this.postId) {
                logger.error('ERROR: No post ID provided in URL');
                this.error = 'No post ID provided. Please start from the article selection page.';
                this.loading = false;
                clearTimeout(loadingTimeout);
                return;
            }

            // Load user info (non-blocking)
            this.loadUserInfo().catch(err => {
                logger.warn('loadUserInfo failed (non-critical):', err);
            });

            // CRITICAL FIX: Load post data first (blocking), then check platform status (non-blocking)
            // This ensures post content displays even if platform status check fails
            await this.loadPost();

            // Check platform status in background (non-blocking)
            // This prevents 404 from blocking the page load
            this.checkPlatformStatus().catch(err => {
                logger.warn('checkPlatformStatus failed (non-critical):', err);
                // Set all platforms to disconnected on error
                this.platformConnections = {
                    twitter: { connected: false, status: 'disconnected', username: null },
                    linkedin: { connected: false, status: 'disconnected', username: null },
                    threads: { connected: false, status: 'disconnected', username: null },
                    instagram: { connected: false, status: 'disconnected', username: null }
                };
            });

            // NEW: Listen for window focus to auto-refresh after OAuth popup
            window.addEventListener('focus', this.handleWindowFocus);

        } catch (error) {
            logger.error('=== ERROR IN MOUNTED() ===');
            logger.error('Error type:', error.constructor.name);
            logger.error('Error message:', error.message);
            logger.error('Error stack:', error.stack);

            if (error.response) {
                logger.error('Response status:', error.response.status);
                logger.error('Response data:', error.response.data);
                logger.error('Response headers:', error.response.headers);
            } else if (error.request) {
                logger.error('No response received:', error.request);
            }

            // Set error if not already set by individual methods
            if (!this.error) {
                this.error = 'Failed to load post editor. Please try again or contact support.';
            }
        } finally {
            // CRITICAL: Always set loading to false
            this.loading = false;
            clearTimeout(loadingTimeout);
        }

        // Warn before leaving if unsaved changes
        window.addEventListener('beforeunload', this.handleBeforeUnload);
    },
    beforeUnmount() {
        window.removeEventListener('beforeunload', this.handleBeforeUnload);
        window.removeEventListener('focus', this.handleWindowFocus);
    },
    methods: {
        // NEW: Handle window focus to refresh connections after OAuth
        async handleWindowFocus() {
            // Only refresh if we have at least one disconnected platform
            const hasDisconnected = Object.values(this.platformConnections).some(p => !p.connected);
            if (hasDisconnected) {
                await this.refreshConnectionStatus();
            }
        },

        // NEW: Manually refresh connection status
        async refreshConnectionStatus() {
            this.refreshingConnections = true;

            try {
                await this.checkPlatformStatus();
                showToast('Connection status refreshed', 'success');
            } catch (error) {
                logger.error('Failed to refresh connection status:', error);
                showToast('Failed to refresh connection status', 'error');
            } finally {
                this.refreshingConnections = false;
            }
        },

        async loadUserInfo() {
            try {
                const response = await api.get(`/api/auth/me`);
                const user = response.data;
                this.userName = user.full_name || user.name || 'User';
                this.userInitials = this.getInitials(this.userName);
            } catch (error) {
                logger.warn('Error loading user info (will try localStorage):', error.message);
                // Try from localStorage as fallback
                try {
                    const storedUser = localStorage.getItem('auth_user');
                    if (storedUser) {
                        const user = JSON.parse(storedUser);
                        this.userName = user.full_name || user.name || 'User';
                        this.userInitials = this.getInitials(this.userName);
                    }
                } catch (e) {
                    logger.warn('Failed to load user from localStorage:', e.message);
                }
            }
        },

        getInitials(name) {
            if (!name) return 'U';
            const names = name.split(' ');
            if (names.length >= 2) {
                return (names[0][0] + names[names.length - 1][0]).toUpperCase();
            }
            return name.substring(0, 2).toUpperCase();
        },

        async loadPost() {
            try {
                logger.debug('=== LOADING POST ===');
                logger.debug('Post ID:', this.postId);

                // FIX: Use correct endpoint /api/posts/{post_id} instead of /api/posts/{post_id}/edit
                const response = await api.get(`/api/posts/${this.postId}`, {
                    timeout: 10000 // 10 second timeout
                });

                const data = response.data;
                logger.debug('=== POST DATA RECEIVED ===');
                logger.debug('Response data:', JSON.stringify(data, null, 2));

                this.post = data;

                // FIX: Backend returns flat structure with twitter_content, linkedin_content, etc.
                // NOT nested in a content object
                this.editableContent = {
                    twitter: data.twitter_content || '',
                    linkedin: data.linkedin_content || '',
                    threads: data.threads_content || ''
                };

                // Load Instagram data
                this.instagramCaption = data.instagram_caption || '';
                this.instagramImage = data.instagram_image_url || null;

                logger.debug('=== CONTENT LOADED ===');
                logger.debug('Twitter:', this.editableContent.twitter.substring(0, 50) + '...');
                logger.debug('LinkedIn:', this.editableContent.linkedin.substring(0, 50) + '...');
                logger.debug('Threads:', this.editableContent.threads.substring(0, 50) + '...');
                logger.debug('Instagram caption:', this.instagramCaption.substring(0, 50) + '...');
                logger.debug('Has Instagram image:', !!this.instagramImage);

                // Store original content for comparison
                this.originalContent = { ...this.editableContent };

                // Update platform connection status from platform_statuses array
                if (data.platform_statuses && Array.isArray(data.platform_statuses)) {

                    // Handle array response from GET /api/posts/{id}
                    data.platform_statuses.forEach(statusObj => {
                        const platform = statusObj.platform;

                        if (this.platformConnections[platform]) {
                            this.platformConnections[platform] = {
                                connected: statusObj.connected || false,
                                status: statusObj.connected ? 'connected' : 'disconnected',
                                username: statusObj.username || null
                            };

                            // Auto-select connected platforms (except Instagram if no image)
                            if (statusObj.connected && !this.selectedPlatforms.includes(platform)) {
                                if (platform === 'instagram' && !this.instagramImage) {} else {
                                    this.selectedPlatforms.push(platform);
                                }
                            }
                        }
                    });
                }

                // Validate all content on load
                this.validateAllPlatforms();

            } catch (error) {
                logger.error('=== loadPost() ERROR ===');
                logger.error('Error type:', error.constructor.name);
                logger.error('Error message:', error.message);

                if (error.code === 'ECONNABORTED') {
                    logger.error('Request timed out after 10 seconds');
                    this.error = 'Request timed out. Please check your connection and try again.';
                } else if (error.response) {
                    logger.error('Response error:');
                    logger.error('  Status:', error.response.status);
                    logger.error('  Status text:', error.response.statusText);
                    logger.error('  Data:', error.response.data);
                    logger.error('  Headers:', error.response.headers);

                    if (error.response.status === 401) {
                        this.error = 'Authentication failed. Redirecting to login...';
                        setTimeout(() => {
                            window.location.href = 'auth.html';
                        }, 2000);
                    } else if (error.response.status === 404) {
                        this.error = 'Post not found. You may not have access to this post.';
                    } else {
                        this.error = error.response?.data?.detail || 'Failed to load post. Please try again.';
                    }
                } else if (error.request) {
                    logger.error('No response received from server');
                    logger.error('Request:', error.request);
                    this.error = 'No response from server. Please check your connection.';
                } else {
                    logger.error('Error setting up request:', error.message);
                    this.error = 'Failed to load post. Please try again.';
                }

                // Re-throw to be caught by mounted()
                throw error;
            }
        },

        async checkPlatformStatus() {

            try {
                // If we already got platform status from loadPost, skip this
                if (this.post.platform_statuses && !this.refreshingConnections) {
                    logger.debug('Platform status already loaded from post data, skipping separate fetch');
                    return;
                }

                // CRITICAL FIX: Use correct endpoint /api/posts/{post_id}/platform-status
                // NOT /api/posts/{post_id}/connections (which doesn't exist in posts_v2)
                logger.debug('Fetching platform status from /api/posts/' + this.postId + '/platform-status');
                const response = await api.get(`/api/posts/${this.postId}/platform-status`, {
                    timeout: 10000
                });

                const statusArray = response.data;
                logger.debug('Platform status received:', statusArray);

                // FIX: Backend returns an array of PlatformConnectionStatus objects
                // Convert array to object for easier processing
                if (Array.isArray(statusArray)) {
                    statusArray.forEach(statusObj => {
                        const platform = statusObj.platform;

                        if (this.platformConnections[platform]) {
                            this.platformConnections[platform] = {
                                connected: statusObj.connected || false,
                                status: statusObj.connected ? 'connected' : 'disconnected',
                                username: statusObj.username || null,
                                // NEW: Track if needs reconnection
                                needsReconnection: statusObj.needs_reconnection || false,
                                error: statusObj.error || null
                            };

                            // Auto-select connected platforms (only on initial load, not refresh)
                            if (statusObj.connected && !this.selectedPlatforms.includes(platform) && !this.refreshingConnections) {
                                if (platform === 'instagram' && !this.instagramImage) {} else {
                                    this.selectedPlatforms.push(platform);
                                }
                            }
                        }
                    });
                } else {
                    // Fallback: handle dictionary format (backwards compatibility)
                    Object.keys(statusArray).forEach(platform => {
                        if (this.platformConnections[platform]) {
                            const platformData = statusArray[platform];
                            this.platformConnections[platform] = {
                                connected: platformData.connected || false,
                                status: platformData.connected ? 'connected' : 'disconnected',
                                username: platformData.username || null,
                                needsReconnection: platformData.needs_reconnection || false,
                                error: platformData.error || null
                            };

                            // Auto-select connected platforms (only on initial load, not refresh)
                            if (platformData.connected && !this.selectedPlatforms.includes(platform) && !this.refreshingConnections) {
                                if (platform === 'instagram' && !this.instagramImage) {} else {
                                    this.selectedPlatforms.push(platform);
                                }
                            }
                        }
                    });
                }

                logger.debug('Platform connections updated:', this.platformConnections);

            } catch (error) {
                logger.error('=== checkPlatformStatus() ERROR ===');
                logger.error('Error message:', error.message);

                // Handle specific errors
                if (error.response) {
                    logger.error('Response status:', error.response.status);
                    logger.error('Response data:', error.response.data);

                    if (error.response.status === 404) {
                        logger.warn('Platform status endpoint returned 404 - endpoint may not exist or post not found');
                        // Don't show error - just set disconnected state
                    } else if (error.response.status === 401) {
                        logger.error('Not authenticated - redirecting to login');
                        window.location.href = 'auth.html';
                        return;
                    } else {
                        logger.error('Unexpected error from platform status endpoint:', error.response.status);
                    }
                } else {
                    logger.error('Network or other error:', error.message);
                }

                // Set all platforms to disconnected state (force Vue reactivity)
                // This is non-critical, so we just default to disconnected
                this.platformConnections = {
                    twitter: { connected: false, status: 'disconnected', username: null },
                    linkedin: { connected: false, status: 'disconnected', username: null },
                    threads: { connected: false, status: 'disconnected', username: null },
                    instagram: { connected: false, status: 'disconnected', username: null }
                };

                // Re-throw to let caller handle
                throw error;
            }
        },

        handleContentChange() {
            // Check if content has changed
            const hasChanges = Object.keys(this.editableContent).some(platform => {
                return this.editableContent[platform] !== this.originalContent[platform];
            });

            if (hasChanges !== this.hasUnsavedChanges) {
                this.hasUnsavedChanges = hasChanges;

                // Show warning after 5 seconds of unsaved changes
                if (hasChanges) {
                    setTimeout(() => {
                        if (this.hasUnsavedChanges) {
                            this.showUnsavedWarning = true;
                        }
                    }, 5000);
                }
            }

            // Validate all platforms when content changes
            this.validateAllPlatforms();
        },

        // Instagram-specific methods
        async generateInstagramImage() {
            this.instagramImageLoading = true;
            this.imageGenerationError = null;
            this.imageGenerationProgress = 0;
            this.imageGenerationStep = 'Starting image generation...';

            try {
                // Step 1: Start image generation
                const startResponse = await api.post(`/api/posts/${this.postId}/generate-instagram-image`, {}, {
                    timeout: 10000 }); // 10 second timeout for starting the job

                const { job_id, estimated_seconds } = startResponse.data;

                // Step 2: Poll for completion (default to 45s if backend doesn't specify)
                const imageUrl = await this.pollImageStatus(job_id, estimated_seconds || 45);

                // Step 3: Update UI
                this.instagramImage = imageUrl;
                this.hasUnsavedChanges = true;
                this.imageGenerationProgress = 100;
                this.imageGenerationStep = 'Image generated successfully!';
                showToast('Instagram image generated successfully!', 'success');

            } catch (error) {
                logger.error('Error generating Instagram image:', error);
                this.handleImageGenerationError(error);
            } finally {
                this.instagramImageLoading = false;
            }
        },

        async pollImageStatus(jobId, maxSeconds) {
            const maxAttempts = maxSeconds * 2; // Poll every 500ms
            const pollInterval = 500;

            for (let attempt = 0; attempt < maxAttempts; attempt++) {
                await new Promise(resolve => setTimeout(resolve, pollInterval));

                try {
                    const statusResponse = await api.get(`/api/posts/${this.postId}/instagram-image/status?job_id=${jobId}`, {
                    timeout: 5000 });

                    const { status, progress, image_url, current_step, error } = statusResponse.data;

                    // Update progress indicators
                    if (progress !== undefined) {
                        this.imageGenerationProgress = progress;
                    }
                    if (current_step) {
                        this.imageGenerationStep = current_step;
                    }

                    if (status === 'completed' && image_url) {
                        return image_url;
                    } else if (status === 'failed') {
                        throw new Error(error || 'Image generation failed');
                    }

                } catch (error) {
                    // If status endpoint fails, continue polling (might be temporary)
                    if (attempt === maxAttempts - 1) {
                        throw error;
                    }
                }
            }

            throw new Error('Image generation timed out after ' + maxSeconds + ' seconds');
        },

        handleImageGenerationError(error) {
            let errorMessage = 'Failed to generate image.';
            let actionMessage = 'Please try again.';

            if (error.response) {
                switch (error.response.status) {
                    case 404:
                        errorMessage = 'Post not found.';
                        actionMessage = 'Please reload the page.';
                        break;
                    case 429:
                        errorMessage = 'Daily image generation limit reached.';
                        actionMessage = 'Try again tomorrow or upgrade your plan.';
                        break;
                    case 500:
                        errorMessage = 'Server error occurred.';
                        actionMessage = 'Please try again in a few minutes.';
                        break;
                    default:
                        errorMessage = error.response.data?.detail || error.response.data?.message || errorMessage;
                }
            } else if (error.code === 'ECONNABORTED') {
                errorMessage = 'Request timed out.';
                actionMessage = 'Check your internet connection and try again.';
            } else if (error.message) {
                errorMessage = error.message;
            }

            this.imageGenerationError = `${errorMessage} ${actionMessage}`;
            showToast(this.imageGenerationError, 'error');
        },

        async regenerateInstagramImage() {
            if (!confirm('This will generate a new image. The current image will be replaced. Continue?')) {
                return;
            }

            this.instagramImageLoading = true;
            this.imageGenerationError = null;
            this.imageGenerationProgress = 0;
            this.imageGenerationStep = 'Starting image regeneration...';

            try {
                // Step 1: Start regeneration
                const startResponse = await api.post(`/api/posts/${this.postId}/regenerate-instagram-image`, {}, {
                    timeout: 10000 });

                const { job_id, estimated_seconds } = startResponse.data;

                // Step 2: Poll for completion (default to 45s if backend doesn't specify)
                const imageUrl = await this.pollImageStatus(job_id, estimated_seconds || 45);

                // Step 3: Update UI
                this.instagramImage = imageUrl;
                this.hasUnsavedChanges = true;
                this.imageGenerationProgress = 100;
                this.imageGenerationStep = 'Image regenerated successfully!';
                showToast('Instagram image regenerated successfully!', 'success');

            } catch (error) {
                logger.error('Error regenerating Instagram image:', error);
                this.handleImageGenerationError(error);
            } finally {
                this.instagramImageLoading = false;
            }
        },

        async uploadImage(event) {
            const file = event.target.files[0];
            if (!file) return;

            // Validate file type
            if (!file.type.startsWith('image/')) {
                showToast('Please upload an image file', 'error');
                return;
            }

            // Validate file size (max 10MB)
            if (file.size > 10 * 1024 * 1024) {
                showToast('Image must be less than 10MB', 'error');
                return;
            }

            this.instagramImageLoading = true;
            this.imageGenerationError = null;

            try {
                // Use api-client's uploadFile method
                const response = await api.uploadFile(
                    `/api/posts/${this.postId}/upload-instagram-image`,
                    file,
                    (progress) => {
                        this.imageGenerationProgress = progress;
                    },
                    { timeout: 30000 }
                );

                // Handle response
                if (typeof response.data === 'string') {
                    this.instagramImage = response.data;
                } else if (response.data.image_url || response.data.url) {
                    this.instagramImage = response.data.image_url || response.data.url;
                } else {
                    // Use local preview if backend doesn't return URL immediately
                    this.instagramImage = URL.createObjectURL(file);
                }

                this.hasUnsavedChanges = true;
                showToast('Image uploaded successfully!', 'success');

                // Clear the file input
                event.target.value = '';

            } catch (error) {
                logger.error('Error uploading image:', error);

                this.imageGenerationError = error.response?.data?.detail ||
                                           error.response?.data?.message ||
                                           'Failed to upload image. Please try again.';

                showToast(this.imageGenerationError, 'error');

                // Clear the file input
                event.target.value = '';
            } finally {
                this.instagramImageLoading = false;
            }
        },

        downloadImage() {
            if (!this.instagramImage) {
                showToast('No image to download', 'error');
                return;
            }

            // Create temporary link and trigger download
            const link = document.createElement('a');
            link.href = this.instagramImage;
            link.download = `instagram-post-${this.postId}.jpg`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            showToast('Image download started!', 'success');
        },

        imageLoadSuccess() {},

        imageLoadError(event) {
            logger.error('Failed to load Instagram image:', event);
            this.imageGenerationError = 'Failed to load image. Please try regenerating.';
        },

        handleInstagramCaptionChange() {
            this.hasUnsavedChanges = true;
        },

        addInstagramHashtags() {
            const hashtags = '\n\n#AI #TechNews #Innovation #Technology #FutureTech';

            if (this.instagramCaption && !this.instagramCaption.endsWith('\n\n')) {
                this.instagramCaption += '\n\n';
            }

            this.instagramCaption += hashtags;
            this.hasUnsavedChanges = true;
        },

        async saveInstagramCaption() {
            // This is automatically saved when saveDraft is called
        },

        // Validation methods
        validateAllPlatforms() {
            this.validationErrors = {};

            this.platforms.forEach(platform => {
                const validation = this.validatePlatform(platform.id);
                if (validation.hasError || validation.hasWarning) {
                    this.validationErrors[platform.id] = validation;
                }
            });
        },

        validatePlatform(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            if (!platform) {
                return { hasError: false, hasWarning: false };
            }

            // Instagram validation is different (image required)
            if (platformId === 'instagram') {
                const validation = {
                    hasError: false,
                    hasWarning: false,
                    isEmpty: !this.instagramImage,
                    errorMessage: null,
                    warningMessage: null
                };

                if (!this.instagramImage && this.selectedPlatforms.includes('instagram')) {
                    validation.hasError = true;
                    validation.errorMessage = 'Image required for Instagram';
                }

                return validation;
            }

            const content = this.editableContent[platformId] || '';
            const length = content.length;
            const maxLength = platform.maxLength;
            const percentage = (length / maxLength) * 100;

            const validation = {
                length,
                maxLength,
                percentage,
                hasError: false,
                hasWarning: false,
                isEmpty: content.trim().length === 0,
                errorMessage: null,
                warningMessage: null
            };

            // Check for errors (exceeds limit)
            if (length > maxLength) {
                validation.hasError = true;
                const excess = length - maxLength;
                validation.errorMessage = `Content is ${excess} character${excess !== 1 ? 's' : ''} too long (${length}/${maxLength})`;
            }
            // Check for warnings (near limit)
            else if (percentage >= 90 && length > 0) {
                validation.hasWarning = true;
                const remaining = maxLength - length;
                validation.warningMessage = `${remaining} character${remaining !== 1 ? 's' : ''} remaining`;
            }

            return validation;
        },

        getPlatformValidationState(platformId) {
            const validation = this.validatePlatform(platformId);

            if (validation.hasError) return 'error';
            if (validation.hasWarning) return 'warning';
            if (platformId === 'instagram' && this.instagramImage) return 'valid';
            if (validation.length > 0) return 'valid';
            return 'empty';
        },

        getPlatformValidationIcon(platformId) {
            const state = this.getPlatformValidationState(platformId);

            switch (state) {
                case 'error':
                    return '<svg class="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>';
                case 'warning':
                    return '<svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>';
                case 'valid':
                    return '<svg class="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>';
                default:
                    return '';
            }
        },

        getAllValidationErrors() {
            const errors = [];

            this.platforms.forEach(platform => {
                const validation = this.validatePlatform(platform.id);
                if (validation.hasError) {
                    errors.push({
                        platform: platform.name,
                        platformId: platform.id,
                        message: validation.errorMessage
                    });
                }
            });

            return errors;
        },

        hasValidationErrors() {
            // Check each selected platform for validation errors
            for (const platformId of this.selectedPlatforms) {
                if (platformId === 'instagram') {
                    if (!this.instagramImage) {
                        return true;
                    }
                    continue;
                }

                const platform = this.platforms.find(p => p.id === platformId);
                if (!platform) continue;

                const content = this.editableContent[platformId] || '';

                // Check if content exceeds max length
                if (content.length > platform.maxLength) {
                    return true;
                }
            }
            return false;
        },

        getContentValidationClass(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            if (!platform) return '';

            const content = this.editableContent[platformId] || '';
            const length = content.length;
            const maxLength = platform.maxLength;

            if (length === 0) return 'text-gray-500';
            if (length > maxLength) return 'text-red-600 font-semibold';
            if (length > maxLength * 0.9) return 'text-yellow-600 font-semibold';
            return 'text-green-600';
        },

        // Switch to first tab with error
        switchToErrorTab() {
            const errors = this.getAllValidationErrors();
            if (errors.length > 0) {
                this.selectedPlatform = errors[0].platformId;

                // Scroll to the editor
                this.$nextTick(() => {
                    const editor = document.getElementById(`editor-${errors[0].platformId}`);
                    if (editor) {
                        editor.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        editor.focus();
                    }
                });
            }
        },

        handleBeforeUnload(e) {
            if (this.hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        },

        async saveDraft() {
            this.saving = true;
            try {
                // Prepare payload
                const payload = {
                    twitter_content: this.editableContent.twitter,
                    linkedin_content: this.editableContent.linkedin,
                    threads_content: this.editableContent.threads,
                    instagram_caption: this.instagramCaption,
                    status: 'draft'
                };

                // Use PATCH endpoint to update post content
                await api.patch(`/api/posts/${this.postId}`, payload);

                // Update original content
                this.originalContent = { ...this.editableContent };
                this.hasUnsavedChanges = false;
                this.showUnsavedWarning = false;

                showToast('Draft saved successfully!', 'success');

            } catch (error) {
                logger.error('Error saving draft:', error);

                // Extract validation error details
                const errorMessage = this.extractValidationError(error);
                showToast(errorMessage, 'error');

                // Switch to problematic tab if validation error
                this.switchToErrorTab();
            } finally {
                this.saving = false;
            }
        },

        extractValidationError(error) {
            // Handle Pydantic validation errors (422)
            if (error.response?.status === 422 && error.response?.data?.detail) {
                const details = error.response.data.detail;

                // If it's an array of Pydantic errors
                if (Array.isArray(details)) {
                    const errors = details.map(err => {
                        const field = err.loc ? err.loc[err.loc.length - 1] : 'content';
                        const message = err.msg || 'Validation error';
                        return `${field}: ${message}`;
                    });
                    return errors.join('; ');
                }

                return details;
            }

            return error.response?.data?.detail ||
                   error.response?.data?.message ||
                   'Failed to save draft';
        },

        openPublishModal() {
            // Check if any platforms are selected
            if (this.selectedPlatforms.length === 0) {
                showToast('Please select at least one platform', 'error');
                return;
            }

            // Enhanced validation with tab switching
            const errors = [];
            for (const platformId of this.selectedPlatforms) {
                if (platformId === 'instagram') {
                    if (!this.instagramImage) {
                        errors.push('Instagram: Image required');
                    }
                    continue;
                }

                const platform = this.platforms.find(p => p.id === platformId);
                if (!platform) continue;

                const content = this.editableContent[platformId] || '';

                if (content.trim().length === 0) {
                    errors.push(`${platform.name}: Content is empty`);
                }

                if (content.length > platform.maxLength) {
                    const excess = content.length - platform.maxLength;
                    errors.push(`${platform.name}: Content is ${excess} characters too long (${content.length}/${platform.maxLength})`);
                }
            }

            if (errors.length > 0) {
                // FIX: Use safe text rendering instead of innerHTML
                // Display errors one by one using multiple toasts
                errors.forEach((error, index) => {
                    setTimeout(() => {
                        showToast(error, 'error');
                    }, index * 300); // Stagger the toast notifications
                });

                // Switch to first problematic tab
                this.switchToErrorTab();
                return;
            }

            this.showPublishModal = true;
        },

        closePublishModal() {
            this.showPublishModal = false;
        },

        async publishPosts() {

            this.publishing = true;
            this.showPublishModal = false;
            this.showPublishingModal = true;

            // Initialize publishing status
            this.publishingStatus = {};
            this.selectedPlatforms.forEach(platform => {
                this.publishingStatus[platform] = 'publishing';
            });

            try {
                // Log content for each platform
                logger.debug('Publishing to platforms:', this.selectedPlatforms);

                // First save the content (including Instagram data)
                const savePayload = {
                    twitter_content: this.editableContent.twitter,
                    linkedin_content: this.editableContent.linkedin,
                    threads_content: this.editableContent.threads,
                    instagram_caption: this.instagramCaption
                };

                await api.patch(`/api/posts/${this.postId}`, savePayload);

                // Then publish using POST /api/posts/publish
                const publishPayload = {
                    post_id: this.postId,
                    platforms: this.selectedPlatforms
                };

                const response = await api.post(`/api/posts/publish`, publishPayload);

                const results = response.data;

                // Update publishing status
                this.publishedCount = 0;
                this.publishedLinks = [];

                // Handle response format - could be results object or success message
                if (results.message || results.success) {
                    // All platforms succeeded
                    this.selectedPlatforms.forEach(platform => {
                        this.publishingStatus[platform] = 'success';
                        this.publishedCount++;
                    });
                } else if (results.results) {
                    logger.debug('Processing individual platform results');

                    // Individual platform results
                    Object.keys(results.results).forEach(platform => {
                        const result = results.results[platform];

                        if (result.success || result.status === 'success') {
                            this.publishingStatus[platform] = 'success';
                            this.publishedCount++;

                            if (result.url || result.post_url || result.platform_url) {
                                const platformUrl = result.url || result.post_url || result.platform_url;
                                this.publishedLinks.push({
                                    platform: this.getPlatformName(platform),
                                    url: platformUrl
                                });
                            } else {
                                logger.debug(`${platform}: Success but no URL provided`);
                            }
                        } else {
                            this.publishingStatus[platform] = 'error';
                            logger.error(`${platform}: FAILED -`, result.error || 'Unknown error');
                        }
                    });
                } else if (results.errors) {
                    logger.error('Errors detected in response:', results.errors);
                    Object.keys(results.errors).forEach(platform => {
                        logger.error(`${platform}: ERROR -`, results.errors[platform]);
                        this.publishingStatus[platform] = 'error';
                    });
                }

                // Wait a moment to show results
                setTimeout(() => {
                    this.showPublishingModal = false;
                    this.showSuccessModal = true;

                    // Update original content to prevent unsaved warning
                    this.originalContent = { ...this.editableContent };
                    this.hasUnsavedChanges = false;
                }, 2000);

            } catch (error) {
                logger.error('=== PUBLISH ERROR ===');
                logger.error('Error type:', error.constructor.name);
                logger.error('Error message:', error.message);

                if (error.response) {
                    logger.error('Response status:', error.response.status);
                    logger.error('Response data:', error.response.data);
                    logger.error('Response headers:', error.response.headers);
                } else if (error.request) {
                    logger.error('No response received');
                    logger.error('Request:', error.request);
                } else {
                    logger.error('Error setup:', error.message);
                }

                this.showPublishingModal = false;

                // Extract detailed error message
                const errorMessage = this.extractValidationError(error);
                showToast(errorMessage, 'error');

                // Switch to problematic tab
                this.switchToErrorTab();

                // Mark all as error
                this.selectedPlatforms.forEach(platform => {
                    this.publishingStatus[platform] = 'error';
                    logger.error(`${platform}: Marked as error due to exception`);
                });
            } finally {
                this.publishing = false;
            }
        },

        closeSuccessModal() {
            this.showSuccessModal = false;
        },

        viewHistory() {
            // Navigate to index.html with history view
            window.location.href = 'index.html?view=history';
        },

        async regenerateContent() {
            if (!confirm('This will regenerate content for all platforms. Current changes will be lost. Continue?')) {
                return;
            }

            this.regenerating = true;
            try {
                // Call regenerate endpoint if available, otherwise fallback to re-generating
                const response = await api.post(`/api/posts/${this.postId}/regenerate`);
                const data = response.data;

                // Update content
                this.editableContent = {
                    twitter: data.content?.twitter || '',
                    linkedin: data.content?.linkedin || '',
                    threads: data.content?.threads || ''
                };

                this.originalContent = { ...this.editableContent };
                this.hasUnsavedChanges = false;

                // Validate regenerated content
                this.validateAllPlatforms();

                showToast('Content regenerated successfully!', 'success');

            } catch (error) {
                logger.error('Error regenerating content:', error);
                showToast(error.response?.data?.detail || 'Failed to regenerate content', 'error');
            } finally {
                this.regenerating = false;
            }
        },

        async connectPlatform(platformId) {
            // Redirect to profile page to connect platform
            window.location.href = `profile.html#social-connections`;
        },

        getPlatformName(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            return platform ? platform.name : platformId;
        },

        copyToClipboard() {
            let content;

            if (this.selectedPlatform === 'instagram') {
                content = this.instagramCaption;
            } else {
                content = this.editableContent[this.selectedPlatform];
            }

            if (!content) {
                showToast('No content to copy', 'error');
                return;
            }

            navigator.clipboard.writeText(content).then(() => {
                showToast('Copied to clipboard!', 'success');
            }).catch(() => {
                showToast('Failed to copy to clipboard', 'error');
            });
        },

        formatContent(platformId, format) {
            // Basic formatting helpers
            const textarea = document.getElementById(`editor-${platformId}`);
            if (!textarea) return;

            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const selectedText = this.editableContent[platformId].substring(start, end);

            if (!selectedText) {
                showToast('Please select text to format', 'error');
                return;
            }

            let formattedText = selectedText;
            if (format === 'bold') {
                formattedText = `**${selectedText}**`;
            }

            const newContent = this.editableContent[platformId].substring(0, start) +
                             formattedText +
                             this.editableContent[platformId].substring(end);

            this.editableContent[platformId] = newContent;
            this.handleContentChange();
        },

        addHashtags(platformId) {
            const commonHashtags = '#AI #TechNews #Innovation';
            const currentContent = this.editableContent[platformId];

            if (currentContent && !currentContent.endsWith('\n\n')) {
                this.editableContent[platformId] += '\n\n';
            }

            this.editableContent[platformId] += commonHashtags;
            this.handleContentChange();
        },

        goBack() {
            if (this.hasUnsavedChanges) {
                if (confirm('You have unsaved changes. Are you sure you want to leave?')) {
                    window.location.href = 'index.html';
                }
            } else {
                window.location.href = 'index.html';
            }
        }
    }
});

app.mount('#edit-app');
