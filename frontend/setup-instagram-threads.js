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
            totalSteps: 5,
            expandedSteps: {
                1: true,
                2: false,
                3: false,
                4: false,
                5: false
            },
            stepCompleted: {
                1: false,
                2: false,
                3: false,
                4: false,
                5: false
            },

            // Step titles for progress bar
            stepTitles: ['Overview', 'Requirements', 'Instagram', 'Threads', 'Verify'],

            // Connection states
            instagramConnected: false,
            threadsConnected: false,
            threadsSkipped: false,

            // Test connection
            testing: false,
            testResult: null,

            setupComplete: false
        };
    },
    computed: {
        progress() {
            const completedCount = Object.values(this.stepCompleted).filter(Boolean).length;
            return (completedCount / this.totalSteps) * 100;
        },
        connectedPlatformsCount() {
            let count = 0;
            if (this.instagramConnected) count++;
            if (this.threadsConnected) count++;
            return count;
        },
        connectedPlatformsText() {
            const platforms = [];
            if (this.instagramConnected) platforms.push('Instagram');
            if (this.threadsConnected) platforms.push('Threads');

            if (platforms.length === 0) return 'account';
            if (platforms.length === 1) return platforms[0] + ' account';
            return platforms.join(' and ') + ' accounts';
        }
    },
    mounted() {
        // Check if already connected
        this.checkConnectionStatus();

        // Load saved progress from localStorage
        this.loadProgress();

        // Handle OAuth callbacks
        this.handleOAuthCallback();
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

        handleInstagramStatus(status) {
            logger.debug('Instagram status update:', status);

            // Handle the event from the InstagramOAuthConnect component
            if (status && status.connected !== undefined) {
                this.instagramConnected = status.connected;

                if (status.connected) {
                    this.stepCompleted[3] = true;
                    showToast('Instagram connected successfully!', 'success');
                    this.saveProgress();
                }
            }
        },

        handleThreadsStatus(status) {
            logger.debug('Threads status update:', status);

            // Handle the event from the ThreadsOAuthConnect component
            if (status && status.connected !== undefined) {
                this.threadsConnected = status.connected;

                if (status.connected) {
                    showToast('Threads connected successfully!', 'success');
                    this.saveProgress();
                }
            }
        },

        skipThreads() {
            this.threadsSkipped = true;
            showToast('Threads setup skipped. You can connect it later from your profile.', 'info');
        },

        async checkConnectionStatus() {
            try {
                const response = await api.get('/social-media/connections/status');

                logger.debug('Connection status check:', response.data);

                // Check Instagram connection
                const instagramConnection = response.data.find(conn => conn.platform === 'instagram');
                this.instagramConnected = instagramConnection && instagramConnection.is_active;

                // Check Threads connection
                const threadsConnection = response.data.find(conn => conn.platform === 'threads');
                this.threadsConnected = threadsConnection && threadsConnection.is_active;

                // Update step completion based on connections
                if (this.instagramConnected) {
                    this.stepCompleted[3] = true;
                }

                if (this.threadsConnected) {
                    // Threads is connected, not skipped
                    this.threadsSkipped = false;
                }
            } catch (error) {
                logger.error('Error checking connection status:', error);
            }
        },

        async testConnection() {
            this.testing = true;
            this.testResult = null;

            try {
                // Test Instagram connection
                const instagramResponse = await api.get('/social-media/instagram/test');

                logger.debug('Instagram test response:', instagramResponse.data);

                if (instagramResponse.data.connected) {
                    this.testResult = {
                        success: true,
                        message: 'Your Instagram connection is working perfectly! You\'re ready to start publishing.'
                    };
                    showToast('Connection test successful!', 'success');
                } else {
                    throw new Error('Instagram connection test failed');
                }
            } catch (error) {
                logger.error('Error testing Instagram connection:', error);
                this.testResult = {
                    success: false,
                    message: 'Connection test failed. Please try reconnecting your account.'
                };
                showToast('Connection test failed', 'error');
            } finally {
                this.testing = false;
            }
        },

        handleOAuthCallback() {
            const urlParams = new URLSearchParams(window.location.search);
            const success = urlParams.get('success');
            const platform = urlParams.get('platform');

            if (success === 'true') {
                if (platform === 'instagram') {
                    this.instagramConnected = true;
                    this.stepCompleted[3] = true;
                    showToast('Instagram connected successfully!', 'success');
                } else if (platform === 'threads') {
                    this.threadsConnected = true;
                    showToast('Threads connected successfully!', 'success');
                }

                this.saveProgress();

                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);

                // Refresh connection status
                setTimeout(() => {
                    this.checkConnectionStatus();
                }, 1000);
            }
        },

        celebrateCompletion() {
            // Create confetti effect
            const colors = ['#9333ea', '#ec4899', '#f59e0b', '#10b981', '#3b82f6'];

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

            showToast('Setup complete! You can now start creating posts.', 'success');
        },

        saveProgress() {
            const progress = {
                stepCompleted: this.stepCompleted,
                currentStep: this.currentStep,
                setupComplete: this.setupComplete,
                instagramConnected: this.instagramConnected,
                threadsConnected: this.threadsConnected,
                threadsSkipped: this.threadsSkipped
            };
            localStorage.setItem('meta_setup_progress', JSON.stringify(progress));
        },

        loadProgress() {
            const saved = localStorage.getItem('meta_setup_progress');
            if (saved) {
                try {
                    const progress = JSON.parse(saved);
                    this.stepCompleted = progress.stepCompleted || { 1: false, 2: false, 3: false, 4: false, 5: false };
                    this.currentStep = progress.currentStep || 1;
                    this.setupComplete = progress.setupComplete || false;
                    this.threadsSkipped = progress.threadsSkipped || false;
                    // Don't load connection status from localStorage - always check API

                    // Expand current step
                    if (this.currentStep <= this.totalSteps) {
                        this.expandedSteps[this.currentStep] = true;
                    }
                } catch (error) {
                    logger.error('Error loading Meta setup progress:', error);
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

// Register Instagram OAuth Connect component
if (typeof InstagramOAuthConnect !== 'undefined') {
    app.component('instagram-oauth-connect', InstagramOAuthConnect);
}

// Register Threads OAuth Connect component
if (typeof ThreadsOAuthConnect !== 'undefined') {
    app.component('threads-oauth-connect', ThreadsOAuthConnect);
}

app.mount('#setup-app');
