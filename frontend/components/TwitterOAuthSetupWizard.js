/**
 * Twitter OAuth Setup Wizard Component - Enhanced Version
 *
 * A beautiful, user-friendly wizard with comprehensive credential validation
 * that guides users through setting up their own Twitter OAuth credentials.
 *
 * Features:
 * - 5-step guided process with progress tracking
 * - Smart credential validation (detects placeholders, invalid formats)
 * - Real-time format checking
 * - Copy-to-clipboard functionality
 * - Detailed error messages and help
 * - Mobile responsive design
 * - Accessibility compliant
 *
 * Usage:
 * <twitter-oauth-setup-wizard></twitter-oauth-setup-wizard>
 */

const TwitterOAuthSetupWizard = {
    name: 'TwitterOAuthSetupWizard',
    template: `
        <div>
            <!-- Trigger Button -->
            <button @click="openWizard"
                    class="w-full px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-md hover:from-blue-600 hover:to-blue-700 font-medium transition-all duration-200 text-sm flex items-center justify-center gap-2 shadow-sm hover:shadow">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                Set Up Your Own Twitter App
            </button>

            <!-- Wizard Modal - Desktop: Modal, Mobile: Full Screen -->
            <div v-if="isOpen"
                 class="fixed inset-0 z-50 overflow-y-auto"
                 @click.self="closeWizard">

                <!-- Backdrop -->
                <div class="fixed inset-0 bg-gray-900 bg-opacity-75 transition-opacity"></div>

                <!-- Modal Container -->
                <div class="flex min-h-screen items-center justify-center p-0 sm:p-4">

                    <!-- Modal Content -->
                    <div class="relative w-full max-w-3xl bg-white sm:rounded-2xl shadow-2xl transform transition-all h-screen sm:h-auto sm:max-h-[90vh] flex flex-col">

                        <!-- Header -->
                        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                                    <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                    </svg>
                                </div>
                                <div>
                                    <h2 class="text-xl font-bold text-gray-900">Twitter OAuth Setup</h2>
                                    <p class="text-sm text-gray-500">{{ stepTitles[currentStep - 1] }}</p>
                                </div>
                            </div>
                            <button @click="closeWizard"
                                    class="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-lg"
                                    aria-label="Close wizard">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>

                        <!-- Progress Bar -->
                        <div class="px-6 pt-6 flex-shrink-0">
                            <div class="flex items-center justify-between mb-2">
                                <span class="text-sm font-medium text-gray-700">Step {{ currentStep }} of 5</span>
                                <span class="text-sm text-gray-500">{{ Math.round((currentStep / 5) * 100) }}% Complete</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                <div class="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-500 ease-out"
                                     :style="{ width: (currentStep / 5 * 100) + '%' }"></div>
                            </div>

                            <!-- Progress Dots -->
                            <div class="flex items-center justify-between mt-4">
                                <div v-for="step in 5" :key="step" class="flex-1 flex items-center">
                                    <div class="flex flex-col items-center flex-1">
                                        <div :class="[
                                            'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300',
                                            currentStep > step ? 'bg-green-500 text-white' :
                                            currentStep === step ? 'bg-blue-500 text-white ring-4 ring-blue-100' :
                                            'bg-gray-200 text-gray-500'
                                        ]">
                                            <svg v-if="currentStep > step" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                                            </svg>
                                            <span v-else>{{ step }}</span>
                                        </div>
                                        <span class="text-xs text-gray-500 mt-1 hidden sm:block text-center">{{ stepLabels[step - 1] }}</span>
                                    </div>
                                    <div v-if="step < 5" :class="[
                                        'flex-1 h-0.5 mx-1 transition-all duration-300',
                                        currentStep > step ? 'bg-green-500' : 'bg-gray-200'
                                    ]"></div>
                                </div>
                            </div>
                        </div>

                        <!-- Content Area - Scrollable -->
                        <div class="flex-1 overflow-y-auto px-6 py-6">

                            <!-- Step 1: Welcome -->
                            <div v-show="currentStep === 1" class="space-y-6 animate-fade-in">
                                <div class="text-center py-8">
                                    <div class="mx-auto w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mb-6">
                                        <svg class="w-10 h-10 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                        </svg>
                                    </div>
                                    <h3 class="text-2xl font-bold text-gray-900 mb-3">Let's Connect Your Twitter Account</h3>
                                    <p class="text-gray-600 max-w-md mx-auto mb-6">
                                        We'll guide you through setting up your own Twitter developer account and creating an app.
                                        This gives you full control over your Twitter integration.
                                    </p>
                                </div>

                                <div class="bg-blue-50 border-2 border-blue-200 rounded-xl p-6 space-y-4">
                                    <h4 class="font-semibold text-blue-900 flex items-center gap-2">
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                        What you'll need:
                                    </h4>
                                    <ul class="space-y-3 text-sm text-blue-800">
                                        <li class="flex items-start gap-2">
                                            <svg class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                            </svg>
                                            <span>A Twitter/X account (free)</span>
                                        </li>
                                        <li class="flex items-start gap-2">
                                            <svg class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                            </svg>
                                            <span>About 5 minutes of your time</span>
                                        </li>
                                        <li class="flex items-start gap-2">
                                            <svg class="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                            </svg>
                                            <span>A phone number (for developer account verification)</span>
                                        </li>
                                    </ul>
                                </div>

                                <div class="bg-green-50 border border-green-200 rounded-xl p-5">
                                    <div class="flex items-start gap-3">
                                        <svg class="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                                        </svg>
                                        <div>
                                            <h5 class="font-semibold text-green-900 mb-1">Your data is secure</h5>
                                            <p class="text-sm text-green-800">Your credentials are encrypted and stored securely. We never share your information.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 2: Create Developer Account -->
                            <div v-show="currentStep === 2" class="space-y-6 animate-fade-in">
                                <div>
                                    <h3 class="text-xl font-bold text-gray-900 mb-2">Create Twitter Developer Account</h3>
                                    <p class="text-gray-600">You need a developer account to create apps on Twitter.</p>
                                </div>

                                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-6 space-y-4">
                                    <h4 class="font-semibold text-gray-900">Follow these steps:</h4>

                                    <div class="space-y-4">
                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">1</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-2">Visit Twitter Developer Portal</p>
                                                <a href="https://developer.twitter.com/en/portal/dashboard"
                                                   target="_blank"
                                                   class="inline-flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium">
                                                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                                                    </svg>
                                                    Open Developer Portal
                                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                                    </svg>
                                                </a>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">2</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-1">Sign in with your Twitter account</p>
                                                <p class="text-sm text-gray-600">Use your existing Twitter credentials</p>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">3</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-1">Apply for Essential access</p>
                                                <p class="text-sm text-gray-600">Free tier is perfect for personal use</p>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">4</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-1">Complete the application</p>
                                                <p class="text-sm text-gray-600">Answer a few questions about how you'll use the API</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                    <div class="flex gap-3">
                                        <svg class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                        <div class="text-sm text-yellow-800">
                                            <p class="font-semibold mb-1">Approval usually takes a few minutes</p>
                                            <p>In some cases, it may take up to 24 hours. You'll receive an email when approved.</p>
                                        </div>
                                    </div>
                                </div>

                                <div class="flex items-center gap-3 pt-4">
                                    <input type="checkbox"
                                           id="dev-account-created"
                                           v-model="wizardData.devAccountCreated"
                                           class="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2">
                                    <label for="dev-account-created" class="text-gray-800 font-medium cursor-pointer select-none">
                                        I've created and verified my developer account
                                    </label>
                                </div>
                            </div>

                            <!-- Step 3: Create Twitter App -->
                            <div v-show="currentStep === 3" class="space-y-6 animate-fade-in">
                                <div>
                                    <h3 class="text-xl font-bold text-gray-900 mb-2">Create Your Twitter App</h3>
                                    <p class="text-gray-600">Now let's create an app in the Developer Portal.</p>
                                </div>

                                <div class="bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-xl p-6 space-y-5">
                                    <h4 class="font-semibold text-gray-900">App Configuration Steps:</h4>

                                    <div class="space-y-5">
                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm">1</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-2">Click "Create App" or "New Project"</p>
                                                <p class="text-sm text-gray-600 mb-2">In your developer dashboard, start creating a new app</p>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm">2</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-2">Name your app</p>
                                                <p class="text-sm text-gray-600 mb-2">Choose a descriptive name (e.g., "My AI News App")</p>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm">3</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-2">Set up App Permissions</p>
                                                <p class="text-sm text-gray-600 mb-3">Go to "Settings" → "User authentication settings" → "Set up"</p>
                                                <div class="bg-white border border-indigo-200 rounded-lg p-3 space-y-2">
                                                    <div class="flex items-center gap-2">
                                                        <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                        </svg>
                                                        <span class="text-sm font-medium text-gray-800">Enable "OAuth 1.0a"</span>
                                                    </div>
                                                    <div class="flex items-center gap-2">
                                                        <svg class="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                        </svg>
                                                        <span class="text-sm font-medium text-gray-800">Permissions: "Read and Write"</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm">4</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-2">Set Callback URL</p>
                                                <p class="text-sm text-gray-600 mb-3">Copy and paste this URL exactly:</p>
                                                <div class="bg-white border-2 border-indigo-300 rounded-lg p-3">
                                                    <div class="flex items-center justify-between gap-2">
                                                        <code class="text-sm font-mono text-gray-800 flex-1 break-all">{{ callbackUrl }}</code>
                                                        <button @click="copyToClipboard(callbackUrl, 'callback')"
                                                                class="flex-shrink-0 px-3 py-1.5 bg-indigo-100 hover:bg-indigo-200 text-indigo-700 rounded-md transition-colors text-sm font-medium flex items-center gap-1">
                                                            <svg v-if="copied === 'callback'" class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                                            </svg>
                                                            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                                                            </svg>
                                                            {{ copied === 'callback' ? 'Copied!' : 'Copy' }}
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div class="flex gap-4">
                                            <div class="flex-shrink-0 w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm">5</div>
                                            <div class="flex-1 pt-1">
                                                <p class="text-gray-800 font-medium mb-2">Set Website URL (optional)</p>
                                                <p class="text-sm text-gray-600 mb-2">You can use your app URL or any valid website</p>
                                                <div class="bg-white border border-indigo-200 rounded-lg p-3">
                                                    <code class="text-sm font-mono text-gray-700">{{ websiteUrl }}</code>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="flex items-center gap-3 pt-4">
                                    <input type="checkbox"
                                           id="app-created"
                                           v-model="wizardData.appCreated"
                                           class="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 focus:ring-2">
                                    <label for="app-created" class="text-gray-800 font-medium cursor-pointer select-none">
                                        I've created my Twitter app with the correct settings
                                    </label>
                                </div>
                            </div>

                            <!-- Step 4: Enter Credentials -->
                            <div v-show="currentStep === 4" class="space-y-6 animate-fade-in">
                                <div>
                                    <h3 class="text-xl font-bold text-gray-900 mb-2">Enter Your API Credentials</h3>
                                    <p class="text-gray-600">Find these in your app's "Keys and Tokens" section.</p>
                                </div>

                                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                                    <div class="flex gap-3">
                                        <svg class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                        <div class="text-sm text-blue-800">
                                            <p class="font-semibold mb-1">Where to find your credentials:</p>
                                            <p>In your Twitter app dashboard → "Keys and Tokens" → Generate "Consumer Keys"</p>
                                        </div>
                                    </div>
                                </div>

                                <form @submit.prevent="validateCredentials" class="space-y-5">
                                    <!-- API Key -->
                                    <div>
                                        <label class="block text-sm font-semibold text-gray-800 mb-2">
                                            API Key (Consumer Key)
                                            <span class="text-red-500">*</span>
                                        </label>
                                        <div class="relative">
                                            <input type="text"
                                                   v-model="wizardData.apiKey"
                                                   @input="validateApiKey"
                                                   @blur="validateApiKey"
                                                   placeholder="Enter your API Key..."
                                                   class="w-full px-4 py-3 pr-12 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                                                   :class="{
                                                       'border-gray-300': !wizardData.apiKey,
                                                       'border-green-400 bg-green-50': validations.apiKey === true,
                                                       'border-red-400 bg-red-50': validations.apiKey === false
                                                   }">
                                            <div class="absolute right-3 top-1/2 -translate-y-1/2">
                                                <svg v-if="validations.apiKey === true" class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                                <svg v-else-if="validations.apiKey === false" class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                            </div>
                                        </div>
                                        <p v-if="!validationErrors.apiKey" class="mt-1.5 text-xs text-gray-500">
                                            Usually 25 characters long (letters, numbers, and special characters)
                                        </p>
                                        <p v-else class="mt-1.5 text-xs text-red-600 flex items-center gap-1">
                                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                                            </svg>
                                            {{ validationErrors.apiKey }}
                                        </p>
                                    </div>

                                    <!-- API Secret -->
                                    <div>
                                        <label class="block text-sm font-semibold text-gray-800 mb-2">
                                            API Secret Key (Consumer Secret)
                                            <span class="text-red-500">*</span>
                                        </label>
                                        <div class="relative">
                                            <input :type="showSecrets.apiSecret ? 'text' : 'password'"
                                                   v-model="wizardData.apiSecret"
                                                   @input="validateApiSecret"
                                                   @blur="validateApiSecret"
                                                   placeholder="Enter your API Secret..."
                                                   class="w-full px-4 py-3 pr-24 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                                                   :class="{
                                                       'border-gray-300': !wizardData.apiSecret,
                                                       'border-green-400 bg-green-50': validations.apiSecret === true,
                                                       'border-red-400 bg-red-50': validations.apiSecret === false
                                                   }">
                                            <div class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                                                <button type="button"
                                                        @click="showSecrets.apiSecret = !showSecrets.apiSecret"
                                                        class="text-gray-400 hover:text-gray-600 transition-colors p-1"
                                                        :aria-label="showSecrets.apiSecret ? 'Hide secret' : 'Show secret'">
                                                    <svg v-if="showSecrets.apiSecret" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"></path>
                                                    </svg>
                                                    <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                                    </svg>
                                                </button>
                                                <svg v-if="validations.apiSecret === true" class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                                <svg v-else-if="validations.apiSecret === false" class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                            </div>
                                        </div>
                                        <p v-if="!validationErrors.apiSecret" class="mt-1.5 text-xs text-gray-500">
                                            Usually 50 characters long. Keep this secret and never share it publicly
                                        </p>
                                        <p v-else class="mt-1.5 text-xs text-red-600 flex items-center gap-1">
                                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                                            </svg>
                                            {{ validationErrors.apiSecret }}
                                        </p>
                                    </div>

                                    <!-- Help Section -->
                                    <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                                        <button type="button"
                                                @click="showHelp = !showHelp"
                                                class="flex items-center justify-between w-full text-left">
                                            <span class="text-sm font-semibold text-gray-800 flex items-center gap-2">
                                                <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                                Where do I find these?
                                            </span>
                                            <svg :class="['w-5 h-5 text-gray-500 transition-transform', showHelp ? 'rotate-180' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                            </svg>
                                        </button>
                                        <div v-if="showHelp" class="mt-4 pt-4 border-t border-gray-300 space-y-3 text-sm text-gray-700">
                                            <div class="flex gap-3">
                                                <div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">1</div>
                                                <p>Go to your Twitter Developer Portal</p>
                                            </div>
                                            <div class="flex gap-3">
                                                <div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">2</div>
                                                <p>Select your app from the dashboard</p>
                                            </div>
                                            <div class="flex gap-3">
                                                <div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">3</div>
                                                <p>Click on "Keys and Tokens" tab</p>
                                            </div>
                                            <div class="flex gap-3">
                                                <div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">4</div>
                                                <p>Find "Consumer Keys" section and click "Regenerate" if needed</p>
                                            </div>
                                            <div class="flex gap-3">
                                                <div class="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">5</div>
                                                <p>Copy both the API Key and API Secret Key</p>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Error Message -->
                                    <div v-if="credentialError" class="bg-red-50 border border-red-200 rounded-lg p-4">
                                        <div class="flex gap-3">
                                            <svg class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                            </svg>
                                            <div class="text-sm text-red-800">
                                                <p class="font-semibold mb-1">Validation Error</p>
                                                <p>{{ credentialError }}</p>
                                            </div>
                                        </div>
                                    </div>
                                </form>
                            </div>

                            <!-- Step 5: Success -->
                            <div v-show="currentStep === 5" class="space-y-6 animate-fade-in">
                                <div class="text-center py-8">
                                    <div class="mx-auto w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mb-6 animate-bounce-slow">
                                        <svg class="w-12 h-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                                        </svg>
                                    </div>
                                    <h3 class="text-3xl font-bold text-gray-900 mb-3">You're All Set!</h3>
                                    <p class="text-gray-600 max-w-md mx-auto mb-2">
                                        Your Twitter account is now connected and ready to use.
                                    </p>
                                    <p v-if="wizardData.twitterUsername" class="text-lg font-semibold text-blue-600 mb-6">
                                        Connected as @{{ wizardData.twitterUsername }}
                                    </p>
                                </div>

                                <div class="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 space-y-4">
                                    <h4 class="font-semibold text-gray-900 text-lg flex items-center gap-2">
                                        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                        What's Next?
                                    </h4>
                                    <div class="space-y-3">
                                        <div class="flex items-start gap-3 bg-white rounded-lg p-4">
                                            <svg class="w-6 h-6 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path>
                                            </svg>
                                            <div>
                                                <p class="font-medium text-gray-900">Create and edit posts</p>
                                                <p class="text-sm text-gray-600">Use our AI-powered editor to craft engaging tweets</p>
                                            </div>
                                        </div>
                                        <div class="flex items-start gap-3 bg-white rounded-lg p-4">
                                            <svg class="w-6 h-6 text-purple-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                                            </svg>
                                            <div>
                                                <p class="font-medium text-gray-900">Schedule posts</p>
                                                <p class="text-sm text-gray-600">Plan your content calendar and publish automatically</p>
                                            </div>
                                        </div>
                                        <div class="flex items-start gap-3 bg-white rounded-lg p-4">
                                            <svg class="w-6 h-6 text-orange-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                                            </svg>
                                            <div>
                                                <p class="font-medium text-gray-900">Track performance</p>
                                                <p class="text-sm text-gray-600">Monitor engagement and optimize your strategy</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                    <div class="flex gap-3">
                                        <svg class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                        <div class="text-sm text-blue-800">
                                            <p class="font-semibold mb-1">Pro Tip</p>
                                            <p>You can manage your Twitter connection anytime from your profile settings.</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                        </div>

                        <!-- Footer Navigation -->
                        <div class="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50 flex-shrink-0">
                            <button v-if="currentStep > 1"
                                    @click="previousStep"
                                    class="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 font-medium transition-colors flex items-center gap-2">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                                </svg>
                                Back
                            </button>
                            <div v-else></div>

                            <button v-if="currentStep < 5"
                                    @click="nextStep"
                                    :disabled="!canProceed"
                                    class="px-6 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg hover:from-blue-600 hover:to-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-sm hover:shadow">
                                {{ currentStep === 4 ? 'Test & Connect' : 'Next Step' }}
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                </svg>
                            </button>
                            <button v-else
                                    @click="finishSetup"
                                    class="px-8 py-2.5 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg hover:from-green-600 hover:to-green-700 font-semibold transition-all flex items-center gap-2 shadow-md hover:shadow-lg">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                </svg>
                                Start Publishing
                            </button>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            isOpen: false,
            currentStep: 1,
            showHelp: false,
            copied: null,
            credentialError: '',

            stepTitles: [
                'Welcome',
                'Developer Account',
                'Create App',
                'API Credentials',
                'Success!'
            ],

            stepLabels: [
                'Start',
                'Account',
                'App',
                'Keys',
                'Done'
            ],

            wizardData: {
                devAccountCreated: false,
                appCreated: false,
                apiKey: '',
                apiSecret: '',
                twitterUsername: ''
            },

            validations: {
                apiKey: null,
                apiSecret: null
            },

            validationErrors: {
                apiKey: '',
                apiSecret: ''
            },

            showSecrets: {
                apiSecret: false
            }
        };
    },
    computed: {
        callbackUrl() {
            const baseUrl = window.location.origin;
            return `${baseUrl}/api/social-media/twitter-oauth1/callback`;
        },

        websiteUrl() {
            return window.location.origin;
        },

        canProceed() {
            switch (this.currentStep) {
                case 1:
                    return true;
                case 2:
                    return this.wizardData.devAccountCreated;
                case 3:
                    return this.wizardData.appCreated;
                case 4:
                    return this.validations.apiKey === true &&
                           this.validations.apiSecret === true;
                case 5:
                    return true;
                default:
                    return false;
            }
        }
    },
    methods: {
        openWizard() {
            this.isOpen = true;
            this.currentStep = 1;
            document.body.style.overflow = 'hidden';
        },

        closeWizard() {
            if (this.currentStep === 5) {
                this.isOpen = false;
                document.body.style.overflow = '';
                this.resetWizard();
            } else {
                if (confirm('Are you sure you want to exit? Your progress will be lost.')) {
                    this.isOpen = false;
                    document.body.style.overflow = '';
                    this.resetWizard();
                }
            }
        },

        resetWizard() {
            this.currentStep = 1;
            this.wizardData = {
                devAccountCreated: false,
                appCreated: false,
                apiKey: '',
                apiSecret: '',
                twitterUsername: ''
            };
            this.validations = {
                apiKey: null,
                apiSecret: null
            };
            this.validationErrors = {
                apiKey: '',
                apiSecret: ''
            };
            this.credentialError = '';
        },

        nextStep() {
            if (!this.canProceed) return;

            if (this.currentStep === 4) {
                // Test credentials before proceeding
                this.testAndSaveCredentials();
            } else {
                this.currentStep++;
            }
        },

        previousStep() {
            if (this.currentStep > 1) {
                this.currentStep--;
            }
        },

        /**
         * Validates API Key with comprehensive checks
         */
        validateApiKey() {
            const key = this.wizardData.apiKey.trim();

            if (!key) {
                this.validations.apiKey = null;
                this.validationErrors.apiKey = '';
                return;
            }

            // Check for placeholder text
            const placeholders = ['your-', 'test', 'placeholder', 'example', 'sample', 'demo', 'xxx', 'key-here', 'api-key'];
            const lowerKey = key.toLowerCase();
            const isPlaceholder = placeholders.some(p => lowerKey.startsWith(p) || lowerKey.includes(p));

            if (isPlaceholder) {
                this.validations.apiKey = false;
                this.validationErrors.apiKey = 'This looks like a placeholder. Please enter your real API key from Twitter.';
                return;
            }

            // Check minimum length
            if (key.length < 15) {
                this.validations.apiKey = false;
                this.validationErrors.apiKey = 'API key is too short. Twitter API keys are typically 25 characters.';
                return;
            }

            // Check for spaces (Twitter keys don't have spaces)
            if (key.includes(' ')) {
                this.validations.apiKey = false;
                this.validationErrors.apiKey = 'API key should not contain spaces. Copy it again from Twitter.';
                return;
            }

            // Valid format - Twitter API keys are alphanumeric with some special chars
            if (!/^[A-Za-z0-9_-]+$/.test(key)) {
                this.validations.apiKey = false;
                this.validationErrors.apiKey = 'API key contains invalid characters. Should only have letters, numbers, hyphens, and underscores.';
                return;
            }

            // All checks passed
            this.validations.apiKey = true;
            this.validationErrors.apiKey = '';
        },

        /**
         * Validates API Secret with comprehensive checks
         */
        validateApiSecret() {
            const secret = this.wizardData.apiSecret.trim();

            if (!secret) {
                this.validations.apiSecret = null;
                this.validationErrors.apiSecret = '';
                return;
            }

            // Check for placeholder text
            const placeholders = ['your-', 'test', 'placeholder', 'example', 'sample', 'demo', 'xxx', 'secret-here', 'api-secret'];
            const lowerSecret = secret.toLowerCase();
            const isPlaceholder = placeholders.some(p => lowerSecret.startsWith(p) || lowerSecret.includes(p));

            if (isPlaceholder) {
                this.validations.apiSecret = false;
                this.validationErrors.apiSecret = 'This looks like a placeholder. Please enter your real API secret from Twitter.';
                return;
            }

            // Check minimum length
            if (secret.length < 30) {
                this.validations.apiSecret = false;
                this.validationErrors.apiSecret = 'API secret is too short. Twitter API secrets are typically 50 characters.';
                return;
            }

            // Check for spaces (Twitter secrets don't have spaces)
            if (secret.includes(' ')) {
                this.validations.apiSecret = false;
                this.validationErrors.apiSecret = 'API secret should not contain spaces. Copy it again from Twitter.';
                return;
            }

            // Valid format - Twitter API secrets are alphanumeric with some special chars
            if (!/^[A-Za-z0-9_-]+$/.test(secret)) {
                this.validations.apiSecret = false;
                this.validationErrors.apiSecret = 'API secret contains invalid characters. Should only have letters, numbers, hyphens, and underscores.';
                return;
            }

            // All checks passed
            this.validations.apiSecret = true;
            this.validationErrors.apiSecret = '';
        },

        async testAndSaveCredentials() {
            this.credentialError = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Save credentials to backend
                const response = await axios.post("/api/user/twitter", {
                withCredentials: true
            });

                if (response.data.success) {
                    // Store username if provided
                    if (response.data.username) {
                        this.wizardData.twitterUsername = response.data.username;
                    }

                    // Move to success step
                    this.currentStep = 5;
                } else {
                    throw new Error(response.data.message || 'Failed to save credentials');
                }
            } catch (error) {
                console.error('Error saving credentials:', error);

                if (error.response?.status === 401) {
                    this.credentialError = 'Invalid credentials. The API Key and Secret you entered are not valid. Please check them in the Twitter Developer Portal and try again.';
                } else if (error.response?.data?.detail) {
                    this.credentialError = error.response.data.detail;
                } else if (error.message === 'Network Error') {
                    this.credentialError = 'Network error. Please check your internet connection and try again.';
                } else {
                    this.credentialError = 'Failed to connect to Twitter. Please verify your credentials and try again.';
                }
            }
        },

        finishSetup() {
            this.isOpen = false;
            document.body.style.overflow = '';

            // Emit event or reload page to show connected state
            this.$emit('setup-complete');

            // Refresh the page to show updated connection status
            setTimeout(() => {
                window.location.reload();
            }, 500);
        },

        async copyToClipboard(text, type) {
            try {
                await navigator.clipboard.writeText(text);
                this.copied = type;

                setTimeout(() => {
                    this.copied = null;
                }, 2000);
            } catch (error) {
                console.error('Failed to copy:', error);
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);

                this.copied = type;
                setTimeout(() => {
                    this.copied = null;
                }, 2000);
            }
        },

    }
};

// Register component globally if Vue is available
if (typeof window !== 'undefined' && window.Vue) {
    const app = window.Vue.createApp({});
    app.component('twitter-oauth-setup-wizard', TwitterOAuthSetupWizard);
}
