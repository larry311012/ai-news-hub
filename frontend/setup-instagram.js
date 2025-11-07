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
            totalSteps: 3,
            expandedSteps: {
                1: true,
                2: false,
                3: false
            },
            stepCompleted: {
                1: false,
                2: false,
                3: false
            },
            instagramConnected: false,
            threadsConnected: false,
            testing: false,
            testResult: null,
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
        // Check if already connected
        this.checkConnectionStatus();

        // Load saved progress from localStorage
        this.loadProgress();
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

        handleInstagramConnection(status) {
            this.instagramConnected = status.connected;

            if (status.connected) {
                this.updateStepCompletion();
                this.saveProgress();
                showToast('Instagram connected successfully!', 'success');
            }
        },

        handleThreadsConnection(status) {
            this.threadsConnected = status.connected;

            if (status.connected) {
                this.updateStepCompletion();
                this.saveProgress();
                showToast('Threads connected successfully!', 'success');
            }
        },

        updateStepCompletion() {
            // Mark step 2 complete if either platform is connected
            if (this.instagramConnected || this.threadsConnected) {
                this.stepCompleted[2] = true;
            }
        },

        async checkConnectionStatus() {
            try {
                const response = await api.get('/social-media/connections/status');

                logger.debug('Connection status:', response.data);

                // Check Instagram connection
                const instagramConnection = response.data.find(conn => conn.platform === 'instagram');
                this.instagramConnected = instagramConnection && instagramConnection.is_active;

                // Check Threads connection
                const threadsConnection = response.data.find(conn => conn.platform === 'threads');
                this.threadsConnected = threadsConnection && threadsConnection.is_active;

                this.updateStepCompletion();
            } catch (error) {
                logger.error('Error checking connection status:', error);
            }
        },

        async testConnection() {
            this.testing = true;
            this.testResult = null;

            try {
                const response = await api.get('/social-media/connections/status');

                logger.debug('Connection test response:', response.data);

                // Check Instagram connection
                const instagramConnection = response.data.find(conn => conn.platform === 'instagram');
                const instagramActive = instagramConnection && instagramConnection.is_active;

                // Check Threads connection
                const threadsConnection = response.data.find(conn => conn.platform === 'threads');
                const threadsActive = threadsConnection && threadsConnection.is_active;

                if (instagramActive && threadsActive) {
                    this.testResult = {
                        success: true,
                        message: 'Both Instagram and Threads are connected and working correctly!'
                    };
                    showToast('Connection test passed!', 'success');
                } else if (instagramActive) {
                    this.testResult = {
                        success: true,
                        message: 'Instagram is connected and working correctly!'
                    };
                    showToast('Instagram connection verified!', 'success');
                } else if (threadsActive) {
                    this.testResult = {
                        success: true,
                        message: 'Threads is connected and working correctly!'
                    };
                    showToast('Threads connection verified!', 'success');
                } else {
                    this.testResult = {
                        success: false,
                        message: 'No platforms are connected. Please connect at least one platform.'
                    };
                    showToast('No connections found', 'warning');
                }
            } catch (error) {
                logger.error('Error testing connection:', error);
                this.testResult = {
                    success: false,
                    message: 'Unable to test connections. Please try again.'
                };
                showToast('Connection test failed', 'error');
            } finally {
                this.testing = false;
            }
        },

        celebrateCompletion() {
            // Create confetti effect with Instagram/Threads colors
            const colors = ['#E1306C', '#5B51D8', '#F58529', '#833AB4', '#C13584'];

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

            showToast('Setup complete! You can now publish to Instagram and Threads.', 'success');
        },

        saveProgress() {
            const progress = {
                stepCompleted: this.stepCompleted,
                currentStep: this.currentStep,
                setupComplete: this.setupComplete
            };
            localStorage.setItem('instagram_setup_progress', JSON.stringify(progress));
        },

        loadProgress() {
            const saved = localStorage.getItem('instagram_setup_progress');
            if (saved) {
                try {
                    const progress = JSON.parse(saved);
                    this.stepCompleted = progress.stepCompleted || { 1: false, 2: false, 3: false };
                    this.currentStep = progress.currentStep || 1;
                    this.setupComplete = progress.setupComplete || false;
                } catch (error) {
                    logger.error('Error loading Instagram setup progress:', error);
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
