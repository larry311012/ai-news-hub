<template>
    <!-- Modal Overlay -->
    <div
        v-if="show"
        class="fixed inset-0 z-50 overflow-y-auto"
        aria-labelledby="modal-title"
        role="dialog"
        aria-modal="true"
        @click.self="handleClose"
    >
        <!-- Background overlay -->
        <div class="fixed inset-0 bg-black bg-opacity-50 transition-opacity" aria-hidden="true"></div>

        <!-- Modal content -->
        <div class="flex min-h-full items-center justify-center p-4 sm:p-6">
            <div
                class="relative bg-white rounded-lg max-w-2xl w-full mx-auto shadow-xl transform transition-all"
                @click.stop
            >
                <!-- Close button (desktop) -->
                <button
                    @click="handleClose"
                    class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors z-10"
                    aria-label="Close modal"
                >
                    <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>

                <!-- Modal header with step indicator -->
                <div class="border-b border-gray-200 px-6 py-4">
                    <h2 id="modal-title" class="text-xl font-semibold text-gray-900">
                        Add News Source
                    </h2>
                    <div class="mt-3 flex items-center justify-center space-x-2">
                        <div
                            v-for="step in 3"
                            :key="step"
                            class="flex items-center"
                        >
                            <div
                                :class="[
                                    'h-2 w-2 rounded-full transition-all',
                                    currentStep >= step ? 'bg-indigo-600 w-8' : 'bg-gray-300'
                                ]"
                            ></div>
                            <div v-if="step < 3" class="w-8 h-0.5 bg-gray-300 mx-1"></div>
                        </div>
                    </div>
                    <p class="mt-2 text-center text-sm text-gray-600">
                        Step {{ currentStep }} of 3
                    </p>
                </div>

                <!-- Modal body -->
                <div class="px-6 py-6">
                    <!-- Step 1: Choose Method -->
                    <div v-if="currentStep === 1" class="space-y-4">
                        <h3 class="text-lg font-semibold text-gray-900 mb-4">
                            How would you like to add a source?
                        </h3>

                        <!-- Option 1: Website URL (Recommended) -->
                        <div
                            @click="selectedMethod = 'url'"
                            :class="[
                                'option-card cursor-pointer rounded-lg border-2 p-4 transition-all hover:shadow-md',
                                selectedMethod === 'url'
                                    ? 'border-indigo-600 bg-indigo-50'
                                    : 'border-gray-200 hover:border-indigo-300'
                            ]"
                            role="button"
                            tabindex="0"
                            @keypress.enter="selectedMethod = 'url'"
                        >
                            <div class="flex items-start">
                                <svg class="h-6 w-6 text-indigo-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <div class="ml-4 flex-1">
                                    <div class="flex items-center">
                                        <h4 class="font-semibold text-gray-900">Enter Website URL</h4>
                                        <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                            Easiest
                                        </span>
                                    </div>
                                    <p class="text-sm text-gray-600 mt-1">
                                        We'll find feeds automatically (recommended)
                                    </p>
                                </div>
                            </div>
                        </div>

                        <!-- Option 2: RSS Feed URL -->
                        <div
                            @click="selectedMethod = 'rss'"
                            :class="[
                                'option-card cursor-pointer rounded-lg border-2 p-4 transition-all hover:shadow-md',
                                selectedMethod === 'rss'
                                    ? 'border-indigo-600 bg-indigo-50'
                                    : 'border-gray-200 hover:border-indigo-300'
                            ]"
                            role="button"
                            tabindex="0"
                            @keypress.enter="selectedMethod = 'rss'"
                        >
                            <div class="flex items-start">
                                <svg class="h-6 w-6 text-orange-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                                </svg>
                                <div class="ml-4 flex-1">
                                    <h4 class="font-semibold text-gray-900">I have a feed URL</h4>
                                    <p class="text-sm text-gray-600 mt-1">
                                        Enter RSS/Atom feed URL directly
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 2: Discovery & Selection -->
                    <div v-if="currentStep === 2">
                        <!-- For URL method -->
                        <div v-if="selectedMethod === 'url'" class="space-y-4">
                            <div>
                                <label for="website-url" class="block text-sm font-medium text-gray-700 mb-2">
                                    Website URL
                                </label>
                                <input
                                    id="website-url"
                                    v-model="websiteUrl"
                                    type="url"
                                    placeholder="https://techcrunch.com"
                                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                                    @blur="handleDiscovery"
                                    @keypress.enter="handleDiscovery"
                                />
                                <p class="text-xs text-gray-500 mt-1">
                                    Paste any website URL - we'll find available feeds
                                </p>
                            </div>

                            <!-- Discovery in progress -->
                            <div v-if="discovering" class="mt-4 text-center py-8">
                                <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
                                <p class="text-sm text-gray-600 mt-4">Searching for feeds...</p>
                            </div>

                            <!-- Discovered feeds -->
                            <div v-if="!discovering && discoveredFeeds.length > 0" class="mt-4">
                                <p class="text-sm font-medium text-gray-700 mb-3">
                                    Found {{ discoveredFeeds.length }} feed(s):
                                </p>
                                <div class="space-y-2 max-h-64 overflow-y-auto">
                                    <div
                                        v-for="feed in discoveredFeeds"
                                        :key="feed.url"
                                        @click="selectedFeed = feed"
                                        :class="[
                                            'feed-option cursor-pointer rounded-lg border-2 p-3 transition-all hover:shadow-sm',
                                            selectedFeed?.url === feed.url
                                                ? 'border-indigo-600 bg-indigo-50'
                                                : 'border-gray-200 hover:border-indigo-300'
                                        ]"
                                    >
                                        <div class="flex items-start">
                                            <input
                                                type="radio"
                                                :checked="selectedFeed?.url === feed.url"
                                                class="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                                                @click.stop="selectedFeed = feed"
                                            />
                                            <div class="ml-3 flex-1">
                                                <h4 class="font-semibold text-sm text-gray-900">{{ feed.title }}</h4>
                                                <p class="text-xs text-gray-600 mt-1">{{ feed.description }}</p>
                                                <p class="text-xs text-gray-500 mt-1">
                                                    {{ feed.type.toUpperCase() }} • {{ feed.item_count }} items
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- No feeds found -->
                            <div v-if="!discovering && attemptedDiscovery && discoveredFeeds.length === 0" class="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg" role="alert" aria-live="polite">
                                <div class="flex items-start">
                                    <svg class="h-6 w-6 text-yellow-600 flex-shrink-0" aria-label="Warning" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                                    </svg>
                                    <div class="ml-3 flex-1">
                                        <h4 class="text-sm font-semibold text-yellow-800">No feeds found</h4>
                                        <p class="text-xs text-yellow-700 mt-1 leading-relaxed">
                                            We couldn't find any RSS feeds at this website. Try entering the feed URL directly instead.
                                        </p>
                                        <button
                                            @click="switchToRssMethod"
                                            class="text-xs text-indigo-600 underline hover:text-indigo-800 mt-2 inline-block transition-colors duration-150 font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 rounded"
                                        >
                                            Switch to direct URL entry →
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- For RSS method -->
                        <div v-if="selectedMethod === 'rss'" class="space-y-4">
                            <div>
                                <label for="feed-url" class="block text-sm font-medium text-gray-700 mb-2">
                                    Feed URL
                                </label>
                                <input
                                    id="feed-url"
                                    v-model="feedUrl"
                                    type="url"
                                    placeholder="https://techcrunch.com/feed/"
                                    class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                                    @blur="handleValidation"
                                    @keypress.enter="handleValidation"
                                />
                                <p class="text-xs text-gray-500 mt-1">
                                    Paste the RSS, Atom, or JSON feed URL
                                </p>
                            </div>

                            <!-- Validation in progress -->
                            <div v-if="validating" class="mt-4 text-center py-8">
                                <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
                                <p class="text-sm text-gray-600 mt-4">Checking feed...</p>
                            </div>

                            <!-- Validation success -->
                            <div v-if="!validating && validationResult?.is_valid" class="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg" role="status" aria-live="polite">
                                <div class="flex items-start">
                                    <svg class="h-6 w-6 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                    </svg>
                                    <div class="ml-3 flex-1">
                                        <h4 class="text-sm font-semibold text-green-800">Feed validated successfully!</h4>
                                        <p class="text-xs text-green-700 mt-1">
                                            {{ validationResult.feed_metadata?.title || 'Feed' }} •
                                            {{ validationResult.feed_metadata?.item_count || 0 }} items
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <!-- Validation error -->
                            <div v-if="!validating && validationError" class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg" role="alert" aria-live="assertive">
                                <div class="flex items-start">
                                    <svg class="h-6 w-6 text-red-600 flex-shrink-0" aria-label="Error" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                                    </svg>
                                    <div class="ml-3 flex-1">
                                        <h4 class="text-sm font-semibold text-red-800">{{ validationErrorTitle }}</h4>
                                        <p class="text-xs text-red-700 mt-1 leading-relaxed">{{ validationError }}</p>
                                        <button
                                            @click="retryValidation"
                                            class="text-xs text-indigo-600 underline hover:text-indigo-800 mt-2 inline-block transition-colors duration-150 font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 rounded"
                                        >
                                            Try again
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 3: Configure & Preview -->
                    <div v-if="currentStep === 3" class="space-y-4">
                        <h3 class="text-lg font-semibold text-gray-900 mb-4">
                            Configure your source
                        </h3>

                        <!-- Feed Name -->
                        <div>
                            <label for="feed-name" class="block text-sm font-medium text-gray-700 mb-2">
                                Source Name
                            </label>
                            <input
                                id="feed-name"
                                v-model="feedName"
                                type="text"
                                :placeholder="autoDetectedName"
                                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                            />
                            <p class="text-xs text-gray-500 mt-1">
                                Give this source a memorable name
                            </p>
                        </div>

                        <!-- Update Frequency -->
                        <div>
                            <label for="update-frequency" class="block text-sm font-medium text-gray-700 mb-2">
                                Check for updates
                            </label>
                            <select
                                id="update-frequency"
                                v-model.number="updateFrequency"
                                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
                            >
                                <option :value="1800">Every 30 minutes</option>
                                <option :value="3600">Every hour (recommended)</option>
                                <option :value="7200">Every 2 hours</option>
                                <option :value="21600">Every 6 hours</option>
                                <option :value="86400">Once a day</option>
                            </select>
                        </div>

                        <!-- Preview -->
                        <div v-if="previewItems.length > 0" class="border rounded-lg p-4 bg-gray-50">
                            <h4 class="text-sm font-semibold text-gray-900 mb-3">Preview</h4>
                            <div class="space-y-3">
                                <div
                                    v-for="(item, index) in previewItems.slice(0, 3)"
                                    :key="index"
                                    class="text-xs border-b border-gray-200 pb-2 last:border-b-0 last:pb-0"
                                >
                                    <p class="font-medium text-gray-900">{{ item.title }}</p>
                                    <p class="text-gray-600 mt-1">{{ formatDate(item.published_date) }}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Modal footer with navigation buttons -->
                <div class="border-t border-gray-200 px-6 py-4 flex justify-between items-center">
                    <button
                        v-if="currentStep > 1"
                        @click="prevStep"
                        class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all"
                    >
                        Back
                    </button>
                    <div v-else></div>

                    <button
                        v-if="currentStep < 3"
                        @click="nextStep"
                        :disabled="!canProceedToNextStep"
                        class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        Continue
                    </button>
                    <button
                        v-else
                        @click="handleAddFeed"
                        :disabled="adding || !feedName"
                        class="px-6 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        <span v-if="!adding">Add Source</span>
                        <span v-else class="flex items-center">
                            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Adding...
                        </span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'AddSourceModal',
    props: {
        show: {
            type: Boolean,
            default: false
        }
    },
    emits: ['close', 'added'],
    data() {
        return {
            currentStep: 1,
            selectedMethod: null, // 'url' or 'rss'

            // Step 2 data
            websiteUrl: '',
            feedUrl: '',
            discovering: false,
            validating: false,
            discoveredFeeds: [],
            selectedFeed: null,
            validationResult: null,
            validationError: null,
            validationErrorTitle: 'Couldn\'t validate feed',
            attemptedDiscovery: false,

            // Step 3 data
            feedName: '',
            feedDescription: '',
            updateFrequency: 3600,
            previewItems: [],
            adding: false
        };
    },
    computed: {
        canProceedToNextStep() {
            if (this.currentStep === 1) {
                return this.selectedMethod !== null;
            }
            if (this.currentStep === 2) {
                if (this.selectedMethod === 'url') {
                    return this.selectedFeed !== null;
                }
                if (this.selectedMethod === 'rss') {
                    return this.validationResult?.is_valid === true;
                }
            }
            return true;
        },
        autoDetectedName() {
            if (this.selectedMethod === 'url' && this.selectedFeed) {
                return this.selectedFeed.title;
            }
            if (this.selectedMethod === 'rss' && this.validationResult?.feed_metadata) {
                return this.validationResult.feed_metadata.title;
            }
            return 'My News Source';
        }
    },
    watch: {
        show(newVal) {
            if (newVal) {
                // Add keyboard listener when modal opens
                document.addEventListener('keydown', this.handleEscape);
                // Prevent body scroll
                document.body.style.overflow = 'hidden';
            } else {
                // Clean up when modal closes
                document.removeEventListener('keydown', this.handleEscape);
                document.body.style.overflow = '';
            }
        }
    },
    beforeUnmount() {
        // Clean up listeners
        document.removeEventListener('keydown', this.handleEscape);
        document.body.style.overflow = '';
    },
    methods: {
        handleEscape(e) {
            if (e.key === 'Escape') {
                this.handleClose();
            }
        },
        handleClose() {
            if (this.discovering || this.validating || this.adding) {
                // Don't allow closing during async operations
                return;
            }
            this.$emit('close');
            // Reset after a short delay to allow close animation
            setTimeout(() => {
                this.resetModal();
            }, 300);
        },
        nextStep() {
            if (this.canProceedToNextStep) {
                this.currentStep++;

                // If moving to step 3, pre-fill data and fetch preview
                if (this.currentStep === 3) {
                    this.feedName = this.autoDetectedName;
                    if (this.selectedMethod === 'url' && this.selectedFeed) {
                        this.feedDescription = this.selectedFeed.description;
                    } else if (this.selectedMethod === 'rss' && this.validationResult?.feed_metadata) {
                        this.feedDescription = this.validationResult.feed_metadata.description || '';
                    }
                    this.fetchPreview();
                }
            }
        },
        prevStep() {
            if (this.currentStep > 1) {
                this.currentStep--;
            }
        },
        switchToRssMethod() {
            this.selectedMethod = 'rss';
            this.currentStep = 1;
            this.websiteUrl = '';
            this.discoveredFeeds = [];
            this.selectedFeed = null;
            this.attemptedDiscovery = false;
        },
        async handleDiscovery() {
            if (!this.websiteUrl || this.discovering) {
                return;
            }

            this.discovering = true;
            this.attemptedDiscovery = false;
            this.discoveredFeeds = [];
            this.selectedFeed = null;

            try {
                const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
                const response = await fetch('/api/user-feeds/discover', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ website_url: this.websiteUrl })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                this.discoveredFeeds = data.discovered_feeds || [];
                this.attemptedDiscovery = true;

                // Auto-select if only one feed found
                if (this.discoveredFeeds.length === 1) {
                    this.selectedFeed = this.discoveredFeeds[0];
                }
            } catch (error) {
                console.error('Discovery error:', error);
                this.showToast(
                    'Failed to discover feeds. Please check the URL and try again.',
                    'Discovery Failed',
                    'error'
                );
                this.attemptedDiscovery = true;
            } finally {
                this.discovering = false;
            }
        },
        async handleValidation() {
            if (!this.feedUrl || this.validating) {
                return;
            }

            this.validating = true;
            this.validationError = null;
            this.validationResult = null;

            try {
                const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
                const response = await fetch('/api/user-feeds/validate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ feed_url: this.feedUrl })
                });

                const data = await response.json();

                if (response.ok && data.is_valid) {
                    this.validationResult = data;
                    this.validationError = null;
                } else {
                    this.validationResult = null;
                    this.validationError = data.error_message || 'Could not validate this feed. Please check the URL.';
                    this.validationErrorTitle = this.getErrorTitle(data.error_code);
                }
            } catch (error) {
                console.error('Validation error:', error);
                this.validationResult = null;
                this.validationError = 'Could not connect to this feed. Please check the URL and try again.';
                this.validationErrorTitle = 'Connection Failed';
            } finally {
                this.validating = false;
            }
        },
        retryValidation() {
            this.validationError = null;
            this.validationResult = null;
            this.handleValidation();
        },
        getErrorTitle(errorCode) {
            const titles = {
                'not_found': 'Couldn\'t find this feed',
                'malformed': 'This feed has formatting issues',
                'timeout': 'Connection timed out',
                'invalid_structure': 'This doesn\'t look like a valid feed'
            };
            return titles[errorCode] || 'Couldn\'t validate feed';
        },
        async fetchPreview() {
            // Use validation result or selected feed to get preview items
            if (this.selectedMethod === 'rss' && this.validationResult?.feed_metadata) {
                this.previewItems = this.validationResult.feed_metadata.preview_items || [];
            } else if (this.selectedMethod === 'url' && this.selectedFeed) {
                // Preview items might be included in discovery result
                this.previewItems = this.selectedFeed.preview_items || [];
            }
        },
        async handleAddFeed() {
            if (!this.feedName || this.adding) {
                return;
            }

            this.adding = true;

            try {
                const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
                const feedUrl = this.selectedMethod === 'url'
                    ? this.selectedFeed.url
                    : this.feedUrl;

                const response = await fetch('/api/user-feeds', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        feed_url: feedUrl,
                        feed_name: this.feedName,
                        feed_description: this.feedDescription,
                        update_frequency: this.updateFrequency
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to add feed');
                }

                const data = await response.json();

                this.showToast('Source added successfully!', 'Success', 'success');
                this.$emit('added', data.feed);
                this.handleClose();
            } catch (error) {
                console.error('Add feed error:', error);
                this.showToast(
                    error.message || 'Failed to add source. Please try again.',
                    'Error',
                    'error'
                );
            } finally {
                this.adding = false;
            }
        },
        resetModal() {
            this.currentStep = 1;
            this.selectedMethod = null;
            this.websiteUrl = '';
            this.feedUrl = '';
            this.discovering = false;
            this.validating = false;
            this.discoveredFeeds = [];
            this.selectedFeed = null;
            this.validationResult = null;
            this.validationError = null;
            this.validationErrorTitle = 'Couldn\'t validate feed';
            this.attemptedDiscovery = false;
            this.feedName = '';
            this.feedDescription = '';
            this.updateFrequency = 3600;
            this.previewItems = [];
            this.adding = false;
        },
        formatDate(dateString) {
            if (!dateString) return 'Unknown date';
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 60) return `${diffMins} minutes ago`;
            if (diffHours < 24) return `${diffHours} hours ago`;
            if (diffDays < 7) return `${diffDays} days ago`;

            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
            });
        },
        showToast(message, title, type) {
            // Emit event for parent component to handle toast
            // Or use a global toast component if available
            const event = new CustomEvent('show-toast', {
                detail: { message, title, type }
            });
            window.dispatchEvent(event);
        }
    }
};
</script>

<style scoped>
/* Animations */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: scale(0.95);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

.option-card {
    animation: fadeIn 0.2s ease-out;
}

/* Loading spinner */
@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.animate-spin {
    animation: spin 1s linear infinite;
}

/* Smooth transitions */
.transition-all {
    transition: all 0.15s ease-in-out;
}

.transition-colors {
    transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out;
}

/* Focus states for accessibility */
button:focus,
input:focus,
select:focus {
    outline: 2px solid #4F46E5;
    outline-offset: 2px;
}

button:focus:not(:focus-visible),
input:focus:not(:focus-visible),
select:focus:not(:focus-visible) {
    outline: none;
}

/* Disabled states */
button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
}

/* Mobile responsiveness */
@media (max-width: 640px) {
    .max-w-2xl {
        max-width: 100%;
        margin: 0;
        min-height: 100vh;
        border-radius: 0;
    }

    .option-card {
        padding: 1rem;
    }
}

/* Reduced motion for accessibility */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
</style>
