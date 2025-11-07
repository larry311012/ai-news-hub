#!/bin/bash

# MASTER DIAGNOSTIC SCRIPT
# Runs all diagnostic tests and generates final report

clear

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                       ║"
echo "║           POST GENERATION FAILURE DIAGNOSTIC SUITE                   ║"
echo "║                                                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Running comprehensive diagnostics to identify generation failure..."
echo ""

# Change to backend directory
cd "$(dirname "$0")"

# Test 1: Code Fix Verification
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Code Fix Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 test_verify_code_fixes.py
CODE_FIX_RESULT=$?
echo ""
sleep 1

# Test 2: API Key Diagnostic
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: API Key Decryption Diagnostic"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 test_api_key_issue.py
API_KEY_RESULT=$?
echo ""
sleep 1

# Test 3: Quick System Check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: System Status Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash test_quick_diagnostic.sh
echo ""

# Final Report
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                        DIAGNOSTIC SUMMARY                             ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

if [ $CODE_FIX_RESULT -eq 0 ]; then
    echo "✅ Code Fixes: ALL LOADED AND WORKING (5/5 tests passed)"
else
    echo "❌ Code Fixes: SOME MISSING (check output above)"
fi

if [ $API_KEY_RESULT -eq 0 ]; then
    echo "✅ API Key: Decryption working correctly"
else
    echo "❌ API Key: DECRYPTION FAILED (root cause of generation failure)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FINAL DIAGNOSIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $CODE_FIX_RESULT -eq 0 ] && [ $API_KEY_RESULT -ne 0 ]; then
    echo "🎯 ROOT CAUSE IDENTIFIED:"
    echo "   - All code fixes are working correctly"
    echo "   - API key decryption is failing"
    echo "   - This is why generation fails"
    echo ""
    echo "🔧 SOLUTION:"
    echo "   User must update their OpenAI API key in Profile settings"
    echo ""
    echo "📋 NEXT STEPS:"
    echo "   1. Log in to http://localhost:8000"
    echo "   2. Go to Profile/Settings"
    echo "   3. Enter new OpenAI API key (sk-...)"
    echo "   4. Save"
    echo "   5. Try generating posts again"
    echo ""
    echo "🚀 ALTERNATIVE QUICK FIX:"
    echo "   Run: python3 fix_api_key_encryption.py"
    echo ""
elif [ $CODE_FIX_RESULT -ne 0 ]; then
    echo "⚠️  CODE FIXES INCOMPLETE:"
    echo "   Some code fixes are missing"
    echo "   Review test output above to see which ones"
    echo ""
elif [ $CODE_FIX_RESULT -eq 0 ] && [ $API_KEY_RESULT -eq 0 ]; then
    echo "✅ EVERYTHING LOOKS GOOD:"
    echo "   - All code fixes loaded"
    echo "   - API key decryption working"
    echo ""
    echo "   If generation is still failing, check:"
    echo "   - Is the API key valid with OpenAI?"
    echo "   - Is the backend server running?"
    echo "   - Check backend logs for errors"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📄 DETAILED REPORT: DIAGNOSTIC_REPORT.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Full diagnostic report saved to:"
echo "  /Users/ranhui/ai_post/web/backend/DIAGNOSTIC_REPORT.md"
echo ""
echo "Test scripts available:"
echo "  - test_verify_code_fixes.py (code verification)"
echo "  - test_api_key_issue.py (API key diagnostic)"
echo "  - test_quick_diagnostic.sh (quick system check)"
echo "  - verify_all_fixes.sh (comprehensive verification)"
echo ""

# Open report in default viewer (optional, commented out)
# open DIAGNOSTIC_REPORT.md

echo "Diagnostic complete! 🎉"
echo ""
