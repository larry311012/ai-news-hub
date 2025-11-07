#!/usr/bin/env python3
"""
Make User Admin Script

This script grants admin privileges to a user by email.
Usage: python make_user_admin.py user@example.com
"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal, User


def make_user_admin(email: str):
    """Grant admin privileges to a user by email"""
    db: Session = SessionLocal()

    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"❌ Error: User with email '{email}' not found.")
            print("\nAvailable users:")
            all_users = db.query(User).all()
            for u in all_users:
                admin_status = "✓ ADMIN" if u.is_admin else "  USER"
                print(f"  [{admin_status}] {u.email} (ID: {u.id}, Name: {u.full_name})")
            return False

        # Check if already admin
        if user.is_admin:
            print(f"✓ User '{email}' is already an admin!")
            return True

        # Make admin
        user.is_admin = True
        db.commit()

        print(f"✓ Successfully granted admin privileges to '{email}'")
        print(f"  User ID: {user.id}")
        print(f"  Name: {user.full_name}")
        print(f"  Admin: {user.is_admin}")
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        return False

    finally:
        db.close()


def list_all_users():
    """List all users in the database"""
    db: Session = SessionLocal()

    try:
        users = db.query(User).all()

        if not users:
            print("No users found in database.")
            return

        print(f"\n📋 All Users ({len(users)} total):")
        print("-" * 80)

        for user in users:
            admin_status = "✓ ADMIN" if user.is_admin else "  USER"
            print(f"  [{admin_status}] {user.email}")
            print(f"            ID: {user.id}, Name: {user.full_name}")
            print()

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_user_admin.py <email>")
        print("   or: python make_user_admin.py --list")
        print("\nExample: python make_user_admin.py user@example.com")
        list_all_users()
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_all_users()
    else:
        email = sys.argv[1]
        success = make_user_admin(email)
        sys.exit(0 if success else 1)
