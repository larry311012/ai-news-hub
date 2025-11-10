# API Key Test Endpoint - Quick Test Commands

## Quick Test (Automated)

```bash
# Run the automated test script
cd /Users/ranhui/ai_post/ai-news-hub-web/backend
./test_api_key_endpoint_manual.sh
```

## Manual Test with curl

### 1. Register/Login
```bash
# Register new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
  }' | jq

# Or login existing user
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }' | jq -r '.token')

echo "Token: $TOKEN"
```

### 2. Save API Key
```bash
# Save OpenAI API key
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-test-your-real-or-fake-key",
    "name": "My OpenAI Key"
  }' | jq
```

### 3. Test API Key
```bash
# Test the API key
curl -X POST http://localhost:8000/api/auth/api-keys/openai/test \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected Response:**
```json
{
  "is_valid": false,
  "message": "API key validation failed: ...",
  "provider": "openai",
  "tested_at": "2025-11-08T10:15:30.123456Z"
}
```

### 4. Test Edge Cases

#### Missing API Key (404)
```bash
curl -X POST http://localhost:8000/api/auth/api-keys/anthropic/test \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected: `{"detail":"API key for provider 'anthropic' not found"}`

#### No Authentication (401)
```bash
curl -X POST http://localhost:8000/api/auth/api-keys/openai/test | jq
```

Expected: `{"detail":"Not authenticated"}` with HTTP 401

#### Case Insensitive Provider
```bash
curl -X POST http://localhost:8000/api/auth/api-keys/OpenAI/test \
  -H "Authorization: Bearer $TOKEN" | jq
```

Should work the same as lowercase "openai"

## pytest Tests

```bash
# Run all API key endpoint tests
cd /Users/ranhui/ai_post/ai-news-hub-web/backend
python -m pytest tests/test_api_key_endpoint.py -v

# Run only encryption tests (these should all pass)
python -m pytest tests/test_api_key_endpoint.py::TestEncryptionRoundTrip -v

# Run specific test
python -m pytest tests/test_api_key_endpoint.py::TestApiKeyTestEndpoint::test_openai_valid_api_key -v

# Run with detailed output
python -m pytest tests/test_api_key_endpoint.py -vv --tb=short
```

## Response Format Validation

### iOS Model (Swift)
```swift
struct APIKeyTestResponse: Codable {
    let isValid: Bool        // maps to is_valid
    let message: String?
    let provider: APIProvider
    let testedAt: Date       // maps to tested_at (ISO8601)

    enum CodingKeys: String, CodingKey {
        case isValid = "is_valid"
        case message
        case provider
        case testedAt = "tested_at"
    }
}
```

### Backend Response (JSON)
```json
{
  "is_valid": boolean,
  "message": string,
  "provider": string,
  "tested_at": string  // ISO8601 format
}
```

## Response Examples

### ✅ Valid API Key
```json
{
  "is_valid": true,
  "message": "API key is valid",
  "provider": "openai",
  "tested_at": "2025-11-08T10:15:30.123456Z"
}
```

### ❌ Invalid API Key
```json
{
  "is_valid": false,
  "message": "API key validation failed: Authentication failed",
  "provider": "openai",
  "tested_at": "2025-11-08T10:15:30.123456Z"
}
```

### ❌ Decryption Failure
```json
{
  "is_valid": false,
  "message": "Failed to decrypt API key - encryption key may have changed",
  "provider": "openai",
  "tested_at": "2025-11-08T10:15:30.123456Z"
}
```

### ❌ Unsupported Provider
```json
{
  "is_valid": false,
  "message": "Testing not implemented for this provider",
  "provider": "twitter",
  "tested_at": "2025-11-08T10:15:30.123456Z"
}
```

## Check Encryption Key

```bash
# Verify ENCRYPTION_KEY is set
python -c "import os; print('ENCRYPTION_KEY length:', len(os.getenv('ENCRYPTION_KEY', '')))"

# Should output: ENCRYPTION_KEY length: 44 (or similar non-zero value)

# Test encryption round-trip
python -c "
from utils.encryption import encrypt_api_key, decrypt_api_key
original = 'sk-test-key-123'
encrypted = encrypt_api_key(original)
decrypted = decrypt_api_key(encrypted)
print(f'Original: {original}')
print(f'Encrypted: {encrypted[:20]}...')
print(f'Decrypted: {decrypted}')
print(f'Match: {original == decrypted}')
"
```

## Files Changed

- **Backend**: `/Users/ranhui/ai_post/ai-news-hub-web/backend/api/auth.py`
- **Tests**: `/Users/ranhui/ai_post/ai-news-hub-web/backend/tests/test_api_key_endpoint.py`
- **Backup**: `/Users/ranhui/ai_post/ai-news-hub-web/backend/api/auth.py.backup_before_ios_fix`

## Rollback (if needed)

```bash
cd /Users/ranhui/ai_post/ai-news-hub-web/backend
cp api/auth.py.backup_before_ios_fix api/auth.py
```

## Verify Backend is Running

```bash
# Check if backend is running
curl -s http://localhost:8000/api/health | jq

# Start backend if needed
cd /Users/ranhui/ai_post/ai-news-hub-web/backend
uvicorn main:app --reload --port 8000
```
