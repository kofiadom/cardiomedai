#!/usr/bin/env python3
"""
CardioMed AI - PostgreSQL Sequence Fix Script

This script fixes the sequence issue in PostgreSQL where the auto-increment 
sequence is out of sync, causing duplicate key violations.

The error occurs when:
1. Data was migrated manually without updating the sequence
2. The sequence is still at 1 but records with ID=1 already exist

This script will:
1. Connect to the PostgreSQL Database
2. Find the maximum ID in the users table
3. Reset the sequence to start from the next available ID

Usage:
    python fix_postgresql_sequence.py

Prerequisites:
    1. POSTGRES_URL_PUBLIC environment variable set in .env file
    2. psycopg2 driver installed for PostgreSQL connection

Author: CardioMed AI Team
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_postgresql_engine():
    """Get PostgreSQL database engine from environment."""
    # Try both possible environment variable names
    database_url = os.getenv("POSTGRES_URL_PUBLIC") or os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ PostgreSQL URL environment variable not found!")
        print("Please make sure you have set POSTGRES_URL_PUBLIC or DATABASE_URL in your .env file.")
        return None

    # Ensure it's a PostgreSQL URL
    if not database_url.startswith("postgresql"):
        print("❌ Database URL should start with 'postgresql://' for PostgreSQL connections.")
        print(f"Current URL starts with: {database_url.split('://')[0]}")
        return None

    try:
        engine = create_engine(database_url, echo=False)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Successfully connected to PostgreSQL Database")
        return engine
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL Database: {e}")
        return None

def check_current_sequence_status(engine):
    """Check the current sequence status and existing data."""
    try:
        with engine.connect() as conn:
            # Get current sequence value using last_value (safer approach)
            result = conn.execute(text("SELECT last_value, is_called FROM users_id_seq"))
            seq_info = result.fetchone()
            last_value = seq_info[0]
            is_called = seq_info[1]
            
            # If is_called is False, the sequence hasn't been used yet
            current_seq = last_value if is_called else 0
            next_seq = last_value + 1 if is_called else last_value
            
            # Get maximum ID in the table
            result = conn.execute(text("SELECT MAX(id) as max_id FROM users"))
            max_id = result.scalar()
            
            # Get count of records
            result = conn.execute(text("SELECT COUNT(*) as record_count FROM users"))
            record_count = result.scalar()
            
            print(f"\n📊 Current Sequence Status:")
            print(f"   Last Sequence Value: {last_value}")
            print(f"   Sequence Called: {is_called}")
            print(f"   Current Effective Value: {current_seq}")
            print(f"   Next Value Would Be: {next_seq}")
            print(f"   Maximum ID in table: {max_id}")
            print(f"   Total records: {record_count}")
            
            return current_seq, next_seq, max_id, record_count
            
    except Exception as e:
        print(f"❌ Error checking sequence status: {e}")
        return None, None, None, None

def fix_postgresql_sequence(engine, max_id):
    """Fix the PostgreSQL sequence by setting it to the correct value."""
    try:
        with engine.connect() as conn:
            # Calculate the next sequence value
            next_seq = (max_id or 0) + 1
            
            print(f"\n🔧 Fixing PostgreSQL sequence...")
            print(f"   Setting sequence to: {max_id or 0} (next value will be {next_seq})")
            
            # Set the sequence to the maximum ID
            conn.execute(text(f"SELECT setval('users_id_seq', {max_id or 0}, true)"))
            conn.commit()
            
            print("✅ PostgreSQL sequence fixed successfully!")
            
            # Verify the fix
            result = conn.execute(text("SELECT last_value FROM users_id_seq"))
            new_seq = result.scalar()
            print(f"   New sequence value: {new_seq}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error fixing PostgreSQL sequence: {e}")
        return False

def test_user_creation(engine):
    """Test creating a new user to verify the fix."""
    try:
        with engine.connect() as conn:
            print(f"\n🧪 Testing user creation...")
            
            # Try to insert a test user
            test_sql = text("""
                INSERT INTO users (username, email, hashed_password, full_name, age, gender, height, weight, medical_conditions, medications)
                VALUES (:username, :email, :hashed_password, :full_name, :age, :gender, :height, :weight, :medical_conditions, :medications)
                RETURNING id
            """)
            
            test_params = {
                'username': 'test_user_temp',
                'email': 'test_temp@example.com',
                'hashed_password': '$2b$12$test_hash',
                'full_name': 'Test User',
                'age': 25,
                'gender': 'Other',
                'height': 170.0,
                'weight': 70.0,
                'medical_conditions': 'None',
                'medications': 'None'
            }
            
            result = conn.execute(test_sql, test_params)
            new_user_id = result.scalar()
            conn.commit()
            
            print(f"✅ Test user created successfully with ID: {new_user_id}")
            
            # Clean up the test user
            conn.execute(text("DELETE FROM users WHERE username = 'test_user_temp'"))
            conn.commit()
            print("🧹 Test user cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Test user creation failed: {e}")
        return False

def show_existing_users(engine):
    """Show existing users to understand the current state."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, username, email FROM users ORDER BY id LIMIT 5"))
            users = result.fetchall()
            
            if users:
                print(f"\n👥 Existing Users (first 5):")
                for user in users:
                    print(f"   ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")
            else:
                print(f"\n👥 No existing users found")
                
    except Exception as e:
        print(f"❌ Error showing existing users: {e}")

def main():
    """Main function to fix the PostgreSQL sequence issue."""
    print("CardioMed AI - PostgreSQL Sequence Fix")
    print("=" * 50)
    
    # Get database connection
    engine = get_postgresql_engine()
    if not engine:
        sys.exit(1)
    
    # Show existing users
    show_existing_users(engine)
    
    # Check current status
    current_seq, next_seq, max_id, record_count = check_current_sequence_status(engine)
    if current_seq is None:
        sys.exit(1)
    
    # Determine if fix is needed
    if max_id is None or max_id == 0:
        print("\n✅ No existing records found. Sequence should work correctly.")
        return True
    
    if next_seq > max_id:
        print(f"\n✅ Sequence appears to be correct.")
        print(f"   Next sequence value ({next_seq}) > Max ID ({max_id})")
        
        # Still test user creation to be sure
        if test_user_creation(engine):
            print("\n🎉 Everything is working correctly!")
            return True
        else:
            print("\n⚠️  User creation test failed despite correct sequence.")
            return False
    
    # Fix is needed
    print(f"\n⚠️  Sequence issue detected!")
    print(f"   Next sequence value ({next_seq}) <= Max ID ({max_id})")
    print(f"   This will cause duplicate key violations.")
    
    # Apply the fix
    if fix_postgresql_sequence(engine, max_id):
        # Test the fix
        if test_user_creation(engine):
            print("\n🎉 PostgreSQL sequence fixed successfully!")
            print("   You can now create new users without duplicate key errors.")
            return True
        else:
            print("\n❌ Fix applied but test creation still failed.")
            return False
    else:
        print("\n❌ Failed to fix PostgreSQL sequence.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)