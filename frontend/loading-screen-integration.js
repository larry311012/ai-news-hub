import { showToast } from './utils/toast.js';
import { createApp } from 'vue'
import axios from 'axios'
import '/src/style.css'

/**
 * LOADING SCREEN INTEGRATION GUIDE
 * AI News Aggregator - Post Generation Loading State
 *
 * This file contains the Vue.js data properties and methods needed
 * to integrate the loading screen component into your app.
 *
 * INTEGRATION STEPS:
 * 1. Add the data properties to your Vue app's data() section
 * 2. Add the computed properties
 * 3. Add the methods
 * 4. Update your generatePosts() method to use the new loading system
 */

// ============================================================================
// 1. DATA PROPERTIES (Add to your Vue app's data() function)
// ============================================================================

const loadingScreenData = {
    // Loading screen visibility
    isGenerating: false,

    // Platform status tracking
    platformStatus: {
        linkedin: {
            status: 'pending',      // 'pending', 'generating', 'completed', 'error'
            message: 'Waiting to start...',
            progress: 0,            // 0-100 for progress bar
            error: null             // Error message if status is 'error'
        },
        twitter: {
            status: 'pending',
            message: 'Waiting to start...',
            progress: 0,
            error: null
        },
        threads: {
            status: 'pending',
            message: 'Waiting to start...',
            progress: 0,
            error: null
        }
    },

    // Generation state
    generationComplete: false,
    generationError: false,
    currentGeneratingPlatform: null,  // 'linkedin', 'twitter', or 'threads'

    // Generated content storage (moved from existing)
    generatedContent: null
};

// ============================================================================
// 2. COMPUTED PROPERTIES (Add to your Vue app's computed section)
// ============================================================================

const loadingScreenComputed = {
    // Calculate overall progress percentage
    overallProgress() {
        const statuses = ['linkedin', 'twitter', 'threads'];
        let totalProgress = 0;

        statuses.forEach(platform => {
            const status = this.platformStatus[platform].status;
            if (status === 'completed') {
                totalProgress += 100;
            } else if (status === 'generating') {
                totalProgress += this.platformStatus[platform].progress || 0;
            }
        });

        return Math.round(totalProgress / 3);
    },

    // Get platform card styling class
    getPlatformCardClass() {
        return (platform) => {
            const status = this.platformStatus[platform].status;
            const baseClass = 'border-gray-200';

            if (status === 'generating') {
                return 'active bg-indigo-50';
            } else if (status === 'completed') {
                return 'completed bg-green-50';
            } else if (status === 'error') {
                return 'error bg-red-50';
            }

            return baseClass;
        };
    },

    // Get platform icon container class
    getPlatformIconClass() {
        return (platform) => {
            const status = this.platformStatus[platform].status;

            if (status === 'completed') {
                if (platform === 'linkedin') return 'bg-blue-100';
                if (platform === 'twitter') return 'bg-sky-100';
                if (platform === 'threads') return 'bg-gradient-to-r from-purple-100 to-pink-100';
            } else if (status === 'error') {
                return 'bg-red-100';
            } else if (status === 'generating') {
                if (platform === 'linkedin') return 'bg-blue-100';
                if (platform === 'twitter') return 'bg-sky-100';
                if (platform === 'threads') return 'bg-gradient-to-r from-purple-100 to-pink-100';
            }

            return 'bg-gray-100';
        };
    },

    // Get platform icon color class
    getPlatformIconColor() {
        return (platform) => {
            const status = this.platformStatus[platform].status;

            if (status === 'error') return 'text-red-600';
            if (status === 'completed' || status === 'generating') {
                if (platform === 'linkedin') return 'text-blue-600';
                if (platform === 'twitter') return 'text-sky-600';
                if (platform === 'threads') return 'text-white';
            }

            return 'text-gray-400';
        };
    },

    // Get platform status text color
    getPlatformStatusColor() {
        return (platform) => {
            const status = this.platformStatus[platform].status;

            if (status === 'completed') return 'text-green-600';
            if (status === 'error') return 'text-red-600';
            if (status === 'generating') return 'text-indigo-600';

            return 'text-gray-500';
        };
    }
};

// ============================================================================
// 3. METHODS (Add to your Vue app's methods section)
// ============================================================================

