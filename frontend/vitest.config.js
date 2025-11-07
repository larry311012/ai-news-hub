import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    // Use happy-dom for faster DOM simulation
    environment: 'happy-dom',

    // Global test setup
    setupFiles: ['./tests/setup.js'],

    // Coverage settings
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        '*.config.js',
        'dist/',
        '*-debug.js',
        '*-backup.js',
        '*.md',
        '*.sh',
        '*.html',
        'components/',  // Vue components require different testing approach
        'js/',
        'settings/',
        'styles/',
        'utils/logger.js'  // Logger is dev-only, hard to test effectively
      ],
      // Thresholds - starting conservative, will increase over time
      lines: 40,
      functions: 40,
      branches: 30,
      statements: 40
    },

    // Test file patterns
    include: ['tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts}'],
    exclude: ['node_modules', 'dist', 'build'],

    // Timeouts
    testTimeout: 10000,
    hookTimeout: 10000,

    // Globals (optional - enables describe, it, expect without imports)
    globals: true
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './')
    }
  }
})
