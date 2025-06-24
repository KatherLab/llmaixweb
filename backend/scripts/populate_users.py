#!/usr/bin/env python3
"""
Script to initialize admin users and add multiple other users.

Usage:
python -m scripts.populate_users
For adding an admin user: python -m scripts.populate_users --admin
For adding a regular user: python -m scripts.populate_users --user
For adding multiple users from a YAML file: python -m scripts.populate_users --import-yaml users.yaml
"""

import sys
import os
import argparse
import getpass
from pathlib import Path

import yaml
from typing import Optional

# Insert the absolute path to backend/src into sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from backend.src.db.session import SessionLocal, engine
from backend.src.db.base import Base
from backend.src.models.user import User, UserRole
from backend.src.core.security import get_password_hash
import re


def init_db():
    """Initialize the database by creating all tables if they don't exist"""
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        sys.exit(1)


def validate_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(email_pattern.match(email))


def validate_password(password: str) -> bool:
    """Validate password strength"""
    # At least 8 characters, one uppercase, one lowercase, one digit
    if len(password) < 8:
        print("Password must be at least 8 characters long.")
        return False
    if not any(c.isupper() for c in password):
        print("Password must contain at least one uppercase letter.")
        return False
    if not any(c.islower() for c in password):
        print("Password must contain at least one lowercase letter.")
        return False
    if not any(c.isdigit() for c in password):
        print("Password must contain at least one digit.")
        return False
    return True


def user_exists(email: str) -> bool:
    """Check if a user with the given email already exists"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        return user is not None
    finally:
        db.close()


def get_user_input(role: UserRole) -> tuple[str, str, str]:
    """Get user input interactively"""
    print(f"\nCreating a new {role.value} account")
    print("=========================")
    # Get email
    while True:
        email = input("Email: ").strip()
        if not validate_email(email):
            print("Invalid email format. Please try again.")
            continue
        if user_exists(email):
            print(
                "A user with this email already exists. Please use a different email."
            )
            continue
        break
    # Get full name
    full_name = input("Full Name: ").strip()
    # Get password with confirmation
    while True:
        password = getpass.getpass("Password: ")
        if not validate_password(password):
            continue
        confirm_password = getpass.getpass("Confirm Password: ")
        if password != confirm_password:
            print("Passwords do not match. Please try again.")
            continue
        break
    return email, full_name, password


def create_user(
    email: str, full_name: str, password: str, role: UserRole
) -> Optional[User]:
    """Create a new user in the database"""
    db = SessionLocal()
    try:
        # Check if user already exists
        if user_exists(email):
            print(f"User with email {email} already exists.")
            return None
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=role.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"\nSuccessfully created {role.value} account: {email}")
        return user
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {e}")
        return None
    finally:
        db.close()


def list_users():
    """List all users in the database"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("\nNo users found in the database.")
            return
        print("\nExisting Users:")
        print("===============")
        for user in users:
            print(
                f"ID: {user.id} | Email: {user.email} | Name: {user.full_name} | Role: {user.role.value}"
            )
    except Exception as e:
        print(f"Error listing users: {e}")
    finally:
        db.close()


def create_admin_user():
    """Create an admin user interactively"""
    email, full_name, password = get_user_input(UserRole.admin)
    create_user(email, full_name, password, UserRole.admin)


def create_regular_user():
    """Create a regular user interactively"""
    email, full_name, password = get_user_input(UserRole.user)
    create_user(email, full_name, password, UserRole.user)


def check_admin_exists() -> bool:
    """Check if any admin user already exists"""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == UserRole.admin).first()
        return admin is not None
    finally:
        db.close()


def import_users_from_yaml(yaml_file: str):
    """Import multiple users from a YAML file"""
    if not os.path.exists(yaml_file):
        print(f"Error: YAML file {yaml_file} not found.")
        return

    try:
        with open(yaml_file, "r") as file:
            users_data = yaml.safe_load(file)
        if not isinstance(users_data, list):
            print("Error: YAML file should contain a list of user entries.")
            return

        successful_imports = 0
        failed_imports = 0

        for idx, user_data in enumerate(users_data):
            # Validate required fields
            if not isinstance(user_data, dict):
                print(f"Error: User entry {idx + 1} is not a dictionary. Skipping.")
                failed_imports += 1
                continue

            if (
                "email" not in user_data
                or "full_name" not in user_data
                or "password" not in user_data
            ):
                print(
                    f"Error: User entry {idx + 1} is missing required fields (email, full_name, password). Skipping."
                )
                failed_imports += 1
                continue

            email = user_data["email"]
            full_name = user_data["full_name"]
            password = user_data["password"]
            role = UserRole.user  # Default role for imported users

            # Validate email
            if not validate_email(email):
                print(f"Error: Invalid email format for user {email}. Skipping.")
                failed_imports += 1
                continue

            # Validate password (optionally disable for bulk imports)
            if not validate_password(password):
                print(
                    f"Error: Password for user {email} does not meet requirements. Skipping."
                )
                failed_imports += 1
                continue

            # Create the user
            user = create_user(email, full_name, password, role)
            if user:
                successful_imports += 1
            else:
                failed_imports += 1

        print(
            f"\nImport summary: {successful_imports} users imported successfully, {failed_imports} failed."
        )

    except Exception as e:
        print(f"Error importing users from YAML: {e}")


def generate_sample_yaml():
    """Generate a sample YAML file for user import"""
    sample_content = """# Sample YAML file for importing multiple users
# Each user entry should have email, full_name, and password fields
# All imported users will be created with the 'user' role
- email: user1@example.com
  full_name: User One
  password: User1Pass
- email: user2@example.com
  full_name: User Two
  password: User2Pass
- email: user3@example.com
  full_name: User Three
  password: User3Pass
"""
    filename = "sample_users.yaml"
    with open(filename, "w") as file:
        file.write(sample_content)

    print(f"Sample YAML file created: {filename}")
    print("You can modify this file and then import users with:")
    print(f"python -m scripts.populate_users --import-yaml {filename}")


def main():
    parser = argparse.ArgumentParser(description="User management script")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--admin", action="store_true", help="Create an admin user")
    group.add_argument("--user", action="store_true", help="Create a regular user")
    group.add_argument("--list", action="store_true", help="List all users")
    group.add_argument(
        "--import-yaml", metavar="FILE", help="Import multiple users from a YAML file"
    )
    group.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate a sample YAML file for importing users",
    )

    args = parser.parse_args()

    # Initialize the database if needed
    print("Initializing database if needed...")
    init_db()

    if args.list:
        list_users()
    elif args.admin:
        create_admin_user()
    elif args.user:
        create_regular_user()
    elif args.import_yaml:
        import_users_from_yaml(args.import_yaml)
    elif args.generate_sample:
        generate_sample_yaml()
    else:
        # If no arguments are provided, check if admin exists
        if not check_admin_exists():
            print("No admin user found. Creating initial admin user...")
            create_admin_user()
        else:
            # Show help menu
            parser.print_help()
            # List available users
            list_users()
            # Ask what they want to do
            print("\nWhat would you like to do?")
            print("1. Create admin user")
            print("2. Create regular user")
            print("3. Import users from YAML file")
            print("4. Generate sample YAML file")
            print("5. Exit")

            choice = input("\nEnter your choice (1-5): ")

            if choice == "1":
                create_admin_user()
            elif choice == "2":
                create_regular_user()
            elif choice == "3":
                yaml_file = input("Enter path to YAML file: ")
                import_users_from_yaml(yaml_file)
            elif choice == "4":
                generate_sample_yaml()
            else:
                print("Exiting.")


if __name__ == "__main__":
    main()