const loadingScreenMethods = {
    /**
     * Initialize loading screen for post generation
     */
    startPostGeneration() {
        // Reset all states
        this.isGenerating = true;
        this.generationComplete = false;
        this.generationError = false;
        this.currentGeneratingPlatform = null;

        // Reset all platform statuses
        Object.keys(this.platformStatus).forEach(platform => {
            this.platformStatus[platform] = {
                status: 'pending',
                message: 'Waiting to start...',
                progress: 0,
                error: null
            };
        });
    },

    /**
     * Update a specific platform's status
     * @param {string} platform - 'linkedin', 'twitter', or 'threads'
     * @param {string} status - 'pending', 'generating', 'completed', 'error'
     * @param {string} message - Status message to display
     * @param {number} progress - Progress percentage (0-100)
     * @param {string} error - Error message (if status is 'error')
     */
    updatePlatformStatus(platform, status, message, progress = 0, error = null) {
        if (!this.platformStatus[platform]) return;

        this.platformStatus[platform] = {
            status,
            message,
            progress,
            error
        };

        // Update current generating platform
        if (status === 'generating') {
            this.currentGeneratingPlatform = platform.charAt(0).toUpperCase() + platform.slice(1);
        } else if (status === 'completed' || status === 'error') {
            this.currentGeneratingPlatform = null;
        }

        // Check if all platforms are done
        this.checkGenerationComplete();
    },

    /**
     * Check if all platforms are completed or have errors
     */
    checkGenerationComplete() {
        const platforms = ['linkedin', 'twitter', 'threads'];
        const allDone = platforms.every(platform => {
            const status = this.platformStatus[platform].status;
            return status === 'completed' || status === 'error';
        });

        if (allDone) {
            const hasError = platforms.some(platform =>
                this.platformStatus[platform].status === 'error'
            );

            this.generationComplete = !hasError;
            this.generationError = hasError;
            this.currentGeneratingPlatform = null;
        }
    },

    /**
     * Simulate progress for a platform (optional - for smooth UX)
     * @param {string} platform - Platform name
     * @param {number} duration - Duration in milliseconds
     */
    simulateProgress(platform, duration = 10000) {
        const startTime = Date.now();
        const interval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(Math.round((elapsed / duration) * 90), 90); // Max 90%

            if (this.platformStatus[platform].status === 'generating') {
                this.platformStatus[platform].progress = progress;
            } else {
                clearInterval(interval);
            }
        }, 200);

        return interval;
    },

    /**
     * Retry a failed platform
     * @param {string} platform - Platform to retry
     */
    async retryPlatform(platform) {
        // Reset this platform's status
        this.updatePlatformStatus(platform, 'pending', 'Waiting to start...', 0);
        this.generationError = false;
        this.generationComplete = false;

        // Retry generation for this platform only
        await this.generateSinglePlatform(platform);
    },

    /**
     * Retry all failed platforms
     */
    async retryAllFailed() {
        const platforms = ['linkedin', 'twitter', 'threads'];
        const failedPlatforms = platforms.filter(platform =>
            this.platformStatus[platform].status === 'error'
        );

        this.generationError = false;
        this.generationComplete = false;

        for (const platform of failedPlatforms) {
            this.updatePlatformStatus(platform, 'pending', 'Waiting to start...', 0);
            await this.generateSinglePlatform(platform);
        }
    },

    /**
     * Continue with successful posts (skip failed ones)
     */
    continueWithSuccessful() {
        this.isGenerating = false;
        this.currentView = 'editor';

        // Analytics tracking
        if (window.analyticsClient) {
            window.analyticsClient.track('post_generation_partial_success', {
                successful_platforms: Object.keys(this.platformStatus).filter(
                    platform => this.platformStatus[platform].status === 'completed'
                )
            });
        }
    },

    /**
     * Continue to editor after successful generation
     */
    continueToEditor() {
        this.isGenerating = false;
        this.currentView = 'editor';

        // Analytics tracking
        if (window.analyticsClient) {
            window.analyticsClient.track('post_generation_complete', {
                platforms: ['linkedin', 'twitter', 'threads']
            });
        }
    },

    /**
     * Cancel the generation process
     */
    cancelGeneration() {
        if (confirm('Are you sure you want to cancel post generation?')) {
            this.isGenerating = false;
            this.startPostGeneration(); // Reset states

            // Analytics tracking
            if (window.analyticsClient) {
                window.analyticsClient.track('post_generation_cancelled', {
                    progress: this.overallProgress
                });
            }
        }
    },

    /**
     * Generate posts for a single platform
     * @param {string} platform - Platform to generate for
     */
    async generateSinglePlatform(platform) {
        try {
            // Update status to generating
            this.updatePlatformStatus(
                platform,
                'generating',
                'Generating content...',
                0
            );

            // Start progress simulation (optional)
            const progressInterval = this.simulateProgress(platform);

            // Make API call to generate content
            const response = await axios.post('/api/generate-post', {
                articles: this.selectedArticles,
                platform: platform,
                // Add any other necessary parameters
            });

            // Stop progress simulation
            clearInterval(progressInterval);

            // Update with success
            this.updatePlatformStatus(
                platform,
                'completed',
                'Generated successfully',
                100
            );

            // Store generated content
            if (!this.generatedContent) {
                this.generatedContent = {};
            }
            this.generatedContent[platform] = response.data.content;

        } catch (error) {
            console.error(`Error generating ${platform} post:`, error);

            // Update with error
            this.updatePlatformStatus(
                platform,
                'error',
                'Generation failed',
                0,
                error.response?.data?.error || error.message || 'Unknown error occurred'
            );
        }
    }
};

