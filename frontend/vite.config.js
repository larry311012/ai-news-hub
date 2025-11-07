import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import { readdirSync } from 'fs'
import { visualizer } from 'rollup-plugin-visualizer'
import { compression } from 'vite-plugin-compression2'

// Get all HTML files in the root directory for multi-page app
// Exclude test files from production build
const htmlFiles = readdirSync('.').filter(file =>
  file.endsWith('.html') && !file.startsWith('test-')
)
const input = {}

htmlFiles.forEach(file => {
  const name = file.replace('.html', '')
  input[name] = path.resolve(process.cwd(), file)
})

export default defineConfig(({ mode }) => {
  const isProduction = mode === 'production'

  return {
    plugins: [
      vue(),

      // Bundle analysis plugin (only in build mode with ANALYZE env var)
      process.env.ANALYZE && visualizer({
        open: true,
        filename: 'dist/stats.html',
        gzipSize: true,
        brotliSize: true,
        template: 'treemap', // 'sunburst', 'treemap', 'network'
      }),

      // Compression plugins for production
      isProduction && compression({
        algorithm: 'gzip',
        threshold: 1024, // Only compress files > 1KB
        deleteOriginalAssets: false,
      }),

      isProduction && compression({
        algorithm: 'brotliCompress',
        threshold: 1024,
        deleteOriginalAssets: false,
      }),
    ].filter(Boolean),

    root: '.',

    // Define constants that can be used in code
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
      __BUILD_DATE__: JSON.stringify(new Date().toISOString()),
    },

    build: {
      outDir: 'dist',
      assetsDir: 'assets',

      // Asset inlining threshold (4KB - assets smaller than this will be inlined as base64)
      assetsInlineLimit: 4096,

      // Enable CSS code splitting
      cssCodeSplit: true,

      // Source maps for production (hidden to prevent source code exposure)
      sourcemap: isProduction ? 'hidden' : true,

      // Minification
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: isProduction, // Remove console.logs in production
          drop_debugger: true,
          pure_funcs: isProduction ? ['console.log', 'console.info', 'console.debug'] : [],
          passes: 2, // Multiple passes for better compression
        },
        format: {
          comments: false, // Remove all comments
        },
        mangle: {
          safari10: true, // Fix Safari 10 issues
        },
      },

      // Chunk size warnings
      chunkSizeWarningLimit: 500, // Warn if chunk exceeds 500KB

      rollupOptions: {
        input,
        output: {
          // Manual chunks for better caching
          manualChunks: (id) => {
            // Vendor chunks for external dependencies
            if (id.includes('node_modules')) {
              // Split Vue into its own chunk
              if (id.includes('vue')) {
                return 'vendor-vue'
              }
              // Split Axios into its own chunk
              if (id.includes('axios')) {
                return 'vendor-axios'
              }
              // All other node_modules go into vendor chunk
              return 'vendor'
            }

            // Utils into their own chunk (shared across pages)
            if (id.includes('/utils/')) {
              return 'utils'
            }

            // Components into their own chunk
            if (id.includes('/components/')) {
              return 'components'
            }
          },

          // Generate readable chunk names
          chunkFileNames: (chunkInfo) => {
            const name = chunkInfo.name
            return `assets/js/${name}-[hash].js`
          },

          // Generate readable entry names
          entryFileNames: 'assets/js/[name]-[hash].js',

          // Generate readable asset names
          assetFileNames: (assetInfo) => {
            const info = assetInfo.name.split('.')
            const ext = info[info.length - 1]

            if (/\.(png|jpe?g|gif|svg|webp|avif)$/i.test(assetInfo.name)) {
              return `assets/images/[name]-[hash].${ext}`
            }
            if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name)) {
              return `assets/fonts/[name]-[hash].${ext}`
            }
            if (/\.css$/i.test(assetInfo.name)) {
              return `assets/css/[name]-[hash].${ext}`
            }

            return `assets/[name]-[hash].${ext}`
          },
        },

        // Optimize dependencies
        external: [],
      },

      // Modern browsers support (ES2020+ supports top-level await)
      target: 'es2020',

      // Report compressed size
      reportCompressedSize: true,
    },

    server: {
      port: 3000,
      host: true, // Listen on all addresses
      strictPort: true,

      // Enable CORS
      cors: true,

      proxy: {
        '/api': {
          target: process.env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          ws: true, // Enable WebSocket proxying
        }
      },

      // Warm up frequently used files
      warmup: {
        clientFiles: [
          './utils/api-client.js',
          './utils/toast.js',
          './utils/logger.js',
        ],
      },
    },

    // Development optimizations
    optimizeDeps: {
      include: [
        'vue',
        'axios',
      ],
      exclude: [],

      // Force optimize these deps
      force: false,
    },

    resolve: {
      alias: {
        '@': path.resolve(process.cwd(), './'),
        '@components': path.resolve(process.cwd(), './components'),
        '@utils': path.resolve(process.cwd(), './utils'),
        '@assets': path.resolve(process.cwd(), './assets'),
        'vue': 'vue/dist/vue.esm-bundler.js'
      },
      extensions: ['.mjs', '.js', '.ts', '.jsx', '.tsx', '.json', '.vue'],
    },

    // Preview server configuration
    preview: {
      port: 3000,
      host: true,
      strictPort: true,
      cors: true,
    },

    // Performance hints
    performance: {
      hints: isProduction ? 'warning' : false,
      maxAssetSize: 500000, // 500KB
      maxEntrypointSize: 500000, // 500KB
    },
  }
})
