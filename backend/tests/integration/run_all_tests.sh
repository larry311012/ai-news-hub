#!/bin/bash

# Master Test Runner for All Authentication Tests
# Runs Phase 1, 2, 3, and 4 tests in sequence

set -e  # Exit on first failure (optional, comment out to run all tests)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Test start time
START_TIME=$(date +%s)

# Print banner
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}║         COMPREHENSIVE AUTHENTICATION TESTS        ║${NC}"
echo -e "${CYAN}║              Phase 1, 2, 3, and 4                 ║${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test Date:${NC} $(date)"
echo -e "${BLUE}Script Dir:${NC} $SCRIPT_DIR"
echo ""

# Check if server is running
echo -e "${CYAN}Checking server status...${NC}"
if ! curl -s "http://localhost:8001/health" > /dev/null 2>&1; then
    echo -e "${RED}✗ Backend server is not running${NC}"
    echo "Please start the server first: python3 main.py"
    exit 1
fi
echo -e "${GREEN}✓ Server is running${NC}"
echo ""

# Function to run a test script
run_test() {
    local test_name="$1"
    local test_script="$2"
    local test_type="${3:-bash}"  # bash or python

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Running: $test_name${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""

    if [ ! -f "$SCRIPT_DIR/$test_script" ]; then
        echo -e "${YELLOW}⚠ Test script not found: $test_script${NC}"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
        return 1
    fi

    # Make script executable
    chmod +x "$SCRIPT_DIR/$test_script"

    # Run the test
    if [ "$test_type" = "python" ]; then
        if python3 "$SCRIPT_DIR/$test_script"; then
            echo -e "${GREEN}✓ $test_name PASSED${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo -e "${RED}✗ $test_name FAILED${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    else
        if bash "$SCRIPT_DIR/$test_script"; then
            echo -e "${GREEN}✓ $test_name PASSED${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
            return 0
        else
            echo -e "${RED}✗ $test_name FAILED${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# Option parsing
RUN_PHASE1=true
RUN_PHASE2=true
RUN_PHASE3=true
RUN_PHASE4=true
RUN_INTEGRATION=true
RUN_SECURITY=true
RUN_PERFORMANCE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --phase1-only)
            RUN_PHASE2=false
            RUN_PHASE3=false
            RUN_PHASE4=false
            RUN_INTEGRATION=false
            RUN_SECURITY=false
            RUN_PERFORMANCE=false
            shift
            ;;
        --phase2-only)
            RUN_PHASE1=false
            RUN_PHASE3=false
            RUN_PHASE4=false
            RUN_INTEGRATION=false
            RUN_SECURITY=false
            RUN_PERFORMANCE=false
            shift
            ;;
        --phase3-only)
            RUN_PHASE1=false
            RUN_PHASE2=false
            RUN_PHASE4=false
            RUN_INTEGRATION=false
            RUN_SECURITY=false
            RUN_PERFORMANCE=false
            shift
            ;;
        --phase4-only)
            RUN_PHASE1=false
            RUN_PHASE2=false
            RUN_PHASE3=false
            RUN_INTEGRATION=false
            RUN_SECURITY=false
            RUN_PERFORMANCE=false
            shift
            ;;
        --skip-integration)
            RUN_INTEGRATION=false
            shift
            ;;
        --skip-security)
            RUN_SECURITY=false
            shift
            ;;
        --skip-performance)
            RUN_PERFORMANCE=false
            shift
            ;;
        --quick)
            RUN_INTEGRATION=false
            RUN_SECURITY=false
            RUN_PERFORMANCE=false
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --phase1-only       Run only Phase 1 tests"
            echo "  --phase2-only       Run only Phase 2 tests"
            echo "  --phase3-only       Run only Phase 3 tests"
            echo "  --phase4-only       Run only Phase 4 tests"
            echo "  --skip-integration  Skip integration tests"
            echo "  --skip-security     Skip security tests"
            echo "  --skip-performance  Skip performance tests"
            echo "  --quick             Run only core tests (skip integration, security, performance)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================
