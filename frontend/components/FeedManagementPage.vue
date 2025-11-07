<template>
    <div class="min-h-screen bg-gray-50">
        <!-- Header with Stats -->
        <div class="bg-white border-b border-gray-200">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <!-- Back button and title -->
                <div class="mb-6">
                    <button @click="goBack" class="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors mb-4">
                        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to News Feed
                    </button>
                    <h1 class="text-2xl font-bold text-gray-900">My News Sources</h1>
                    <p class="mt-1 text-sm text-gray-600">
                        Manage your custom news feeds and sources
                    </p>
                </div>

                <!-- Stats Dashboard -->
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <!-- Total Sources -->
                    <div class="bg-white rounded-lg border border-gray-200 p-4">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <svg class="h-8 w-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                                </svg>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Total Sources</dt>
                                    <dd class="text-2xl font-semibold text-gray-900">{{ totalFeeds }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>

                    <!-- Active Sources -->
                    <div class="bg-white rounded-lg border border-gray-200 p-4">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <svg class="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Active</dt>
                                    <dd class="text-2xl font-semibold text-green-600">{{ activeFeeds }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>

                    <!-- Needs Attention -->
                    <div class="bg-white rounded-lg border border-gray-200 p-4">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <svg class="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Needs Attention</dt>
                                    <dd class="text-2xl font-semibold text-red-600">{{ errorFeeds }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>

                    <!-- Items Today -->
                    <div class="bg-white rounded-lg border border-gray-200 p-4">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <svg class="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                                </svg>
                            </div>
                            <div class="ml-5 w-0 flex-1">
                                <dl>
                                    <dt class="text-sm font-medium text-gray-500 truncate">Items Today</dt>
                                    <dd class="text-2xl font-semibold text-blue-600">{{ itemsFetchedToday }}</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Bar -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <!-- Search Input -->
                <div class="w-full sm:w-96">
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </div>
                        <input
                            v-model="searchQuery"
                            type="text"
                            placeholder="Search sources..."
                            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                        />
                    </div>
                </div>

                <!-- Add Source Button -->
                <button
                    @click="$emit('add-source')"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                >
                    <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                    Add Source
                </button>
            </div>
        </div>

        <!-- Feed List -->
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
            <!-- Loading State -->
            <div v-if="loading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div v-for="i in 6" :key="i" class="bg-white rounded-lg border border-gray-200 p-4">
                    <div class="animate-pulse">
                        <div class="flex items-start space-x-3">
                            <div class="h-8 w-8 bg-gray-200 rounded"></div>
                            <div class="flex-1">
                                <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                                <div class="h-3 bg-gray-200 rounded w-full"></div>
                            </div>
                        </div>
                        <div class="mt-4 grid grid-cols-3 gap-4">
                            <div class="h-8 bg-gray-200 rounded"></div>
                            <div class="h-8 bg-gray-200 rounded"></div>
                            <div class="h-8 bg-gray-200 rounded"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Empty State -->
            <div v-else-if="filteredFeeds.length === 0" class="text-center py-12">
                <svg class="mx-auto h-16 w-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                </svg>
                <h3 class="mt-4 text-lg font-semibold text-gray-900">
                    {{ searchQuery ? 'No sources found' : 'No news sources yet' }}
                </h3>
                <p class="mt-2 text-sm text-gray-600">
                    {{ searchQuery ? 'Try adjusting your search.' : 'Add your first source to start collecting articles' }}
                </p>
                <button
                    v-if="!searchQuery"
                    @click="$emit('add-source')"
                    class="mt-6 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                    Add Source
                </button>
            </div>

            <!-- Feed Grid -->
            <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <slot name="feed-card" v-for="feed in filteredFeeds" :feed="feed" :key="feed.id"></slot>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: 'FeedManagementPage',
    props: {
        feeds: {
            type: Array,
            default: () => []
        },
        totalFeeds: {
            type: Number,
            default: 0
        },
        activeFeeds: {
            type: Number,
            default: 0
        },
        errorFeeds: {
            type: Number,
            default: 0
        },
        itemsFetchedToday: {
            type: Number,
            default: 0
        },
        loading: {
            type: Boolean,
            default: false
        }
    },
    emits: ['add-source'],
    data() {
        return {
            searchQuery: ''
        };
    },
    computed: {
        filteredFeeds() {
            if (!this.searchQuery) return this.feeds;

            const query = this.searchQuery.toLowerCase();
            return this.feeds.filter(feed =>
                feed.feed_name.toLowerCase().includes(query) ||
                (feed.feed_description && feed.feed_description.toLowerCase().includes(query))
            );
        }
    },
    methods: {
        goBack() {
            window.location.href = '/index.html';
        }
    }
};
</script>

<style scoped>
/* Animations */
@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}

.animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Line clamp for descriptions */
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