// ============================================================================
// 4. UPDATED GENERATE POSTS METHOD
// Replace your existing generatePosts() method with this version
// ============================================================================

async function generatePosts() {
    // Validate selection
    if (this.selectedArticles.length === 0) {
        showToast('Please select at least one article', 'warning');
        return;
    }

    // Initialize loading screen
    this.startPostGeneration();

    // Track analytics
    if (window.analyticsClient) {
        window.analyticsClient.track('post_generation_started', {
            article_count: this.selectedArticles.length,
            platforms: ['linkedin', 'twitter', 'threads']
        });
    }

    // Generate for each platform sequentially
    const platforms = ['linkedin', 'twitter', 'threads'];

    for (const platform of platforms) {
        await this.generateSinglePlatform(platform);

        // Optional: Add small delay between platforms for better UX
        await new Promise(resolve => setTimeout(resolve, 500));
    }
}

// ============================================================================
// 5. EXAMPLE USAGE IN YOUR APP
// ============================================================================

/*
// In your Vue app initialization:

createApp({
    data() {
        return {
            // ... your existing data properties ...

            // Add loading screen data
            ...loadingScreenData,

            // ... rest of your data ...
        };
    },

    computed: {
        // ... your existing computed properties ...

        // Add loading screen computed properties
        ...loadingScreenComputed,

        // ... rest of your computed properties ...
    },

    methods: {
        // ... your existing methods ...

        // Add loading screen methods
        ...loadingScreenMethods,

        // Replace generatePosts method
        generatePosts,

        // ... rest of your methods ...
    },

    mounted() {
        // ... your existing mounted logic ...
    }
}).mount('#app');
*/

// ============================================================================
// 6. API ENDPOINT EXAMPLE (Backend Integration)
// ============================================================================

/*
// Example Express.js endpoint for post generation:

app.post('/api/generate-post', async (req, res) => {
    try {
        const { articles, platform } = req.body;

        // Your AI generation logic here
        const content = await generatePostContent(articles, platform);

        res.json({
            success: true,
            content: content,
            platform: platform
        });

    } catch (error) {
        console.error('Post generation error:', error);
        res.status(500).json({
            success: false,
            error: error.message || 'Failed to generate post'
        });
    }
});
*/

// ============================================================================
// 7. ACCESSIBILITY NOTES
// ============================================================================

/*
IMPORTANT ACCESSIBILITY FEATURES INCLUDED:

1. ARIA Labels:
   - Add role="status" to status messages
   - Add aria-live="polite" to progress indicators
   - Add aria-label to all interactive elements

2. Keyboard Navigation:
   - All buttons are keyboard accessible
   - Focus trap should be implemented in the modal
   - ESC key should cancel generation (add @keydown.esc handler)

3. Screen Reader Support:
   - Status changes are announced
   - Progress updates are conveyed
   - Error messages are properly associated

4. Example ARIA implementation:
   <div role="status" aria-live="polite" aria-atomic="true">
       {{ platformStatus.linkedin.message }}
   </div>

5. Focus Management:
   - When modal opens, focus should move to first interactive element
   - When modal closes, focus should return to trigger element
*/

// ============================================================================
// 8. PERFORMANCE OPTIMIZATION TIPS
// ============================================================================

/*
1. Debounce progress updates:
   - Don't update progress more than every 100-200ms
   - Use requestAnimationFrame for smooth animations

2. Lazy load platform icons:
   - Consider using inline SVGs (already done in component)
   - Or lazy load icon sprite sheet

3. Memory management:
   - Clear intervals when component unmounts
   - Remove event listeners properly

4. Network optimization:
   - Consider implementing retry with exponential backoff
   - Add request cancellation for user-initiated cancels
   - Implement request timeouts

5. Animation performance:
   - Use CSS transforms instead of position changes
   - Prefer opacity changes over visibility
   - Use will-change for animated elements (sparingly)
*/

// Export for module systems (optional)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loadingScreenData,
        loadingScreenComputed,
        loadingScreenMethods,
        generatePosts
    };
}
