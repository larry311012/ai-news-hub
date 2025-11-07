// Social Media OAuth Connection Component
// User-facing component for connecting personal social media accounts
const SocialMediaConnect = {
    name: 'SocialMediaConnect',
    template: `
        <div class="space-y-6">
            <!-- Header Section -->
            <div class="text-center">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 mb-4">
                    <svg class="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                </div>
                <h3 class="text-2xl font-bold text-gray-900 mb-2">Connect Your Social Accounts</h3>
                <p class="text-gray-600 max-w-2xl mx-auto">
                    Link your social media accounts to publish AI-generated content directly. Your credentials are encrypted and secure.
                </p>
            </div>

            <!-- Connection Status Overview -->
            <div class="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h4 class="text-lg font-semibold text-gray-900">Connection Status</h4>
                        <p class="text-sm text-gray-600 mt-1">{{ connectedCount }} of {{ platforms.length }} platforms connected</p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <div class="w-32 bg-gray-200 rounded-full h-2">
                            <div class="bg-gradient-to-r from-indigo-600 to-purple-600 h-2 rounded-full transition-all duration-500"
                                 :style="\`width: \${connectionProgress}%\`"></div>
                        </div>
                        <span class="text-sm font-medium text-gray-700">{{ Math.round(connectionProgress) }}%</span>
                    </div>
                </div>

                <!-- Platform Quick View -->
                <div class="flex flex-wrap gap-3">
                    <div v-for="platform in platforms"
                         :key="platform.id"
                         class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all"
                         :class="platform.connected ? 'bg-white shadow-sm' : 'bg-gray-100'">
                        <div :class="[
                            'w-8 h-8 rounded-lg flex items-center justify-center transition-all',
                            platform.connected ? platform.activeBg : 'bg-gray-300'
                        ]">
                            <svg :class="[
                                'w-4 h-4',
                                platform.connected ? 'text-white' : 'text-gray-500'
                            ]" fill="currentColor" viewBox="0 0 24 24" v-html="platform.icon">
                            </svg>
                        </div>
                        <span :class="[
                            'text-sm font-medium',
                            platform.connected ? 'text-gray-900' : 'text-gray-500'
                        ]">{{ platform.name }}</span>
                        <svg v-if="platform.connected" class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                </div>
            </div>

            <!-- Success/Error Messages -->
            <transition name="fade">
                <div v-if="successMessage" class="bg-green-50 border-l-4 border-green-500 rounded-lg p-4 animate-slide-in">
                    <div class="flex items-start">
                        <svg class="h-5 w-5 text-green-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                        <p class="text-sm font-medium text-green-800">{{ successMessage }}</p>
                    </div>
                </div>
            </transition>

            <transition name="fade">
                <div v-if="errorMessage" class="bg-red-50 border-l-4 border-red-500 rounded-lg p-4 animate-slide-in">
                    <div class="flex items-start">
                        <svg class="h-5 w-5 text-red-500 mt-0.5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                        <div class="flex-1">
                            <p class="text-sm font-medium text-red-800">{{ errorMessage }}</p>
                        </div>
                        <button @click="errorMessage = ''" class="ml-3 text-red-400 hover:text-red-600">
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </transition>

            <!-- Platform Connection Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div v-for="platform in platforms"
                     :key="platform.id"
                     class="bg-white rounded-xl shadow-sm border-2 transition-all duration-300 hover:shadow-md"
                     :class="platform.connected ? 'border-green-200 bg-gradient-to-br from-white to-green-50' : 'border-gray-200 hover:border-indigo-200'">

                    <!-- Card Header -->
                    <div class="p-6">
                        <div class="flex items-start justify-between mb-4">
                            <div :class="[
                                'w-14 h-14 rounded-2xl flex items-center justify-center shadow-sm transition-all',
                                platform.connected ? platform.activeBg : 'bg-gray-100'
                            ]">
                                <svg :class="[
                                    'w-7 h-7',
                                    platform.connected ? 'text-white' : 'text-gray-400'
                                ]" fill="currentColor" viewBox="0 0 24 24" v-html="platform.icon">
                                </svg>
                            </div>

                            <!-- Status Badge -->
                            <div v-if="platform.connected" class="flex flex-col items-end">
                                <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 shadow-sm">
                                    <span class="w-2 h-2 rounded-full bg-green-500 mr-1.5 animate-pulse"></span>
                                    Connected
                                </span>
                                <span class="text-xs text-gray-500 mt-1">{{ formatDate(platform.connectedAt) }}</span>
                            </div>
                            <span v-else class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600">
                                Not Connected
                            </span>
                        </div>

                        <h4 class="text-lg font-bold text-gray-900 mb-2">{{ platform.name }}</h4>
                        <p class="text-sm text-gray-600 mb-4">{{ platform.description }}</p>

                        <!-- Connected Account Info -->
                        <div v-if="platform.connected && platform.accountInfo"
                             class="bg-white rounded-lg p-3 mb-4 border border-green-100">
                            <div class="flex items-center space-x-3">
                                <div v-if="platform.accountInfo.avatar" class="w-10 h-10 rounded-full overflow-hidden bg-gray-200 flex-shrink-0">
                                    <img :src="platform.accountInfo.avatar" :alt="platform.accountInfo.name" class="w-full h-full object-cover">
                                </div>
                                <div v-else :class="[
                                    'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0',
                                    platform.activeBg
                                ]">
                                    {{ getInitials(platform.accountInfo.name) }}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <p class="text-sm font-semibold text-gray-900 truncate">{{ platform.accountInfo.name }}</p>
                                    <p class="text-xs text-gray-500 truncate">{{ platform.accountInfo.username }}</p>
                                </div>
                            </div>
                        </div>

                        <!-- Benefits List -->
                        <ul v-if="!platform.connected" class="space-y-2 mb-4">
                            <li v-for="benefit in platform.benefits"
                                :key="benefit"
                                class="flex items-start text-xs text-gray-600">
                                <svg class="w-4 h-4 text-green-500 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                                </svg>
                                {{ benefit }}
                            </li>
                        </ul>

                        <!-- Action Buttons -->
                        <div class="space-y-2">
                            <!-- Connect Button -->
                            <button v-if="!platform.connected"
                                    @click="connectPlatform(platform.id)"
                                    :disabled="connecting[platform.id]"
                                    :class="[
                                        'w-full px-4 py-3 rounded-lg font-semibold text-sm transition-all duration-200 shadow-sm',
                                        'flex items-center justify-center space-x-2',
                                        platform.brandButton,
                                        'disabled:opacity-50 disabled:cursor-not-allowed',
                                        'transform hover:scale-105 active:scale-95'
                                    ]">
                                <svg v-if="!connecting[platform.id]" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-11.25a.75.75 0 00-1.5 0v2.5h-2.5a.75.75 0 000 1.5h2.5v2.5a.75.75 0 001.5 0v-2.5h2.5a.75.75 0 000-1.5h-2.5v-2.5z" clip-rule="evenodd"/>
                                </svg>
                                <svg v-else class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <span>{{ connecting[platform.id] ? 'Connecting...' : 'Connect ' + platform.name }}</span>
                            </button>

                            <!-- Connected Actions -->
                            <div v-else class="flex space-x-2">
                                <button @click="testConnection(platform.id)"
                                        :disabled="testing[platform.id]"
                                        class="flex-1 px-4 py-2.5 border-2 border-gray-200 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-50 disabled:opacity-50 transition-all">
                                    <span v-if="!testing[platform.id]">Test</span>
                                    <span v-else>Testing...</span>
                                </button>
                                <button @click="confirmDisconnect(platform.id)"
                                        class="flex-1 px-4 py-2.5 border-2 border-red-200 text-red-600 rounded-lg font-medium text-sm hover:bg-red-50 transition-all">
                                    Disconnect
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Loading State Overlay -->
                    <div v-if="connecting[platform.id]"
                         class="absolute inset-0 bg-white bg-opacity-90 rounded-xl flex items-center justify-center">
                        <div class="text-center">
                            <svg class="animate-spin h-10 w-10 text-indigo-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            <p class="text-sm font-medium text-gray-700">Opening authorization...</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Help Section -->
            <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
                <div class="flex items-start space-x-4">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="flex-1">
                        <h4 class="text-sm font-semibold text-blue-900 mb-2">Why connect your accounts?</h4>
                        <ul class="space-y-1.5 text-sm text-blue-800">
                            <li class="flex items-start">
                                <svg class="w-4 h-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                </svg>
                                <span>Publish AI-generated content directly to your social media</span>
                            </li>
                            <li class="flex items-start">
                                <svg class="w-4 h-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                </svg>
                                <span>Your credentials are encrypted and stored securely</span>
                            </li>
                            <li class="flex items-start">
                                <svg class="w-4 h-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                </svg>
                                <span>You can disconnect anytime without data loss</span>
                            </li>
                            <li class="flex items-start">
                                <svg class="w-4 h-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                </svg>
                                <span>We only request the permissions needed to post content</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- Disconnect Confirmation Modal -->
            <div v-if="showDisconnectModal"
                 class="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50 p-4"
                 @click.self="showDisconnectModal = false">
                <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 transform transition-all animate-slide-in">
                    <div class="flex items-start mb-4">
                        <div class="flex-shrink-0">
                            <div class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                                <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                            </div>
                        </div>
                        <div class="ml-4 flex-1">
                            <h3 class="text-lg font-semibold text-gray-900 mb-2">
                                Disconnect {{ platformToDisconnect ? getPlatformName(platformToDisconnect) : '' }}?
                            </h3>
                            <p class="text-sm text-gray-600 mb-4">
                                You won't be able to publish to this platform until you reconnect. Your posts and settings will be preserved.
                            </p>

                            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                                <div class="flex items-start">
                                    <svg class="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                                    </svg>
                                    <p class="text-xs text-yellow-800">This will revoke access to your {{ platformToDisconnect ? getPlatformName(platformToDisconnect) : '' }} account.</p>
                                </div>
                            </div>

                            <div class="flex space-x-3">
                                <button @click="disconnectPlatform"
                                        :disabled="disconnecting"
                                        class="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg font-semibold text-sm hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm">
                                    <span v-if="!disconnecting">Disconnect</span>
                                    <span v-else class="flex items-center justify-center">
                                        <svg class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Disconnecting...
                                    </span>
                                </button>
                                <button @click="showDisconnectModal = false"
                                        class="flex-1 px-4 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:bg-gray-50 transition-all">
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            platforms: [
                {
                    id: 'twitter',
                    name: 'Twitter / X',
                    description: 'Share concise updates and engage with your audience',
                    icon: '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>',
                    activeBg: 'bg-black',
                    brandButton: 'bg-black hover:bg-gray-800 text-white',
                    connected: false,
                    connectedAt: null,
                    accountInfo: null,
                    benefits: [
                        'Auto-post tweets up to 280 characters',
                        'Schedule posts for optimal engagement',
                        'Track performance metrics'
                    ]
                },
                {
                    id: 'linkedin',
                    name: 'LinkedIn',
                    description: 'Build your professional network and share insights',
                    icon: '<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>',
                    activeBg: 'bg-blue-600',
                    brandButton: 'bg-blue-600 hover:bg-blue-700 text-white',
                    connected: false,
                    connectedAt: null,
                    accountInfo: null,
                    benefits: [
                        'Share professional content and articles',
                        'Reach your network with rich posts',
                        'Build your thought leadership'
                    ]
                },
                {
                    id: 'threads',
                    name: 'Threads',
                    description: 'Join conversations on Meta\'s text-based platform',
                    icon: '<path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.704-1.488 0-2.743-.546-3.625-1.577a5.688 5.688 0 0 1-1.081-2.174c-.288-.901-.438-1.886-.438-2.936 0-1.043.156-2.03.465-2.935.29-.852.703-1.613 1.226-2.26.924-1.132 2.141-1.706 3.614-1.706 1.493 0 2.718.573 3.644 1.705.488.598.853 1.326 1.086 2.167l1.01-.548c-.34-.876-.82-1.647-1.429-2.29-1.17-1.238-2.707-1.914-4.562-2.009-.025-.02-.05-.041-.075-.06l-.023-.023c-.878-.834-1.898-1.255-3.034-1.255-1.137 0-2.156.423-3.032 1.258-.866.826-1.313 1.904-1.313 3.203v.989c.032 2.015.827 3.51 2.37 4.45.916.56 1.996.844 3.208.844 1.208 0 2.283-.285 3.197-.845.492-.3.948-.69 1.358-1.163.37-.429.676-.92.91-1.465l.022.012c.01.005.018.012.028.018.464.315.84.693 1.117 1.122.397.614.617 1.34.654 2.157.023.485.012.97-.031 1.452-.095 1.032-.38 1.977-.849 2.813-.698 1.244-1.784 2.202-3.23 2.85-.967.43-2.07.65-3.275.65h-.001z"/>',
                    activeBg: 'bg-gradient-to-br from-purple-600 to-pink-600',
                    brandButton: 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white',
                    connected: false,
                    connectedAt: null,
                    accountInfo: null,
                    benefits: [
                        'Post engaging text-based content',
                        'Connect with Instagram followers',
                        'Join trending conversations'
                    ]
                }
            ],
            connecting: {},
            testing: {},
            disconnecting: false,
            showDisconnectModal: false,
            platformToDisconnect: null,
            successMessage: '',
            errorMessage: ''
        };
    },
    computed: {
        connectedCount() {
            return this.platforms.filter(p => p.connected).length;
        },
        connectionProgress() {
            return (this.connectedCount / this.platforms.length) * 100;
        }
    },
    mounted() {
        // Configure axios to send httpOnly cookies
        axios.defaults.withCredentials = true;

        this.loadConnections();

        // Listen for OAuth callback
        window.addEventListener('message', this.handleOAuthCallback);
    },
    beforeUnmount() {
        window.removeEventListener('message', this.handleOAuthCallback);
    },
    methods: {
        async loadConnections() {
            try {
                if (!token) return;

                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Load connection status for each platform
                for (const platform of this.platforms) {
                    try {
                        const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                        if (response.data.connected) {
                            platform.connected = true;
                            platform.connectedAt = response.data.connected_at;
                            platform.accountInfo = response.data.account_info;
                        }
                    } catch (error) {
                        // Platform not connected - expected for some platforms
                        if (error.response?.status !== 404) {
                            console.error(`Error loading ${platform.id} status:`, error);
                        }
                    }
                }
            } catch (error) {
                console.error('Error loading connections:', error);
            }
        },

        async connectPlatform(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            if (!platform) return;

            this.connecting[platformId] = true;
            this.successMessage = '';
            this.errorMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                // Get OAuth authorization URL
                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                const authUrl = response.data.authorization_url;

                // Open OAuth popup
                const width = 600;
                const height = 700;
                const left = (window.screen.width - width) / 2;
                const top = (window.screen.height - height) / 2;

                const popup = window.open(
                    authUrl,
                    `${platform.name} Authorization`,
                    `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no`
                );

                // Poll for popup close or message
                const pollTimer = setInterval(() => {
                    if (popup.closed) {
                        clearInterval(pollTimer);
                        this.connecting[platformId] = false;
                        this.checkConnectionStatus(platformId);
                    }
                }, 500);

            } catch (error) {
                console.error(`Error connecting to ${platformId}:`, error);
                this.handleError(error, `Failed to connect to ${platform.name}`);
                this.connecting[platformId] = false;
            }
        },

        async checkConnectionStatus(platformId) {
            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await axios.get("/api/user/twitter", {
                withCredentials: true
            });

                const platform = this.platforms.find(p => p.id === platformId);
                if (response.data.connected) {
                    platform.connected = true;
                    platform.connectedAt = response.data.connected_at;
                    platform.accountInfo = response.data.account_info;

                    this.successMessage = `Successfully connected to ${platform.name}!`;
                    setTimeout(() => this.successMessage = '', 5000);
                }
            } catch (error) {
                console.error(`Error checking ${platformId} status:`, error);
            }
        },

        handleOAuthCallback(event) {
            // Handle OAuth callback from popup
            if (event.data && event.data.type === 'oauth-success') {
                const platformId = event.data.platform;
                this.connecting[platformId] = false;
                this.checkConnectionStatus(platformId);
            } else if (event.data && event.data.type === 'oauth-error') {
                this.connecting[event.data.platform] = false;
                this.errorMessage = event.data.message || 'OAuth authorization failed';
            }
        },

        async testConnection(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            if (!platform) return;

            this.testing[platformId] = true;
            this.successMessage = '';
            this.errorMessage = '';

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                const response = await axios.post("/api/user/twitter", {
                withCredentials: true
            });

                if (response.data.success) {
                    this.successMessage = `${platform.name} connection is working perfectly!`;
                    setTimeout(() => this.successMessage = '', 5000);
                }
            } catch (error) {
                console.error(`Error testing ${platformId}:`, error);
                this.handleError(error, `Failed to test ${platform.name} connection`);
            } finally {
                this.testing[platformId] = false;
            }
        },

        confirmDisconnect(platformId) {
            this.platformToDisconnect = platformId;
            this.showDisconnectModal = true;
        },

        async disconnectPlatform() {
            if (!this.platformToDisconnect) return;

            const platform = this.platforms.find(p => p.id === this.platformToDisconnect);
            this.disconnecting = true;

            try {
                const API_BASE_URL = window.API_BASE_URL || 'http://localhost:8000';

                await axios.delete("/api/user/twitter", {
                withCredentials: true
            });

                platform.connected = false;
                platform.connectedAt = null;
                platform.accountInfo = null;

                this.successMessage = `${platform.name} has been disconnected`;
                this.showDisconnectModal = false;
                this.platformToDisconnect = null;

                setTimeout(() => this.successMessage = '', 5000);

            } catch (error) {
                console.error(`Error disconnecting ${this.platformToDisconnect}:`, error);
                this.handleError(error, `Failed to disconnect ${platform.name}`);
            } finally {
                this.disconnecting = false;
            }
        },

        getPlatformName(platformId) {
            const platform = this.platforms.find(p => p.id === platformId);
            return platform ? platform.name : platformId;
        },

        getInitials(name) {
            if (!name) return '?';
            const parts = name.split(' ');
            if (parts.length >= 2) {
                return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
            }
            return name.substring(0, 2).toUpperCase();
        },

        formatDate(dateString) {
            if (!dateString) return 'Recently';
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
            return date.toLocaleDateString();
        },

        handleError(error, defaultMessage) {
            if (error.response) {
                const status = error.response.status;
                const detail = error.response.data?.detail || error.response.data?.message;

                if (status === 401) {
                    this.errorMessage = 'Session expired. Please login again.';
                    setTimeout(() => {
                        window.location.href = 'auth.html';
                    }, 2000);
                } else {
                    this.errorMessage = detail || defaultMessage;
                }
            } else if (error.request) {
                this.errorMessage = 'Cannot connect to server. Please check your connection.';
            } else {
                this.errorMessage = defaultMessage;
            }

            setTimeout(() => this.errorMessage = '', 5000);
        },

    }
};

// Auto-register if Vue is available
if (typeof window !== 'undefined' && window.Vue) {
    const app = window.Vue.createApp({});
    app.component('social-media-connect', SocialMediaConnect);
}
