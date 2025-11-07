/**
 * Guest Mode Banner Component
 * Non-intrusive banner to encourage guest users to try the app
 *
 * Features:
 * - Dismissible with localStorage persistence
 * - Shows only to non-authenticated users
 * - Clear call-to-action
 * - Responsive design
 */

const GuestModeBanner = {
    name: 'GuestModeBanner',
    template: `
        <div
            v-if="isVisible && !isAuthenticated"
            class="bg-gradient-to-r from-indigo-500 to-purple-600 border-b border-indigo-700 py-3 px-4 animate-slide-down"
        >
            <div class="max-w-7xl mx-auto flex items-center justify-between">
                <div class="flex items-center flex-1">
                    <svg class="h-6 w-6 text-white mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <div class="flex-1">
                        <p class="text-white font-medium text-sm md:text-base">
                            Try it free! Generate <span class="font-bold">1 post</span> without signing up
                        </p>
                        <p class="text-indigo-100 text-xs mt-0.5 hidden sm:block">
                            No credit card required. See AI-powered content in action.
                        </p>
                    </div>
                </div>

                <div class="flex items-center space-x-3 ml-4">
                    <button
                        @click="handleGetStarted"
                        class="bg-white text-indigo-600 px-4 py-2 rounded-md text-sm font-semibold hover:bg-indigo-50 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-600"
                    >
                        Get Started
                    </button>

                    <button
                        @click="dismiss"
                        class="text-white hover:text-indigo-100 focus:outline-none focus:ring-2 focus:ring-white rounded p-1"
                        aria-label="Dismiss banner"
                    >
                        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    `,
    props: {
        isAuthenticated: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            isVisible: true
        };
    },
    mounted() {
        // Check if banner was previously dismissed
        const dismissed = localStorage.getItem('guest_banner_dismissed');
        const dismissedTime = dismissed ? parseInt(dismissed) : 0;
        const now = Date.now();

        // Show banner again after 7 days
        const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000;
        if (dismissed && (now - dismissedTime < SEVEN_DAYS)) {
            this.isVisible = false;
        }
    },
    methods: {
        dismiss() {
            this.isVisible = false;
            localStorage.setItem('guest_banner_dismissed', Date.now().toString());
        },

        handleGetStarted() {
            // Scroll to articles section or emit event
            this.$emit('get-started');

            // Optionally dismiss after click
            this.dismiss();
        }
    }
};

// Export for use in other components
if (typeof window !== 'undefined') {
    window.GuestModeBanner = GuestModeBanner;
}

export default GuestModeBanner;
