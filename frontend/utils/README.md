# Frontend Utils - Quick Reference Guide

This directory contains reusable utilities that reduce code duplication and improve maintainability.

---

## 📦 Available Utilities

### 1. API Client (`api-client.js`)
Centralized HTTP client for all API communication.

**Features:**
- Automatic retry logic (3 attempts)
- Global error handling
- Request/response interceptors
- File upload support
- Timeout management
- Environment-aware base URL

**Basic Usage:**
```javascript
import apiClient from './utils/api-client.js';

// GET request
const { data } = await apiClient.get('/api/posts');

// POST request
const { data } = await apiClient.post('/api/posts', {
    title: 'My Post',
    content: 'Post content'
});

// PUT request
await apiClient.put('/api/posts/123', { title: 'Updated' });

// DELETE request
await apiClient.delete('/api/posts/123');
```

**File Upload:**
```javascript
// With progress tracking
await apiClient.uploadFile('/api/upload', file, (progress) => {
    console.log(`Upload progress: ${progress}%`);
});
```

**Custom Options:**
```javascript
// Custom timeout (default 30s)
await apiClient.get('/api/slow-endpoint', { timeout: 60000 });

// Disable credentials
await apiClient.post('/api/public', data, { withCredentials: false });

// Custom headers
await apiClient.post('/api/data', data, {
    headers: { 'X-Custom-Header': 'value' }
});
```

**Error Handling:**
Errors are automatically handled and shown to users via toast notifications:
- 401 → Redirect to login
- 403 → "Access denied"
- 429 → "Too many requests"
- 500 → "Server error"
- Network errors → "Check your connection"

---

### 2. Toast Notifications (`toast.js`)
Non-blocking user notification system.

**Features:**
- 4 notification types (success, error, warning, info)
- Auto-dismiss
- Stackable notifications
- Smooth animations
- Mobile-friendly
- Zero dependencies

**Basic Usage:**
```javascript
import { showToast } from './utils/toast.js';

// Success notification
showToast('Saved successfully!', 'success');

// Error notification
showToast('Failed to save', 'error');

// Warning notification
showToast('Please complete all fields', 'warning');

// Info notification
showToast('Processing your request...', 'info');
```

**Custom Duration:**
```javascript
// Show for 5 seconds (default is 3s)
showToast('Important message', 'warning', 5000);

// Quick message (1 second)
showToast('Done!', 'success', 1000);
```

**Convenience Methods:**
```javascript
import { toast } from './utils/toast.js';

toast.success('Operation completed');
toast.error('Something went wrong');
toast.warning('Are you sure?');
toast.info('Loading...');
```

**HTML Usage:**
```html
<script type="module" src="/utils/toast.js"></script>

<script>
    // Available globally as showToast
    showToast('Hello!', 'info');
</script>
```

---

### 3. Logger (`logger.js`)
Production-safe logging with environment awareness.

**Features:**
- Conditional logging (dev vs production)
- Namespace support
- Performance timing
- Grouped logs
- Automatic production silencing

**Basic Usage:**
```javascript
import logger from './utils/logger.js';

// Only logs in development
logger.log('Debug information');
logger.debug('Detailed debug info');

// Always logs (even in production)
logger.error('Critical error occurred');
logger.warn('Warning message');
logger.info('Informational message');
```

**Namespaced Logger:**
```javascript
import { Logger } from './utils/logger.js';

const authLogger = new Logger('Auth');
authLogger.log('User logged in'); // "[Auth] User logged in"

const apiLogger = new Logger('API');
apiLogger.debug('API call started'); // "[API] [DEBUG 2025-10-26T...] API call started"
```

**Advanced Features:**
```javascript
// Group related logs
logger.group('User Login Flow');
logger.log('Step 1: Validate credentials');
logger.log('Step 2: Create session');
logger.log('Step 3: Redirect to dashboard');
logger.groupEnd();

// Performance timing
logger.time('data-fetch');
await fetchData();
logger.timeEnd('data-fetch'); // Logs elapsed time

// Table output for objects/arrays
logger.table([
    { name: 'John', age: 30 },
    { name: 'Jane', age: 25 }
]);
```

**Production Behavior:**
In production, `logger.log()` and `logger.debug()` are silenced. Only `error`, `warn`, and `info` are shown.

---

## 🎯 Migration Guide

### From alert() to showToast()

**Before:**
```javascript
alert('Login successful!');
```

**After:**
```javascript
import { showToast } from './utils/toast.js';
showToast('Login successful!', 'success');
```

### From axios to apiClient