# PHASE 1 TESTS
# ============================================
if [ "$RUN_PHASE1" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║               PHASE 1 TESTS                       ║${NC}"
    echo -e "${BLUE}║    Basic Auth: Register, Login, Logout            ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    run_test "Phase 1: Basic Authentication" "test_auth.sh"
fi

# ============================================
# PHASE 2 TESTS
# ============================================
if [ "$RUN_PHASE2" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║               PHASE 2 TESTS                       ║${NC}"
    echo -e "${BLUE}║   Profile, Password, API Keys, Account Deletion   ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    run_test "Phase 2: Authentication Extended" "test_auth_phase2.sh"
    run_test "Phase 2: Endpoint Validation" "test_phase2_endpoints.py" "python"
fi

# ============================================
# PHASE 3 TESTS
# ============================================
if [ "$RUN_PHASE3" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║               PHASE 3 TESTS                       ║${NC}"
    echo -e "${BLUE}║    Email Verification, OAuth, Guest Mode          ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    run_test "Phase 3: Email Verification" "test_email_verification.sh"
    run_test "Phase 3: Guest Mode" "test_guest_mode.sh"
    run_test "Phase 3: OAuth Integration" "test_oauth.sh"
    run_test "Phase 3: OAuth Mock Tests" "test_oauth_mock.py" "python"
fi

# ============================================
# PHASE 4 TESTS
# ============================================
if [ "$RUN_PHASE4" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║               PHASE 4 TESTS                       ║${NC}"
    echo -e "${BLUE}║  Password Reset, Sessions, Security Dashboard     ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    run_test "Phase 4: Password Reset" "test_password_reset.sh"

    if [ -f "$SCRIPT_DIR/test_session_management.sh" ]; then
        run_test "Phase 4: Session Management" "test_session_management.sh"
    else
        echo -e "${YELLOW}⚠ Session Management tests not yet created${NC}"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi

    if [ -f "$SCRIPT_DIR/test_security_dashboard.sh" ]; then
        run_test "Phase 4: Security Dashboard" "test_security_dashboard.sh"
    else
        echo -e "${YELLOW}⚠ Security Dashboard tests not yet created${NC}"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi

    if [ -f "$SCRIPT_DIR/test_rate_limiting.sh" ]; then
        run_test "Phase 4: Rate Limiting" "test_rate_limiting.sh"
    else
        echo -e "${YELLOW}⚠ Rate Limiting tests not yet created${NC}"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi
fi

# ============================================
# INTEGRATION TESTS
# ============================================
if [ "$RUN_INTEGRATION" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║            INTEGRATION TESTS                      ║${NC}"
    echo -e "${BLUE}║         Full User Journey Testing                 ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    if [ -f "$SCRIPT_DIR/test_full_auth_flow.sh" ]; then
        run_test "Integration: Full Authentication Flow" "test_full_auth_flow.sh"
    else
        echo -e "${YELLOW}⚠ Full Auth Flow tests not yet created${NC}"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi
fi

# ============================================
# SECURITY TESTS
# ============================================
if [ "$RUN_SECURITY" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║             SECURITY TESTS                        ║${NC}"
    echo -e "${BLUE}║    Penetration Testing & Vulnerability Scanning   ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    if [ -f "$SCRIPT_DIR/security_penetration_test.sh" ]; then
        run_test "Security: Penetration Testing" "security_penetration_test.sh"
    else
        echo -e "${YELLOW}⚠ Security Penetration tests not yet created${NC}"
        SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    fi
fi

# ============================================
# PERFORMANCE TESTS
# ============================================
if [ "$RUN_PERFORMANCE" = true ]; then
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           PERFORMANCE TESTS                       ║${NC}"
    echo -e "${BLUE}║      Load Testing & Benchmarking                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"

    if [ -f "$SCRIPT_DIR/performance_test_full.sh" ]; then
        run_test "Performance: Full Load Testing" "performance_test_full.sh"
    else
        run_test "Performance: Basic Tests" "performance_test.sh"
    fi
fi

# ============================================
# FINAL SUMMARY
# ============================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}║              FINAL TEST SUMMARY                   ║${NC}"
echo -e "${CYAN}║                                                   ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test Duration:${NC} ${MINUTES}m ${SECONDS}s"
echo ""
echo -e "${CYAN}Test Suites:${NC}"
echo -e "${GREEN}  Passed:  $PASSED_TESTS${NC}"
echo -e "${RED}  Failed:  $FAILED_TESTS${NC}"
echo -e "${YELLOW}  Skipped: $SKIPPED_TESTS${NC}"
echo ""

# Coverage estimate
TOTAL_EXPECTED=17  # Approximate number of test suites
if [ $TOTAL_TESTS -gt 0 ]; then
    COVERAGE=$(( (PASSED_TESTS * 100) / TOTAL_EXPECTED ))
    echo -e "${BLUE}Estimated Coverage:${NC} ${COVERAGE}%"
    echo ""
fi

# Overall result
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                   ║${NC}"
    echo -e "${GREEN}║            ✓ ALL TESTS PASSED! ✓                  ║${NC}"
    echo -e "${GREEN}║                                                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                   ║${NC}"
    echo -e "${RED}║            ✗ SOME TESTS FAILED ✗                  ║${NC}"
    echo -e "${RED}║                                                   ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Review the output above for details on failures.${NC}"
    echo ""
    exit 1
fi
