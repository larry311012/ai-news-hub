# Integration Test Scripts

This directory contains integration test scripts and diagnostic tools used during development.

## Organization

- **test_*.sh** - Feature-specific integration tests
- **quick_*.sh** - Quick diagnostic tests for specific features
- **comprehensive_*.sh** - Full end-to-end test suites
- **verify_*.sh** - Verification scripts for bug fixes
- **run_*.sh** - Test runners for specific modules
- **fix_*.sh** - One-time fix/migration scripts
- **TEST_*.py** - Python integration test scripts
- **QUICK_TEST_COMMANDS.sh** - Quick reference command lists

## Running Tests

### Quick Smoke Tests
```bash
# Test authentication
./quick_api_test.sh

# Test OAuth flows
./quick_oauth_test.sh

# Test all core features
./run_all_tests.sh
```

### Comprehensive Tests
```bash
# Full API test suite
./comprehensive_api_test.sh

# Full auth flow tests
./comprehensive_auth_tests.sh

# Performance benchmarks
./performance_test.sh
```

### Platform-Specific Tests
```bash
# Twitter OAuth
./run_twitter_publishing_tests.sh

# LinkedIn integration
./run_linkedin_tests.sh

# Instagram publishing
./run_instagram_tests.sh
```

## Test Categories

### Authentication & Security
- `test_auth*.sh` - Login, registration, sessions
- `test_csrf*.sh` - CSRF protection
- `security_audit_test.sh` - Security vulnerability scan

### OAuth & Social Media
- `test_linkedin*.sh` - LinkedIn OAuth integration
- `test_twitter*.sh` - Twitter OAuth 1.0a
- `test_instagram*.sh` - Instagram OAuth
- `test_social_media*.sh` - Multi-platform tests

### API & Features
- `test_api_key*.sh` - API key management
- `test_post*.sh` - Content generation
- `test_rss*.sh` - RSS feed aggregation
- `test_caching*.sh` - Redis caching layer

### Infrastructure
- `test_database_migration.sh` - Migration testing
- `test_mobile_api.sh` - Mobile API endpoints
- `performance_test.sh` - Load testing

## Verification Scripts

After bug fixes, run corresponding verification scripts:
```bash
./verify_all_fixes.sh           # Run all verification tests
./verify_twitter_oauth_fix.sh   # Verify Twitter OAuth fix
./verify_linkedin_oauth_fix.sh  # Verify LinkedIn OAuth fix
```

## Notes

- Most scripts require backend running on port 8000
- Some tests create temporary test users (auto-cleaned)
- Check script headers for specific requirements
- Test result JSON files are gitignored

## Contributing

When adding new integration tests:
1. Follow naming convention: `test_<feature>_<scope>.sh`
2. Include cleanup logic (delete test data)
3. Add error handling and clear output
4. Document in this README
5. Add to `run_all_tests.sh` if appropriate
