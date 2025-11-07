"""
Verify Anonymous Mode Implementation

This script checks that all components of anonymous mode are properly configured.
Run this after implementing anonymous mode to verify everything works.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import os
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def print_success(message):
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")

def check_files_exist():
    """Check that all required files exist"""
    print("\n" + "="*60)
    print("Checking Files...")
    print("="*60)

    base_dir = Path(__file__).parent.parent
    required_files = [
        "utils/anonymous_auth.py",
        "utils/auth_selector.py",
        "scripts/create_anonymous_user.py",
        "docs/ANONYMOUS_MODE.md",
    ]

    all_exist = True
    for file_path in required_files:
        full_path = base_dir / file_path
        if full_path.exists():
            print_success(f"{file_path} exists")
        else:
            print_error(f"{file_path} missing!")
            all_exist = False

    return all_exist

def check_imports():
    """Check that imports work correctly"""
    print("\n" + "="*60)
    print("Checking Imports...")
    print("="*60)

    try:
        from utils.anonymous_auth import get_anonymous_user, ANONYMOUS_MODE_ENABLED
        print_success("anonymous_auth module imports")

        from utils.auth_selector import get_current_user, ANONYMOUS_MODE
        print_success("auth_selector module imports")

        return True
    except ImportError as e:
        print_error(f"Import failed: {e}")
        return False

def check_anonymous_user():
    """Check that anonymous user exists in database"""
    print("\n" + "="*60)
    print("Checking Anonymous User...")
    print("="*60)

    try:
        from database import SessionLocal, User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == 1).first()

            if user:
                print_success(f"Anonymous user exists (id={user.id})")
                print_info(f"  Email: {user.email}")
                print_info(f"  Name: {user.full_name}")
                print_info(f"  Active: {user.is_active}")
                print_info(f"  Admin: {user.is_admin}")
                return True
            else:
                print_error("Anonymous user (id=1) not found!")
                print_warning("Run: python scripts/create_anonymous_user.py")
                return False
        finally:
            db.close()
    except Exception as e:
        print_error(f"Database check failed: {e}")
        return False

def check_api_imports():
    """Check that API files use auth_selector"""
    print("\n" + "="*60)
    print("Checking API Imports...")
    print("="*60)

    base_dir = Path(__file__).parent.parent / "api"

    # Files that should use auth_selector
    api_files = [
        "posts.py",
        "articles.py",
        "social_media.py",
        "settings.py",
    ]

    all_correct = True
    for filename in api_files:
        file_path = base_dir / filename
        if not file_path.exists():
            print_warning(f"{filename} not found (may be optional)")
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        # Check for correct import
        if "from utils.auth_selector import get_current_user" in content:
            print_success(f"{filename} uses auth_selector")
        elif "from utils.auth import get_current_user_dependency" in content:
            print_error(f"{filename} still uses old auth import!")
            all_correct = False
        else:
            print_warning(f"{filename} may not use auth (could be OK)")

    return all_correct

def check_env_configuration():
    """Check .env.example has anonymous mode configuration"""
    print("\n" + "="*60)
    print("Checking Configuration...")
    print("="*60)

    env_example = Path(__file__).parent.parent / ".env.example"

    if not env_example.exists():
        print_error(".env.example not found!")
        return False

    with open(env_example, 'r') as f:
        content = f.read()

    if "ANONYMOUS_MODE" in content:
        print_success(".env.example includes ANONYMOUS_MODE")

        # Check current .env setting
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()

            if "ANONYMOUS_MODE=true" in env_content:
                print_warning("ANONYMOUS_MODE is currently ENABLED in .env")
            elif "ANONYMOUS_MODE=false" in env_content:
                print_info("ANONYMOUS_MODE is currently DISABLED in .env")
            else:
                print_info("ANONYMOUS_MODE not set in .env (defaults to false)")
        else:
            print_info(".env file not found (will use defaults)")

        return True
    else:
        print_error(".env.example missing ANONYMOUS_MODE configuration!")
        return False

def check_main_py():
    """Check that main.py has anonymous mode startup check"""
    print("\n" + "="*60)
    print("Checking main.py...")
    print("="*60)

    main_py = Path(__file__).parent.parent / "main.py"

    if not main_py.exists():
        print_error("main.py not found!")
        return False

    with open(main_py, 'r') as f:
        content = f.read()

    if "ANONYMOUS MODE ENABLED" in content:
        print_success("main.py includes anonymous mode startup check")
        return True
    else:
        print_error("main.py missing anonymous mode startup check!")
        return False

def main():
    """Run all verification checks"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print("Anonymous Mode Implementation Verification")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    checks = [
        ("Files", check_files_exist),
        ("Imports", check_imports),
        ("Anonymous User", check_anonymous_user),
        ("API Files", check_api_imports),
        ("Configuration", check_env_configuration),
        ("Main.py", check_main_py),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Check failed with exception: {e}")
            results[name] = False

    # Print summary
    print(f"\n{Fore.CYAN}{'='*60}")
    print("Summary")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        if result:
            print_success(f"{name}: PASS")
        else:
            print_error(f"{name}: FAIL")

    print(f"\n{Fore.CYAN}Result: {passed}/{total} checks passed{Style.RESET_ALL}")

    if passed == total:
        print(f"\n{Fore.GREEN}{'='*60}")
        print("✓ All checks passed!")
        print("Anonymous mode implementation is verified and ready to use.")
        print(f"{'='*60}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}To enable anonymous mode:{Style.RESET_ALL}")
        print("1. Add to .env: ANONYMOUS_MODE=true")
        print("2. Restart backend: pkill -f uvicorn && uvicorn main:app --reload")
        print("3. Test: curl http://localhost:8000/api/auth/profile")

        return 0
    else:
        print(f"\n{Fore.YELLOW}{'='*60}")
        print("⚠ Some checks failed!")
        print("Review the errors above and fix any issues.")
        print(f"{'='*60}{Style.RESET_ALL}\n")

        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Verification cancelled by user.{Style.RESET_ALL}")
        sys.exit(130)
