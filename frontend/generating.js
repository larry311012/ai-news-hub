import { showToast } from './utils/toast.js';
import api from './utils/api-client.js';
import logger from './utils/logger.js';
import { createApp } from 'vue'
import '/src/style.css'
import { ErrorDisplay } from './components/ErrorDisplay.js';

const app = createApp({
    components: {
        ErrorDisplay
    },
    data() {
        return {
            jobId: null,
            progress: 0,
            currentStep: 'Initializing...',
            headingText: 'Generating Your Posts',
            subheadingText: 'Creating engaging content for your selected platforms...',
            platformStatus: {
                twitter: { status: 'pending', message: 'Waiting to start...' },
                linkedin: { status: 'pending', message: 'Waiting to start...' },
                threads: { status: 'pending', message: 'Waiting to start...' },
                instagram: { status: 'pending', message: 'Waiting to start...' }
            },
            error: null,
            errorDetails: null, // NEW: Store structured error data
            showTimeoutWarning: false,
            isComplete: false,
            pollInterval: null,
            startTime: null,
            timeoutWarningTimer: null,
            maxTimeout: 300000, // 5 minutes (allows time for all 4 platforms)
            pollDelay: 500, // Poll every 500ms
            // Enhanced UX features
            encouragingMessages: [
                'Analyzing article content...',
                'Crafting the perfect tweet...',
                'Creating engaging LinkedIn post...',
                'Writing compelling Threads content...',
                'Crafting Instagram caption...',
                'Adding perfect emojis and hashtags...',
                'Optimizing for maximum engagement...',
                'Adding professional polish...',
                'Almost there...',
                'Fine-tuning the details...',
                'Generating high-quality content...',
                'Making it shine...',
                'Polishing Instagram aesthetics...',
                'Creating scroll-stopping captions...'
            ],
            messageIndex: 0,
            messageInterval: null
        };
    },
    async mounted() {
        // Get parameters from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.jobId = urlParams.get('job_id');
        const articleIds = urlParams.get('article_ids');

        // If we have article_ids but no job_id, we need to start generation
        if (!this.jobId && articleIds) {
            this.currentStep = 'Starting generation...';
            await this.startGeneration(articleIds);
            return;
        }

        if (!this.jobId) {
            this.handleError('No generation job ID provided. Please start from the article selection page.');
            return;
        }

        // Start polling
        this.startTime = Date.now();
        this.startPolling();

        // Cycle through encouraging messages
        this.startMessageCycle();

        // Set timeout warning (show after 90 seconds)
        this.timeoutWarningTimer = setTimeout(() => {
            if (!this.isComplete && !this.error) {
                this.showTimeoutWarning = true;
            }
        }, 90000);

        // Set maximum timeout (fail after 5 minutes)
        setTimeout(() => {
            if (!this.isComplete && !this.error) {
                this.handleError('Generation timed out. Please try again or check your API key configuration.', {
                    type: 'timeout',
                    title: 'Request Timed Out',
                    message: 'The AI took too long to respond. This may indicate network issues or API problems.'
                });
            }
        }, this.maxTimeout);
    },
    beforeUnmount() {
        this.stopPolling();
        this.stopMessageCycle();
        if (this.timeoutWarningTimer) {
            clearTimeout(this.timeoutWarningTimer);
        }
    },
    methods: {
        startPolling() {
            // Poll immediately
            this.pollStatus();

            // Then poll every 500ms
            this.pollInterval = setInterval(() => {
                this.pollStatus();
            }, this.pollDelay);
        },

        stopPolling() {
            if (this.pollInterval) {
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        },

        startMessageCycle() {
            // Change encouraging message every 3 seconds
            this.messageInterval = setInterval(() => {
                if (!this.isComplete && !this.error) {
                    this.messageIndex = (this.messageIndex + 1) % this.encouragingMessages.length;
                    this.currentStep = this.encouragingMessages[this.messageIndex];
                }
            }, 3000);
        },

        stopMessageCycle() {
            if (this.messageInterval) {
                clearInterval(this.messageInterval);
                this.messageInterval = null;
            }
        },

        async startGeneration(articleIdsString) {
            try {
                // Parse article IDs
                const articleIds = articleIdsString.split(',').map(id => parseInt(id.trim()));

                this.currentStep = 'Initiating post generation...';

                // Call API to start generation - include Instagram in platforms array
                const response = await api.post('/api/posts/generate', {
                    article_ids: articleIds,
                    platforms: ['twitter', 'linkedin', 'threads', 'instagram']
                });

                // Get job ID from response
                this.jobId = response.data.post_id;
                this.currentStep = 'Generation started successfully!';

                logger.debug('Generation started with job ID:', this.jobId);

                // Now start polling for progress
                this.startTime = Date.now();
                this.startPolling();
                this.startMessageCycle();

                // Set timeout warning (show after 90 seconds)
                this.timeoutWarningTimer = setTimeout(() => {
                    if (!this.isComplete && !this.error) {
                        this.showTimeoutWarning = true;
                    }
                }, 90000);

                // Set maximum timeout (fail after 5 minutes)
                setTimeout(() => {
                    if (!this.isComplete && !this.error) {
                        this.handleError('Generation timed out. Please try again or check your API key configuration.', {
                            type: 'timeout',
                            title: 'Request Timed Out',
                            message: 'The AI took too long to respond. This may indicate network issues or API problems.'
                        });
                    }
                }, this.maxTimeout);

            } catch (error) {
                logger.error('Error starting generation:', error);

                // Parse structured error from backend
                const errorDetails = this.parseApiError(error);
                this.handleError(errorDetails.message, errorDetails);
            }
        },

        /**
         * Parse API error response into structured error object
         */
        parseApiError(error) {
            // Check if error has response data with structured error
            if (error.response && error.response.data) {
                const data = error.response.data;

                // Backend may return structured error with type, message, provider, action
                if (data.error && typeof data.error === 'object') {
                    return {
                        type: data.error.type || 'unknown',
                        title: this.getErrorTitle(data.error.type),
                        message: data.error.message || 'An error occurred',
                        provider: data.error.provider || null,
                        action: data.error.action || null,
                        rawError: data.error
                    };
                }

                // Backend may return simple error message
                if (data.detail || data.message) {
                    const errorMsg = data.detail || data.message;
                    return this.parseErrorMessage(errorMsg);
                }
            }

            // Check HTTP status codes
            if (error.status) {
                switch (error.status) {
                    case 400:
                        return this.parseErrorMessage(error.message || 'Invalid request');
                    case 401:
                        return {
                            type: 'auth_error',
                            title: 'Authentication Required',
                            message: 'Your session has expired. Please log in again.',
                            action: 'Redirecting to login...'
                        };
                    case 429:
                        return {
                            type: 'rate_limit',
                            title: 'Rate Limit Exceeded',
                            message: 'Too many requests. Please wait a moment before trying again.',
                        };
                    case 500:
                    case 502:
                    case 503:
                        return {
                            type: 'service_unavailable',
                            title: 'Service Unavailable',
                            message: 'The server is experiencing issues. Please try again in a moment.',
                        };
                }
            }

            // Check for network errors
            if (error.message && (
                error.message.includes('Failed to fetch') ||
                error.message.includes('NetworkError') ||
                error.message.includes('Network')
            )) {
                return {
                    type: 'network_error',
                    title: 'Network Error',
                    message: 'Unable to connect to the server. Please check your internet connection.',
                };
            }

            // Default error
            return this.parseErrorMessage(error.message || 'An unexpected error occurred');
        },

        /**
         * Parse error message string to detect error type
         */
        parseErrorMessage(message) {
            const lowerMsg = message.toLowerCase();

            // Check for quota/billing errors
            if (lowerMsg.includes('quota') || lowerMsg.includes('billing') || lowerMsg.includes('exceeded')) {
                return {
                    type: 'quota_exceeded',
                    title: 'API Quota Exceeded',
                    message: message,
                    provider: this.detectProvider(message)
                };
            }

            // Check for API key errors
            if (lowerMsg.includes('api key') || lowerMsg.includes('invalid key') || lowerMsg.includes('authentication')) {
                return {
                    type: 'invalid_key',
                    title: 'Invalid API Key',
                    message: message,
                    provider: this.detectProvider(message)
                };
            }

            // Check for rate limit
            if (lowerMsg.includes('rate limit') || lowerMsg.includes('too many requests')) {
                return {
                    type: 'rate_limit',
                    title: 'Rate Limit Exceeded',
                    message: message
                };
            }

            // Check for timeout
            if (lowerMsg.includes('timeout') || lowerMsg.includes('timed out')) {
                return {
                    type: 'timeout',
                    title: 'Request Timed Out',
                    message: message
                };
            }

            // Default unknown error
            return {
                type: 'unknown',
                title: 'Generation Failed',
                message: message
            };
        },

        getErrorTitle(errorType) {
            const titles = {
                quota_exceeded: 'API Quota Exceeded',
                invalid_key: 'Invalid API Key',
                rate_limit: 'Rate Limit Exceeded',
                timeout: 'Request Timed Out',
                service_unavailable: 'Service Unavailable',
                network_error: 'Network Error',
                auth_error: 'Authentication Error',
                unknown: 'Generation Failed'
            };
            return titles[errorType] || 'Error';
        },

        detectProvider(message) {
            const lowerMsg = message.toLowerCase();
            if (lowerMsg.includes('openai')) return 'openai';
            if (lowerMsg.includes('anthropic') || lowerMsg.includes('claude')) return 'anthropic';
            return null;
        },

        async pollStatus() {
            try {
                const response = await api.get(`/api/posts/generation/${this.jobId}/status`);
                const data = response.data;

                // Update progress
                this.progress = data.progress || 0;

                // Use backend step message if available, otherwise use our cycling messages
                if (data.current_step) {
                    this.currentStep = data.current_step;
                }

                // Update platform statuses
                if (data.platforms) {
                    Object.keys(data.platforms).forEach(platform => {
                        if (this.platformStatus[platform]) {
                            const platformData = data.platforms[platform];
                            this.platformStatus[platform] = {
                                status: platformData.status || 'pending',
                                message: platformData.message || 'Waiting...',
                                error: platformData.error || null
                            };
                        }
                    });
                }

                // Check if complete
                if (data.status === 'completed' || this.progress >= 100) {
                    this.handleComplete(data);
                } else if (data.status === 'failed' || data.status === 'error') {
                    // Parse error from status response
                    const errorDetails = data.error_details || data.error || 'Generation failed. Please try again.';
                    const parsedError = typeof errorDetails === 'object' ? errorDetails : this.parseErrorMessage(errorDetails);
                    this.handleError(parsedError.message, parsedError);
                }

            } catch (error) {
                logger.error('Error polling status:', error);

                // Don't show error for network issues - keep polling
                if (error.status) {
                    // Server error
                    const errorDetails = this.parseApiError(error);
                    this.handleError(errorDetails.message, errorDetails);
                }
                // For network errors, just log and continue polling
            }
        },

        handleComplete(data) {
            this.stopPolling();
            this.stopMessageCycle();
            this.isComplete = true;
            this.progress = 100;
            this.currentStep = 'Complete!';
            this.headingText = 'Posts Generated Successfully!';
            this.subheadingText = 'Redirecting to editor...';

            logger.debug('Generation complete:', data);

            // Mark all platforms as complete
            Object.keys(this.platformStatus).forEach(platform => {
                if (this.platformStatus[platform].status !== 'error') {
                    this.platformStatus[platform] = {
                        status: 'complete',
                        message: 'Ready to edit!'
                    };
                }
            });

            // Clear timeout warning
            if (this.timeoutWarningTimer) {
                clearTimeout(this.timeoutWarningTimer);
            }

            showToast('Posts generated successfully!', 'success');

            // Redirect to edit page after a brief delay
            setTimeout(() => {
                const postId = data.post_id || this.jobId;
                window.location.href = `post-edit.html?post_id=${postId}`;
            }, 1500);
        },

        handleError(errorMessage, errorDetails = null) {
            this.stopPolling();
            this.stopMessageCycle();
            this.error = errorMessage;
            this.errorDetails = errorDetails || this.parseErrorMessage(errorMessage);
            this.headingText = 'Generation Failed';
            this.subheadingText = 'We encountered an issue';

            logger.error('Generation failed:', errorMessage, errorDetails);

            // Mark processing platforms as error
            Object.keys(this.platformStatus).forEach(platform => {
                if (this.platformStatus[platform].status === 'processing') {
                    this.platformStatus[platform] = {
                        status: 'error',
                        message: 'Failed'
                    };
                }
            });

            // Clear timeout warning
            if (this.timeoutWarningTimer) {
                clearTimeout(this.timeoutWarningTimer);
            }

            // Show toast notification
            showToast(errorMessage, 'error', 5000);
        },

        getPlatformCardClass(platform) {
            const status = this.platformStatus[platform].status;
            if (status === 'complete') {
                return 'border-green-600 bg-green-900/20';
            } else if (status === 'processing') {
                return 'border-indigo-600 bg-indigo-900/20 ring-2 ring-indigo-400 ring-opacity-50';
            } else if (status === 'error') {
                return 'border-red-600 bg-red-900/20';
            }
            return '';
        },

        retry() {
            // Redirect back to feed for article selection
            window.location.href = 'index.html';
        },

        retryWithDelay(delay = 0) {
            if (delay > 0) {
                showToast(`Retrying in ${delay} seconds...`, 'info');
                setTimeout(() => {
                    window.location.reload();
                }, delay * 1000);
            } else {
                window.location.reload();
            }
        },

        cancel() {
            // Redirect back to feed (don't ask for confirmation, just go back)
            window.location.href = 'index.html';
        },

        goToHistory() {
            // Navigate to History page
            window.location.href = 'index.html?view=history';
        }
    }
});

app.mount('#generating-app');
