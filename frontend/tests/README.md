# Frontend Unit Tests

Comprehensive unit testing suite for AI Post Generator frontend utilities and components using Vitest.

## Overview

- **Test Framework**: Vitest 4.0.3
- **Test Environment**: happy-dom (faster DOM simulation)
- **Coverage Tool**: v8
- **Current Coverage**: 92.75% statements, 80.85% branches

## Test Structure

```
tests/
├── setup.js              # Global test configuration
├── api-client.test.js    # API client tests (26 tests)
├── toast.test.js         # Toast notification tests (39 tests)
├── logger.test.js        # Logger utility tests (17 tests)
└── README.md             # This file
```

## Running Tests

### Run all tests (watch mode)
```bash
npm test
# or
npm run test:watch
```

### Run tests once (CI/CD mode)
```bash
npm run test:run
```

### Generate coverage report
```bash
npm run test:coverage
open coverage/index.html
```

### Run tests with UI
```bash
npm run test:ui
```

## Test Coverage

### Current Coverage (as of 2025-10-27)

| File           | Statements | Branches | Functions | Lines |
|----------------|-----------|----------|-----------|-------|
| api-client.js  | 90.29%    | 80%      | 90%       | 90%   |
| toast.js       | 100%      | 85.71%   | 100%      | 100%  |
| **Overall**    | **92.75%**| **80.85%**| **92.85%**| **92.59%** |

### Coverage Goals

- Utilities: 50%+ (ACHIEVED: 92.75%)
- Components: 30%+ (In progress)
- Overall: 40%+ (ACHIEVED: 92.75%)

## What's Tested

### 1. API Client (`api-client.test.js`) - 26 tests

**Configuration** (4 tests)
- Base URL configuration from environment
- Timeout settings
- Retry attempt configuration
- URL building logic

**HTTP Methods** (6 tests)
- GET requests with proper headers
- POST requests with JSON data
- PUT requests
- PATCH requests
- DELETE requests
- File uploads with FormData

**Error Handling** (6 tests)
- 401 Unauthorized errors
- 403 Forbidden errors
- 404 Not Found errors
- 500 Server errors
- Network failures
- Non-JSON error responses

**Request Options** (3 tests)
- Credentials (cookies) handling
- Custom headers
- withCredentials option

**Response Handling** (3 tests)
- JSON response parsing
- Text response handling
- Status and headers extraction

**Retry Logic** (3 tests)
- Automatic retry on network failures
- Retry limit respect
- No retry on 4xx client errors

**Advanced Features** (1 test)
- File upload with progress tracking

### 2. Toast Notifications (`toast.test.js`) - 39 tests

**Container Management** (3 tests)
- Toast container creation
- Container reuse across toasts
- Positioning styles

**Toast Creation** (3 tests)
- Element creation with message
- Return value verification
- Max-width constraints

**Toast Types** (5 tests)
- Info toast (default, blue)
- Success toast (green)
- Warning toast (yellow)
- Error toast (red)
- Invalid type handling

**Styling** (4 tests)
- Text color
- Padding
- Rounded corners
- Shadow effects

**Animation** (3 tests)
- Initial state (hidden)
- Animate in transition
- Animate out before removal

**Auto-Dismiss** (3 tests)
- Default 3000ms duration
- Custom duration support
- Very short durations

**Multiple Toasts** (3 tests)
- Stacking multiple toasts
- Independent removal
- Correct ordering

**Container Cleanup** (2 tests)
- Remove container when empty
- Keep container if toasts exist

**XSS Protection** (3 tests)
- textContent prevents script execution
- HTML entity escaping
- Event handler prevention

**Helper Methods** (5 tests)
- toast.info()
- toast.success()
- toast.warning()
- toast.error()
- Custom duration in helpers

**Edge Cases** (5 tests)
- Empty messages
- Very long messages
- Special characters
- Unicode characters
- Global availability

### 3. Logger Utility (`logger.test.js`) - 17 tests

**Logger Creation** (3 tests)
- Without namespace
- With namespace
- Development environment detection

**Log Methods** (4 tests)
- info() logging
- warn() logging
- error() logging
- Namespace inclusion

**Advanced Features** (3 tests)
- Multiple arguments support
- Object logging
- Array logging

**Console Utilities** (3 tests)
- console.table() support
- console.group() support
- Performance timing (time/timeEnd)

**Edge Cases** (4 tests)
- Undefined arguments
- Null arguments
- Empty strings
- Global availability

## Writing New Tests

### Test File Template

```javascript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { yourFunction } from '../path/to/file.js'

describe('Your Feature', () => {
  beforeEach(() => {
    // Reset state before each test
    vi.clearAllMocks()
    document.body.innerHTML = ''
  })

  describe('Feature Group', () => {
    it('should do something specific', () => {
      // Arrange
      const input = 'test'

      // Act
      const result = yourFunction(input)

      // Assert
      expect(result).toBe('expected')
    })
  })
})
```

### Best Practices

1. **Arrange-Act-Assert**: Structure tests clearly
2. **Descriptive Names**: Use clear, action-based test names
3. **One Assertion Per Test**: Focus each test on one behavior
4. **Mock External Dependencies**: Use vi.fn() for mocks
5. **Clean Up**: Reset state in beforeEach/afterEach
6. **Test Edge Cases**: Include empty, null, undefined, extreme values

### Mocking Examples

```javascript
// Mock fetch
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({ data: 'test' })
})

// Mock localStorage
localStorage.setItem = vi.fn()
localStorage.getItem = vi.fn().mockReturnValue('value')

// Mock timers
vi.useFakeTimers()
vi.advanceTimersByTime(1000)
vi.useRealTimers()

// Mock modules
vi.mock('../utils/toast.js', () => ({
  showToast: vi.fn()
}))
```

## CI/CD Integration

Tests run automatically in GitHub Actions:

```yaml
- name: Run Frontend Tests
  run: |
    cd web/frontend
    npm run test:run
    npm run test:coverage
```

### Quality Gates

- All tests must pass
- Coverage must meet thresholds:
  - Lines: 40%+
  - Functions: 40%+
  - Branches: 30%+
  - Statements: 40%+

## Common Issues

### Issue: Tests timeout
**Solution**: Increase timeout or check for missing mock responses
```javascript
it('test name', { timeout: 10000 }, async () => {
  // test code
})
```

### Issue: "Module not found"
**Solution**: Check import paths use `../` relative paths
```javascript
import { fn } from '../utils/file.js'  // Correct
import { fn } from 'utils/file.js'     // Wrong
```

### Issue: DOM not available
**Solution**: happy-dom is configured globally, but check setup.js

### Issue: Fake timers not working
**Solution**: Use vi.useFakeTimers() and vi.useRealTimers()
```javascript
beforeEach(() => {
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
})
```

## Next Steps

### Phase 2: Component Tests (Planned)
- auth.js tests
- post-edit.js tests
- generating.js tests

### Phase 3: OAuth Setup Tests (Planned)
- setup-twitter.js tests
- setup-linkedin.js tests
- setup-instagram.js tests

### Phase 4: E2E Tests (Planned)
- Full user flows
- Multi-page navigation
- Form submissions

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Vi API (Mocking)](https://vitest.dev/api/vi.html)
- [Happy DOM](https://github.com/capricorn86/happy-dom)

## Maintenance

- Run tests before committing: `npm run test:run`
- Update tests when changing utilities
- Aim for 80%+ coverage on new code
- Review coverage report weekly

---

**Last Updated**: 2025-10-27
**Test Suite Version**: 1.0.0
**Total Tests**: 82
**All Tests Passing**: ✅
