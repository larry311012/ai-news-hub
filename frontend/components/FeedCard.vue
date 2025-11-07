<template>
    <div class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
        <!-- Header -->
        <div class="flex items-start justify-between">
            <div class="flex items-start space-x-3 flex-1 min-w-0">
                <div class="flex-shrink-0">
                    <svg class="h-8 w-8" :class="iconColor" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 5c7.18 0 13 5.82 13 13M6 11a7 7 0 017 7m-6 0a1 1 0 11-2 0 1 1 0 012 0z" />
                    </svg>
                </div>
                <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-gray-900 truncate" :title="feed.feed_name">
                        {{ feed.feed_name }}
                    </h3>
                    <p class="text-xs text-gray-600 mt-1 line-clamp-2" :title="feed.feed_description">
                        {{ feed.feed_description || 'No description' }}
                    </p>
                </div>
            </div>

            <!-- Status Badge -->
            <span
                :class="statusBadgeClass"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ml-2 flex-shrink-0"
            >
                {{ statusText }}
            </span>
        </div>

        <!-- Stats -->
        <div class="mt-4 grid grid-cols-3 gap-4 text-center">
            <div>
                <p class="text-lg font-semibold text-gray-900">{{ feed.total_items_fetched || 0 }}</p>
                <p class="text-xs text-gray-600">Items</p>
            </div>
            <div>
                <p class="text-lg font-semibold text-gray-900">{{ updateFrequencyText }}</p>
                <p class="text-xs text-gray-600">Updates</p>
            </div>
            <div>
                <p class="text-lg font-semibold text-gray-900">{{ lastFetchedText }}</p>
                <p class="text-xs text-gray-600">Last Check</p>
            </div>
        </div>

        <!-- Error Message (if any) -->
        <div v-if="feed.health_status === 'error' && feed.error_message" class="mt-3 p-2 bg-red-50 rounded border border-red-100">
            <div class="flex">
                <svg class="h-4 w-4 text-red-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p class="ml-2 text-xs text-red-800 flex-1">{{ feed.error_message }}</p>
            </div>
        </div>

        <!-- Actions -->
        <div class="mt-4 flex items-center justify-between border-t border-gray-200 pt-3">
            <div class="flex space-x-2">
                <!-- Test Button -->
                <button
                    @click="$emit('test', feed.id)"
                    class="p-2 text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                    title="Test connection"
                    aria-label="Test feed connection"
                >
                    <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </button>

                <!-- Edit Button -->
                <button
                    @click="$emit('edit', feed.id)"
                    class="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                    title="Edit settings"
                    aria-label="Edit feed settings"
                >
                    <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                </button>
            </div>

            <!-- Delete Button -->
            <button
                @click="handleDelete"
                class="p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                title="Remove source"
                aria-label="Remove this feed"
            >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
            </button>
        </div>
    </div>
</template>

<script>
export default {
    name: 'FeedCard',
    props: {
        feed: {
            type: Object,
            required: true,
            validator: (feed) => {
                return typeof feed.id !== 'undefined' && typeof feed.feed_name === 'string';
            }
        }
    },
    emits: ['test', 'edit', 'delete'],
    computed: {
        statusBadgeClass() {
            const classes = {
                'healthy': 'bg-green-100 text-green-800',
                'warning': 'bg-yellow-100 text-yellow-800',
                'error': 'bg-red-100 text-red-800',
                'unknown': 'bg-gray-100 text-gray-800'
            };
            return classes[this.feed.health_status] || 'bg-gray-100 text-gray-800';
        },
        statusText() {
            const text = {
                'healthy': 'Active',
                'warning': 'Slow',
                'error': 'Error',
                'unknown': 'Unknown'
            };
            return text[this.feed.health_status] || 'Unknown';
        },
        iconColor() {
            const colors = {
                'healthy': 'text-green-600',
                'warning': 'text-yellow-600',
                'error': 'text-red-600',
                'unknown': 'text-gray-400'
            };
            return colors[this.feed.health_status] || 'text-gray-400';
        },
        updateFrequencyText() {
            if (!this.feed.update_frequency) return 'N/A';

            const minutes = this.feed.update_frequency / 60;
            if (minutes < 60) return `${minutes}min`;

            const hours = minutes / 60;
            if (hours < 24) return `${hours}hr`;

            const days = hours / 24;
            return `${days}d`;
        },
        lastFetchedText() {
            if (!this.feed.last_fetched_at) return 'Never';
            return this.timeAgo(this.feed.last_fetched_at);
        }
    },
    methods: {
        timeAgo(date) {
            const now = new Date();
            const then = new Date(date);
            const diffMs = now - then;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);

            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
            return `${Math.floor(diffDays / 365)}y ago`;
        },
        handleDelete() {
            // Confirmation dialog before deletion
            const confirmed = confirm(
                `Are you sure you want to remove "${this.feed.feed_name}"?\n\nThis action cannot be undone.`
            );

            if (confirmed) {
                this.$emit('delete', this.feed.id);
            }
        }
    }
};
</script>

<style scoped>
/* Line clamp utility for multi-line text truncation */
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Smooth transitions */
.transition-shadow {
    transition: box-shadow 0.15s ease-in-out;
}

.transition-colors {
    transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out;
}

/* Focus states for accessibility */
button:focus {
    outline: 2px solid #4F46E5;
    outline-offset: 2px;
}

button:focus:not(:focus-visible) {
    outline: none;
}

/* Hover effects */
button:active {
    transform: scale(0.95);
}
</style>
