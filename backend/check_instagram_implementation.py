"""
Instagram API Implementation Status Checker

This script checks if the backend-architect has completed implementing
the Instagram image generation API endpoints.

Usage:
    python check_instagram_implementation.py
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict


# ============================================================================
# REQUIRED COMPONENTS
# ============================================================================

REQUIRED_COMPONENTS = {
    "services": [
        ("services/image_generation_service.py", "ImageGenerationService"),
        ("services/image_storage.py", "ImageStorage"),
    ],
    "api_endpoints": [
        ("api/instagram.py", "router.post.*generate-instagram-image"),
        ("api/instagram.py", "router.get.*instagram-image"),
        ("api/instagram.py", "router.post.*regenerate-instagram-image"),
        ("api/instagram.py", "router.get.*instagram/quota"),
        ("api/instagram.py", "router.delete.*instagram-image"),
    ],
    "database": [
        ("database.py", "class InstagramImage"),
        ("database.py", "class ImageGenerationQuota"),
    ],
    "utils": [
        ("utils/image_generator.py", "generate_dalle_image"),
        ("utils/prompt_generator.py", "generate_instagram_prompt"),
    ],
}


# ============================================================================
# CHECKER FUNCTIONS
# ============================================================================

def check_file_exists(file_path: str) -> Tuple[bool, str]:
    """Check if file exists"""
    backend_dir = Path(__file__).parent
    full_path = backend_dir / file_path

    if full_path.exists():
        return True, f"✓ Found: {file_path}"
    else:
        return False, f"✗ Missing: {file_path}"


def check_code_pattern(file_path: str, pattern: str) -> Tuple[bool, str]:
    """Check if file contains code pattern"""
    backend_dir = Path(__file__).parent
    full_path = backend_dir / file_path

    if not full_path.exists():
        return False, f"✗ File not found: {file_path}"

    try:
        content = full_path.read_text()

        if re.search(pattern, content, re.MULTILINE):
            return True, f"✓ Found pattern in {file_path}: {pattern[:50]}"
        else:
            return False, f"✗ Pattern not found in {file_path}: {pattern[:50]}"

    except Exception as e:
        return False, f"✗ Error reading {file_path}: {e}"


def check_main_py_registration() -> Tuple[bool, str]:
    """Check if Instagram router is registered in main.py"""
    backend_dir = Path(__file__).parent
    main_path = backend_dir / "main.py"

    if not main_path.exists():
        return False, "✗ main.py not found"

    content = main_path.read_text()

    # Check for import
    if "from api import" not in content or "instagram" not in content:
        return False, "✗ Instagram API not imported in main.py"

    # Check for router registration
    if not re.search(r'app\.include_router\(instagram\.router.*instagram', content):
        return False, "✗ Instagram router not registered in main.py"

    return True, "✓ Instagram router registered in main.py"


# ============================================================================
# MAIN CHECKER
# ============================================================================

def main():
    """Run implementation status check"""
    print("="*80)
    print("INSTAGRAM API IMPLEMENTATION STATUS CHECK")
    print("="*80)
    print()

    all_checks_passed = True
    results_by_category: Dict[str, List[Tuple[bool, str]]] = {}

    # Check services
    print("SERVICES:")
    print("-"*80)
    service_results = []

    for file_path, class_name in REQUIRED_COMPONENTS["services"]:
        passed, message = check_code_pattern(file_path, f"class {class_name}")
        service_results.append((passed, message))
        print(message)

        if not passed:
            all_checks_passed = False

    results_by_category["services"] = service_results
    print()

    # Check API endpoints
    print("API ENDPOINTS:")
    print("-"*80)
    api_results = []

    for file_path, pattern in REQUIRED_COMPONENTS["api_endpoints"]:
        passed, message = check_code_pattern(file_path, pattern)
        api_results.append((passed, message))
        print(message)

        if not passed:
            all_checks_passed = False

    results_by_category["api_endpoints"] = api_results
    print()

    # Check database models
    print("DATABASE MODELS:")
    print("-"*80)
    db_results = []

    for file_path, pattern in REQUIRED_COMPONENTS["database"]:
        passed, message = check_code_pattern(file_path, pattern)
        db_results.append((passed, message))
        print(message)

        if not passed:
            all_checks_passed = False

    results_by_category["database"] = db_results
    print()

    # Check utilities
    print("UTILITIES:")
    print("-"*80)
    util_results = []

    for file_path, pattern in REQUIRED_COMPONENTS["utils"]:
        passed, message = check_code_pattern(file_path, pattern)
        util_results.append((passed, message))
        print(message)

        if not passed:
            all_checks_passed = False

    results_by_category["utils"] = util_results
    print()

    # Check main.py registration
    print("MAIN.PY REGISTRATION:")
    print("-"*80)
    main_passed, main_message = check_main_py_registration()
    print(main_message)
    print()

    if not main_passed:
        all_checks_passed = False

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)

    total_checks = sum(len(results) for results in results_by_category.values()) + 1  # +1 for main.py
    passed_checks = sum(
        sum(1 for passed, _ in results if passed)
        for results in results_by_category.values()
    )
    if main_passed:
        passed_checks += 1

    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print()

    if all_checks_passed:
        print("✓ ALL CHECKS PASSED")
        print()
        print("The Instagram API implementation is complete!")
        print()
        print("Next steps:")
        print("  1. Start the backend server: python main.py")
        print("  2. Run manual tests: python test_instagram_api_manual.py")
        print("  3. Run shell tests: ./test_instagram_endpoints.sh")
        print("  4. Run load tests: python test_instagram_load.py --scenario gradual")
        return 0
    else:
        print("✗ IMPLEMENTATION INCOMPLETE")
        print()
        print("Missing components detected. Waiting for backend-architect to complete:")
        print()

        for category, results in results_by_category.items():
            failed = [msg for passed, msg in results if not passed]
            if failed:
                print(f"{category.upper()}:")
                for msg in failed:
                    print(f"  {msg}")
                print()

        print("Once implementation is complete, re-run this checker.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
