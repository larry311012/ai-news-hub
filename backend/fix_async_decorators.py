#!/usr/bin/env python3
"""
Fix async test decorator ordering issues.

Changes:
1. Move @pytest.mark.asyncio to be AFTER @patch.dict
2. Or convert @patch.dict decorators to context managers inside the function

For simplicity, we convert @patch.dict decorators to use 'with patch.dict(...)' inside functions.
"""

import re
import sys

def fix_async_decorator_order(filepath):
    """Fix decorator ordering in test file"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Pattern: @pytest.mark.asyncio followed by @patch.dict decorator
    pattern = r'(\s*)@pytest.mark.asyncio\n(\s*)@patch\.dict\((.*?)\)\n(\s*)async def (test_\w+)\((.*?)\):'

    # Replacement: swap the order
    replacement = r'\1@patch.dict(\3)\n\2@pytest.mark.asyncio\n\4async def \5(\6):'

    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Also handle AsyncMock for responses - Mock should be used for response objects
    # This is a simple pattern - may need manual review

    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Fixed {filepath}")
        return True
    else:
        print(f"No changes needed for {filepath}")
        return False

if __name__ == '__main__':
    files = [
        'test_twitter_oauth1_comprehensive.py',
    ]

    for filepath in files:
        try:
            fix_async_decorator_order(filepath)
        except Exception as e:
            print(f"Error fixing {filepath}: {e}")
