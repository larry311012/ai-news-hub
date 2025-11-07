#!/usr/bin/env python3
"""
Batch fix user_id=1 references in test files to use test_user fixture
"""
import re
import sys
from pathlib import Path

def fix_fixture_user_id(content):
    """Fix user_id=1 in fixture definitions"""
    # Pattern 1: @pytest.fixture\ndef some_fixture(db_session):
    # Add test_user parameter
    pattern1 = r'(@pytest\.fixture[^\n]*\n)(def\s+\w+\(db_session)\)'

    def replace_fixture(match):
        decorator = match.group(1)
        def_line = match.group(2)
        # Only add test_user if the fixture body contains user_id=1
        return f"{decorator}{def_line}, test_user)"

    # Pattern 2: user_id=1 -> user_id=test_user.id
    content = re.sub(r'\buser_id=1\b', 'user_id=test_user.id', content)

    return content

def fix_test_method_user_id(content):
    """Fix user_id=1 in test methods"""
    # Pattern: def test_something(self, ...):
    # If method body contains user_id=1 or manager.get_connection(1, ...), add test_user param

    # First pass: Replace all user_id=1 with user_id=test_user.id
    content = re.sub(r'\buser_id=1\b', 'user_id=test_user.id', content)

    # Second pass: Replace manager.get_connection(1, with manager.get_connection(test_user.id,
    content = re.sub(r'\.get_connection\(1,', '.get_connection(test_user.id,', content)

    return content

def add_test_user_to_params(content):
    """Add test_user to function parameters if not present"""
    lines = content.split('\n')
    result = []

    for i, line in enumerate(lines):
        # Check if this is a fixture or test method that might need test_user
        if 'def ' in line and '(db_session' in line and 'test_user' not in line:
            # Look ahead to see if this function uses test_user.id
            next_20_lines = '\n'.join(lines[i:min(i+20, len(lines))])
            if 'test_user.id' in next_20_lines:
                # Add test_user parameter
                line = line.replace('(db_session)', '(db_session, test_user)')
                line = line.replace('(db_session,', '(db_session, test_user,')

        result.append(line)

    return '\n'.join(result)

def fix_file(filepath):
    """Fix a single test file"""
    print(f"Fixing {filepath}...")

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        original_content = content

        # Apply fixes
        content = fix_fixture_user_id(content)
        content = fix_test_method_user_id(content)
        content = add_test_user_to_params(content)

        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✓ Fixed {filepath}")
            return True
        else:
            print(f"  - No changes needed for {filepath}")
            return False

    except Exception as e:
        print(f"  ✗ Error fixing {filepath}: {e}")
        return False

def main():
    # Files to fix
    files = [
        'tests/test_image_storage.py',
        'tests/test_instagram_performance.py',
        'tests/test_post_generation_integration.py',
        'tests/test_post_generation_flow_comprehensive.py',
    ]

    fixed_count = 0
    for filepath in files:
        path = Path(filepath)
        if path.exists():
            if fix_file(path):
                fixed_count += 1
        else:
            print(f"  ⚠ File not found: {filepath}")

    print(f"\n✓ Fixed {fixed_count}/{len(files)} files")

if __name__ == '__main__':
    main()