**Before:**
```javascript
import axios from 'axios';

try {
    const response = await axios.post('http://localhost:8000/api/login', data);
    console.log('Success:', response.data);
} catch (error) {
    alert('Error: ' + error.message);
}
```

**After:**
```javascript
import apiClient from './utils/api-client.js';

// Error handling is automatic!
const { data } = await apiClient.post('/api/login', data);
showToast('Login successful!', 'success');
```

### From console.log to logger

**Before:**
```javascript
console.log('User data:', userData);
console.log('API call succeeded');
```

**After:**
```javascript
import logger from './utils/logger.js';

logger.log('User data:', userData); // Only in development
logger.log('API call succeeded'); // Only in development
```

---

## 🎨 Toast Notification Types

### Success (Green)
```javascript
showToast('Post published successfully!', 'success');
```
Use for: Successful operations, confirmations, completions

### Error (Red)
```javascript
showToast('Failed to save post', 'error');
```
Use for: Errors, failures, validation issues

### Warning (Yellow)
```javascript
showToast('Please select at least one platform', 'warning');
```
Use for: Warnings, required actions, confirmations needed

### Info (Blue)
```javascript
showToast('Processing your request...', 'info');
```
Use for: Informational messages, loading states, general notifications

---

## 🔧 Configuration

### API Client Base URL

The API client automatically uses the environment variable:
```javascript
// In .env or .env.local
VITE_API_URL=https://api.example.com
```

Fallback: `http://localhost:8000`

### Toast Duration

Default: 3000ms (3 seconds)

Customize per call:
```javascript
showToast('Quick message', 'info', 1000); // 1 second
showToast('Important message', 'warning', 5000); // 5 seconds
```

### Logger Environment Detection

Automatically detects:
1. `import.meta.env.DEV`
2. `import.meta.env.MODE === 'development'`
3. `process.env.NODE_ENV === 'development'`
4. `localhost` or `127.0.0.1` hostname

---

## 📊 Benefits

### Code Reduction
- **Before:** Duplicated axios config in 21+ files
- **After:** Single api-client.js (194 lines)
- **Savings:** ~80% reduction in API code

### Security
- ✅ No console.log in production (no data exposure)
- ✅ Centralized error handling
- ✅ Automatic timeout protection

### User Experience
- ✅ Non-blocking notifications (28 alert() removed)
- ✅ Consistent error messages
- ✅ Mobile-friendly toast notifications

### Maintainability
- ✅ Single source of truth for API config
- ✅ Easy to update error handling
- ✅ Standardized logging approach

---

## 🐛 Troubleshooting

### Toast not showing?
1. Check that toast.js is imported or included
2. Verify showToast is called correctly
3. Check browser console for errors
4. Ensure Tailwind CSS is loaded (for styling)

### API client not working?
1. Verify VITE_API_URL is set correctly
2. Check network tab in DevTools
3. Verify backend is running
4. Check CORS configuration

### Logger not logging?
1. In production, log() and debug() are silenced (expected)
2. Use error() or warn() for production logs
3. Check environment detection is working

---

## 📝 Examples

### Complete Form Submission Example

```javascript
import apiClient from './utils/api-client.js';
import { showToast } from './utils/toast.js';
import logger from './utils/logger.js';

async function submitForm(formData) {
    try {
        logger.log('Submitting form:', formData);

        // Show loading toast
        showToast('Saving...', 'info', 10000);

        // API call (errors handled automatically)
        const { data } = await apiClient.post('/api/forms', formData);

        logger.log('Form saved:', data);

        // Show success
        showToast('Form saved successfully!', 'success');

        return data;
    } catch (error) {
        logger.error('Form submission failed:', error);
        // Error toast shown automatically by apiClient
        throw error;
    }
}
```

### File Upload with Progress

```javascript
import apiClient from './utils/api-client.js';
import { showToast } from './utils/toast.js';

async function uploadImage(file) {
    try {
        const { data } = await apiClient.uploadFile(
            '/api/upload',
            file,
            (progress) => {
                // Update progress UI
                updateProgressBar(progress);

                if (progress === 100) {
                    showToast('Upload complete!', 'success');
                }
            }
        );

        return data.url;
    } catch (error) {
        showToast('Upload failed', 'error');
        throw error;
    }
}
```

---

## 🚀 Demo

See the interactive demo: `/DEMO_toast_notifications.html`

```bash
cd /Users/ranhui/ai_post/web/frontend
open DEMO_toast_notifications.html
```

---

## 📚 Further Reading

- [Fetch API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [ES6 Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [ARIA Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA)

---

**Created:** October 26, 2025
**Part of:** Epic 5.3 - Frontend Critical Fixes
