/**
 * Registration Modal Component
 * Triggered when guest tries to publish - encourages conversion
 *
 * Features:
 * - Compelling benefits messaging
 * - Quick signup form (email/password or OAuth)
 * - Pre-filled email from context
 * - Smooth animations
 */

const RegistrationModal = {
    name: 'RegistrationModal',
    template: `
        <transition name="modal-fade">
            <div
                v-if="show"
                class="fixed inset-0 z-50 overflow-y-auto"
                @click.self="handleBackdropClick"
            >
                <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                    <!-- Background overlay -->
                    <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="handleBackdropClick"></div>

                    <!-- Modal panel -->
                    <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                        <!-- Header -->
                        <div class="bg-gradient-to-r from-indigo-500 to-purple-600 px-6 py-8 text-center">
                            <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-white mb-4">
                                <svg class="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                                </svg>
                            </div>
                            <h3 class="text-2xl font-bold text-white mb-2">
                                Ready to share your posts?
                            </h3>
                            <p class="text-indigo-100 text-sm">
                                Create your free account to publish and unlock more features
                            </p>
                        </div>

                        <!-- Content -->
                        <div class="px-6 py-6">
                            <!-- Benefits List -->
                            <div class="mb-6 space-y-3">
                                <div class="flex items-start">
                                    <svg class="h-6 w-6 text-green-500 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div>
                                        <p class="text-sm font-medium text-gray-900">Generate 2 posts per day</p>
                                        <p class="text-xs text-gray-500">Perfect for consistent content creation</p>
                                    </div>
                                </div>

                                <div class="flex items-start">
                                    <svg class="h-6 w-6 text-green-500 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div>
                                        <p class="text-sm font-medium text-gray-900">Connect social media accounts</p>
                                        <p class="text-xs text-gray-500">Twitter, LinkedIn, Instagram, Threads</p>
                                    </div>
                                </div>

                                <div class="flex items-start">
                                    <svg class="h-6 w-6 text-green-500 mr-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div>
                                        <p class="text-sm font-medium text-gray-900">Schedule posts for later</p>
                                        <p class="text-xs text-gray-500">Plan your content calendar ahead</p>
                                    </div>
                                </div>
                            </div>

                            <!-- Social Login Buttons -->
                            <div class="space-y-2 mb-4">
                                <button
                                    @click="handleSocialLogin('google')"
                                    :disabled="loading"
                                    class="w-full inline-flex justify-center items-center px-4 py-3 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-all"
                                >
                                    <svg class="h-5 w-5 mr-3" viewBox="0 0 24 24">
                                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                    </svg>
                                    Continue with Google
                                </button>
                            </div>

                            <!-- Divider -->
                            <div class="relative my-4">
                                <div class="absolute inset-0 flex items-center">
                                    <div class="w-full border-t border-gray-300"></div>
                                </div>
                                <div class="relative flex justify-center text-sm">
                                    <span class="px-2 bg-white text-gray-500">Or with email</span>
                                </div>
                            </div>

                            <!-- Email Form -->
                            <form @submit.prevent="handleSignup" class="space-y-4">
                                <div>
                                    <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
                                        Email address
                                    </label>
                                    <input
                                        id="email"
                                        v-model="form.email"
                                        type="email"
                                        required
                                        :class="{'border-red-300': errors.email}"
                                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                                        placeholder="you@example.com"
                                    >
                                    <p v-if="errors.email" class="mt-1 text-sm text-red-600">{{ errors.email }}</p>
                                </div>

                                <div>
                                    <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
                                        Password
                                    </label>
                                    <input
                                        id="password"
                                        v-model="form.password"
                                        type="password"
                                        required
                                        :class="{'border-red-300': errors.password}"
                                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                                        placeholder="Create a password"
                                    >
                                    <p v-if="errors.password" class="mt-1 text-sm text-red-600">{{ errors.password }}</p>
                                </div>

                                <!-- Error Message -->
                                <div v-if="errors.general" class="bg-red-50 border border-red-200 rounded-md p-3">
                                    <p class="text-sm text-red-800">{{ errors.general }}</p>
                                </div>

                                <!-- Submit Button -->
                                <button
                                    type="submit"
                                    :disabled="loading"
                                    class="w-full flex justify-center items-center px-4 py-3 border border-transparent text-sm font-semibold rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <span v-if="!loading">Sign up to publish</span>
                                    <span v-else class="flex items-center">
                                        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Creating account...
                                    </span>
                                </button>
                            </form>

                            <!-- Login Link -->
                            <p class="mt-4 text-center text-sm text-gray-600">
                                Already have an account?
                                <button @click="handleLoginClick" class="font-medium text-indigo-600 hover:text-indigo-500">
                                    Sign in
                                </button>
                            </p>
                        </div>

                        <!-- Close Button -->
                        <button
                            @click="close"
                            class="absolute top-4 right-4 text-white hover:text-indigo-100 focus:outline-none"
                        >
                            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </transition>
    `,
    props: {
        show: {
            type: Boolean,
            default: false
        },
        prefillEmail: {
            type: String,
            default: ''
        }
    },
    data() {
        return {
            loading: false,
            form: {
                email: this.prefillEmail,
                password: ''
            },
            errors: {
                email: '',
                password: '',
                general: ''
            }
        };
    },
    watch: {
        prefillEmail(newVal) {
            this.form.email = newVal;
        }
    },
    methods: {
        close() {
            this.$emit('close');
        },

        handleBackdropClick() {
            this.$emit('backdrop-click');
        },

        handleSocialLogin(provider) {
            this.$emit('social-login', provider);
        },

        handleLoginClick() {
            this.$emit('switch-to-login');
        },

        async handleSignup() {
            // Reset errors
            this.errors = { email: '', password: '', general: '' };
            this.loading = true;

            try {
                this.$emit('signup', this.form);
            } catch (error) {
                this.errors.general = error.message || 'Failed to create account';
            } finally {
                this.loading = false;
            }
        }
    }
};

// Export for use in other components
if (typeof window !== 'undefined') {
    window.RegistrationModal = RegistrationModal;
}

export default RegistrationModal;
