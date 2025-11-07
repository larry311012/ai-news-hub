<!-- Instagram Tab Editor Component -->
<!-- This component integrates seamlessly into post-edit.html -->

<template>
    <div class="instagram-editor">
        <!-- Desktop: Side-by-side layout -->
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">

            <!-- LEFT: Image Section (60% / 3 cols) -->
            <div class="lg:col-span-3">
                <div class="bg-white rounded-lg border border-gray-200 p-6">
                    <!-- Section Header -->
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-sm font-medium text-gray-700 flex items-center">
                            <svg class="w-5 h-5 mr-2 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            Instagram Image
                        </h3>
                        <span v-if="instagramData.image" class="text-xs text-gray-500">
                            {{ aspectRatioDisplay }}
                        </span>
                    </div>

                    <!-- STATE: Empty State -->
                    <div v-if="!instagramData.image && !instagramData.generatingImage && !instagramData.imageError"
                         class="aspect-square bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50 rounded-2xl flex flex-col items-center justify-center border-2 border-dashed border-gray-300 hover:border-purple-400 transition-colors cursor-pointer"
                         @click="generateInstagramImage">

                        <!-- Instagram gradient icon -->
                        <div class="w-20 h-20 bg-gradient-to-br from-purple-500 via-pink-500 to-orange-500 rounded-3xl p-4 mb-6">
                            <svg class="w-full h-full text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        </div>

                        <h3 class="text-lg font-semibold text-gray-900 mb-2">No Image Yet</h3>
                        <p class="text-sm text-gray-600 text-center max-w-xs mb-6 px-4">
                            Generate a stunning AI image for your Instagram post
                        </p>

                        <button @click.stop="generateInstagramImage"
                                class="px-6 py-3 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-600 text-white font-semibold rounded-lg hover:shadow-lg transform hover:scale-105 transition-all">
                            <span class="flex items-center">
                                <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Generate Image
                            </span>
                        </button>
                    </div>

                    <!-- STATE: Loading State -->
                    <div v-else-if="instagramData.generatingImage"
                         :class="aspectRatioClass"
                         class="bg-gradient-to-br from-purple-100 via-pink-100 to-orange-100 rounded-2xl overflow-hidden relative">

                        <!-- Animated shimmer effect -->
                        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-50"
                             style="animation: shimmer 2s infinite;">
                        </div>

                        <!-- Loading spinner overlay -->
                        <div class="absolute inset-0 flex flex-col items-center justify-center bg-white bg-opacity-90">
                            <!-- Spinning Instagram logo -->
                            <div class="relative w-20 h-20 mb-4">
                                <svg class="animate-spin w-full h-full" viewBox="0 0 24 24">
                                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" style="stroke: #833AB4;"></circle>
                                    <path class="opacity-75" fill="url(#instagram-gradient)" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                    <defs>
                                        <linearGradient id="instagram-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" style="stop-color:#833AB4"/>
                                            <stop offset="50%" style="stop-color:#FD1D1D"/>
                                            <stop offset="100%" style="stop-color:#F77737"/>
                                        </linearGradient>
                                    </defs>
                                </svg>
                            </div>

                            <p class="text-base font-semibold text-gray-900 mb-2">Generating your image...</p>
                            <p class="text-sm text-gray-600">AI is crafting the perfect visual</p>

                            <!-- Progress indicator -->
                            <div class="w-48 h-2 bg-gray-200 rounded-full mt-4 overflow-hidden">
                                <div class="h-full bg-gradient-to-r from-purple-600 via-pink-600 to-orange-600 animate-pulse"
                                     :style="{ width: generationProgress + '%' }">
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- STATE: Generated State -->
                    <div v-else-if="instagramData.image"
                         class="relative group">
                        <!-- Image container with aspect ratio -->
                        <div :class="aspectRatioClass"
                             class="rounded-2xl overflow-hidden shadow-lg relative">

                            <!-- The generated image -->
                            <img :src="instagramData.image.url"
                                 :alt="instagramData.image.alt || 'Generated Instagram image'"
                                 class="w-full h-full object-cover image-reveal"
                                 @load="onImageLoad">

                            <!-- Success checkmark overlay (appears briefly) -->
                            <div v-if="instagramData.showSuccessCheckmark"
                                 class="absolute inset-0 bg-green-600 bg-opacity-80 flex items-center justify-center fade-in">
                                <svg class="w-16 h-16 text-white success-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                        </div>

                        <!-- Floating action toolbar (appears on hover) -->
                        <div class="absolute bottom-4 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <div class="flex items-center space-x-2 bg-white rounded-full shadow-xl px-3 py-2 backdrop-blur-sm bg-opacity-95">

                                <!-- Regenerate -->
                                <button @click="regenerateInstagramImage"
                                        title="Regenerate Image"
                                        :disabled="instagramData.generatingImage"
                                        class="p-2 text-purple-600 hover:bg-purple-50 rounded-full transition-colors disabled:opacity-50">
                                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                    </svg>
                                </button>

                                <!-- Edit Prompt -->
                                <button @click="instagramData.showPromptEditor = true"
                                        title="Edit Prompt"
                                        class="p-2 text-blue-600 hover:bg-blue-50 rounded-full transition-colors">
                                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                    </svg>
                                </button>

                                <!-- Upload Alternative -->
                                <button @click="triggerFileUpload"
                                        title="Upload Image"
                                        class="p-2 text-green-600 hover:bg-green-50 rounded-full transition-colors">
                                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                </button>

                                <!-- Aspect Ratio -->
                                <div class="relative">
                                    <button @click="instagramData.showAspectMenu = !instagramData.showAspectMenu"
                                            title="Aspect Ratio"
                                            class="p-2 text-orange-600 hover:bg-orange-50 rounded-full transition-colors">
                                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                        </svg>
                                    </button>

                                    <!-- Aspect ratio dropdown -->
                                    <div v-if="instagramData.showAspectMenu"
                                         @click.stop
                                         class="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-white rounded-lg shadow-xl py-1 min-w-[140px] border border-gray-200 z-10">
                                        <button @click="setAspectRatio('square')"
                                                :class="instagramData.aspectRatio === 'square' ? 'bg-purple-50 text-purple-700' : 'text-gray-700'"
                                                class="w-full px-4 py-2 text-sm hover:bg-gray-50 transition-colors text-left flex items-center justify-between">
                                            <span>Square</span>
                                            <span class="text-xs text-gray-500">1:1</span>
                                        </button>
                                        <button @click="setAspectRatio('portrait')"
                                                :class="instagramData.aspectRatio === 'portrait' ? 'bg-purple-50 text-purple-700' : 'text-gray-700'"
                                                class="w-full px-4 py-2 text-sm hover:bg-gray-50 transition-colors text-left flex items-center justify-between">
                                            <span>Portrait</span>
                                            <span class="text-xs text-gray-500">4:5</span>
                                        </button>
                                        <button @click="setAspectRatio('landscape')"
                                                :class="instagramData.aspectRatio === 'landscape' ? 'bg-purple-50 text-purple-700' : 'text-gray-700'"
                                                class="w-full px-4 py-2 text-sm hover:bg-gray-50 transition-colors text-left flex items-center justify-between">
                                            <span>Landscape</span>
                                            <span class="text-xs text-gray-500">16:9</span>
                                        </button>
                                    </div>
                                </div>

                                <!-- Download -->
                                <button @click="downloadImage"
                                        title="Download Image"
                                        class="p-2 text-pink-600 hover:bg-pink-50 rounded-full transition-colors">
                                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                </button>
                            </div>
                        </div>

                        <!-- Aspect ratio badge -->
                        <div class="absolute top-4 right-4 bg-black bg-opacity-60 text-white text-xs px-3 py-1.5 rounded-full backdrop-blur-sm font-medium">
                            {{ aspectRatioDisplay }}
                        </div>
                    </div>

                    <!-- STATE: Error State -->
                    <div v-else-if="instagramData.imageError"
                         class="aspect-square bg-red-50 rounded-2xl flex flex-col items-center justify-center border-2 border-red-200 p-8">

                        <!-- Error icon with shake animation -->
                        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4 animate-shake">
                            <svg class="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>

                        <h3 class="text-lg font-semibold text-red-900 mb-2">Generation Failed</h3>
                        <p class="text-sm text-red-700 text-center max-w-xs mb-6" v-text="instagramData.imageError"></p>

                        <button @click="retryGenerateImage"
                                class="px-6 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors">
                            Try Again
                        </button>
                    </div>

                    <!-- Hidden file input for upload -->
                    <input ref="fileInput"
                           type="file"
                           accept="image/*"
                           @change="handleFileUpload"
                           class="hidden">
                </div>
            </div>

            <!-- RIGHT: Caption Section (40% / 2 cols) -->
            <div class="lg:col-span-2">
                <div class="bg-white rounded-lg border border-gray-200 p-6 space-y-6">

                    <!-- Caption textarea -->
                    <div>
                        <label for="instagram-caption" class="block text-sm font-medium text-gray-700 mb-2 flex items-center">
                            <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Instagram Caption
                        </label>

                        <textarea
                            id="instagram-caption"
                            v-model="content"
                            @input="handleContentChange"
                            rows="10"
                            maxlength="2300"
                            :class="[
                                'w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:border-transparent text-sm resize-none',
                                validationState === 'error' ? 'border-red-300 focus:ring-red-500 bg-red-50' :
                                validationState === 'warning' ? 'border-yellow-300 focus:ring-yellow-500 bg-yellow-50' :
                                'border-gray-300 focus:ring-purple-500'
                            ]"
                            placeholder="Write your Instagram caption here... ✨&#10;&#10;Use emojis and hashtags to engage your audience!"
                        ></textarea>

                        <!-- Character counter & actions -->
                        <div class="flex justify-between items-center mt-2">
                            <div class="text-sm" :class="validationClass">
                                <span class="font-medium">{{ content.length }}</span>
                                <span class="text-gray-500"> / 2200</span>
                                <span v-if="validationState === 'warning'" class="ml-2 text-yellow-600">
                                    ⚠️ {{ 2200 - content.length }} chars left
                                </span>
                                <span v-else-if="validationState === 'error'" class="ml-2 text-red-600">
                                    ❌ {{ content.length - 2200 }} chars over
                                </span>
                            </div>

                            <!-- Quick actions -->
                            <div class="flex items-center space-x-1">
                                <button @click="addEmoji"
                                        class="p-1.5 text-2xl hover:bg-purple-50 rounded transition-colors"
                                        title="Add emoji">
                                    😊
                                </button>
                                <button @click="suggestHashtags"
                                        :disabled="loadingHashtags"
                                        class="p-1.5 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded transition-colors disabled:opacity-50"
                                        title="Suggest hashtags">
                                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Caption preview -->
                    <div class="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                        <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center">
                            <svg class="w-4 h-4 mr-2 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                                <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                            </svg>
                            Instagram Preview
                        </h4>
                        <div class="text-sm text-gray-900 bg-white rounded-lg p-3">
                            <p class="line-clamp-3 whitespace-pre-wrap break-words"
                               v-text="content || 'Your caption preview will appear here...'"></p>
                            <button v-if="content && content.split('\n').length > 3"
                                    class="text-purple-600 text-xs mt-1 hover:underline">
                                ...more
                            </button>
                        </div>
                    </div>

                    <!-- Hashtag suggestions -->
                    <div>
                        <div class="flex items-center justify-between mb-2">
                            <h4 class="text-sm font-medium text-gray-700">Suggested Hashtags</h4>
                            <button @click="refreshHashtags"
                                    :disabled="loadingHashtags"
                                    class="text-xs text-purple-600 hover:text-purple-700 disabled:opacity-50 flex items-center">
                                <svg class="w-3 h-3 mr-1" :class="{ 'animate-spin': loadingHashtags }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Refresh
                            </button>
                        </div>

                        <div class="flex flex-wrap gap-2">
                            <button v-for="tag in instagramData.suggestedHashtags"
                                    :key="tag"
                                    @click="addHashtag(tag)"
                                    class="px-3 py-1.5 text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-full transition-colors inline-flex items-center">
                                {{ tag }}
                                <svg class="w-3 h-3 ml-1 opacity-0 group-hover:opacity-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Prompt Editor Modal -->
        <div v-if="instagramData.showPromptEditor"
             class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 fade-in"
             @click.self="instagramData.showPromptEditor = false">
            <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 slide-up">
                <div class="p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold text-gray-900">Customize Image Prompt</h3>
                        <button @click="instagramData.showPromptEditor = false"
                                class="text-gray-400 hover:text-gray-600 transition-colors">
                            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <p class="text-sm text-gray-600 mb-4">
                        Customize the AI prompt to generate your perfect Instagram image. Be specific about style, mood, colors, and composition.
                    </p>

                    <!-- Prompt textarea -->
                    <textarea
                        v-model="instagramData.imagePrompt"
                        rows="5"
                        class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm resize-none mb-4"
                        placeholder="Example: A vibrant sunset over mountains, cinematic lighting, warm colors, professional photography, 4k quality"
                    ></textarea>

                    <!-- Prompt style suggestions -->
                    <div class="mb-6">
                        <h4 class="text-sm font-medium text-gray-700 mb-2">Quick Styles</h4>
                        <div class="flex flex-wrap gap-2">
                            <button v-for="style in instagramData.promptStyles"
                                    :key="style"
                                    @click="appendPromptStyle(style)"
                                    class="px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors">
                                {{ style }}
                            </button>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex space-x-3">
                        <button @click="generateWithCustomPrompt"
                                :disabled="!instagramData.imagePrompt || instagramData.generatingImage"
                                class="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all">
                            {{ instagramData.generatingImage ? 'Generating...' : 'Generate Image' }}
                        </button>
                        <button @click="instagramData.showPromptEditor = false"
                                :disabled="instagramData.generatingImage"
                                class="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* Additional animations for Instagram editor */
@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

@keyframes shake {
    0%, 100% { transform: translateX(0); }
    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
    20%, 40%, 60%, 80% { transform: translateX(5px); }
}

.animate-shake {
    animation: shake 0.5s ease-in-out;
}

@keyframes imageReveal {
    from {
        opacity: 0;
        transform: scale(0.95);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

.image-reveal {
    animation: imageReveal 0.6s ease-out;
}

@keyframes successPulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.1); opacity: 0.9; }
}

.success-pulse {
    animation: successPulse 0.6s ease-in-out;
}

/* Line clamp utility (for caption preview) */
.line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
