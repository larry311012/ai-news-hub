#!/usr/bin/env python3
"""
Check Admin Status and Guide User

This script checks if you're admin and provides next steps.
"""

from database import SessionLocal, User

def check_and_guide():
    db = SessionLocal()

    try:
        users = db.query(User).all()

        print("\n" + "="*80)
        print("🔍 ADMIN STATUS CHECK")
        print("="*80)

        admins = [u for u in users if u.is_admin]
        non_admins = [u for u in users if not u.is_admin]

        if admins:
            print(f"\n✅ Found {len(admins)} admin user(s):\n")
            for user in admins:
                print(f"   👤 {user.email}")
                print(f"      Name: {user.full_name}")
                print(f"      ID: {user.id}")
                print()
        else:
            print("\n⚠️  No admin users found!\n")

        if non_admins:
            print(f"📋 Non-admin users ({len(non_admins)}):\n")
            for user in non_admins:
                print(f"   • {user.email} (ID: {user.id})")
            print()

        print("="*80)
        print("📝 NEXT STEPS")
        print("="*80)

        if not admins:
            print("\n1️⃣  Make yourself admin:")
            if users:
                print(f"    python make_user_admin.py {users[0].email}")
            print()

        print("2️⃣  Logout and login again with your admin account")
        print()
        print("3️⃣  Go to profile page: http://localhost:8080/profile.html")
        print()
        print("4️⃣  Scroll down PAST 'Social Media Connections'")
        print()
        print("5️⃣  You should see 'Twitter API Credentials (Admin)' section")
        print()
        print("6️⃣  Click the Twitter/X card to expand")
        print()
        print("7️⃣  Enter your Twitter credentials and save")
        print()
        print("="*80)

        # Check if Twitter is already configured
        from utils.oauth_config import get_oauth_config_status
        twitter_status = get_oauth_config_status()

        if twitter_status['configured']:
            print("\n✅ Twitter OAuth is already configured!")
            print(f"   Source: {twitter_status.get('source', 'unknown')}")
        else:
            print("\n⚠️  Twitter OAuth is NOT configured yet")
            print("   Configure it via the admin UI after logging in as admin")

        print("\n" + "="*80 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    check_and_guide()
