"""
Simple patch to add API key validation imports to auth.py
"""

# Read the file
with open('api/auth.py', 'r') as f:
    lines = f.readlines()

# Find the encryption import line and add our import after it
for i, line in enumerate(lines):
    if 'from utils.encryption import' in line:
        # Check if api_key_validator is already imported
        already_imported = any('api_key_validator' in l for l in lines[:i+5])

        if not already_imported:
            # Add the new import after this line
            new_import = """from utils.api_key_validator import (
    validate_api_key,
    sanitize_api_key,
    detect_potential_corruption,
    mask_api_key
)
"""
            lines.insert(i+1, new_import)
            print("✅ Added api_key_validator import")
            break
        else:
            print("ℹ️  api_key_validator already imported")
            break

# Write back
with open('api/auth.py', 'w') as f:
    f.writelines(lines)

print("\n✅ Import added successfully!")
print("\n📝 Note: You'll need to manually update the save_api_key function")
print("   Or use the enhanced version from api/auth_enhanced.py")
