#!/usr/bin/env python3
"""
CardioMed AI - Complete PostgreSQL Sequence Fix Script

This script fixes sequence issues for ALL tables in the PostgreSQL database where
auto-increment sequences are out of sync, causing duplicate key violations.

The script will:
1. Connect to the PostgreSQL Database
2. Check all tables with SERIAL/auto-increment columns
3. Fix sequences for all tables that need it
4. Test the fixes

Usage:
    python fix_all_postgresql_sequences.py

Prerequisites:
    1. POSTGRES_URL_PUBLIC environment variable set in .env file
    2. psycopg2 driver installed for PostgreSQL connection

Author: CardioMed AI Team
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
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

def get_tables_with_sequences(engine):
    """Get all tables that have auto-increment sequences."""
    tables_with_sequences = []
    
    # Define tables and their sequence names based on your models
    table_sequence_map = {
        'users': 'users_id_seq',
        'blood_pressure_readings': 'blood_pressure_readings_id_seq',
        'medication_reminders': 'medication_reminders_id_seq',
        'bp_check_reminders': 'bp_check_reminders_id_seq',
        'doctor_appointment_reminders': 'doctor_appointment_reminders_id_seq',
        'workout_reminders': 'workout_reminders_id_seq'
    }
    
    try:
        with engine.connect() as conn:
            for table_name, sequence_name in table_sequence_map.items():
                # Check if table exists
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    )
                """))
                table_exists = result.scalar()
                
                if table_exists:
                    # Check if sequence exists
                    result = conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.sequences 
                            WHERE sequence_schema = 'public' 
                            AND sequence_name = '{sequence_name}'
                        )
                    """))
                    sequence_exists = result.scalar()
                    
                    if sequence_exists:
                        tables_with_sequences.append((table_name, sequence_name))
                        print(f"✅ Found table '{table_name}' with sequence '{sequence_name}'")
                    else:
                        print(f"⚠️  Table '{table_name}' exists but sequence '{sequence_name}' not found")
                else:
                    print(f"⚠️  Table '{table_name}' does not exist")
                    
    except Exception as e:
        print(f"❌ Error checking tables and sequences: {e}")
        return []
    
    return tables_with_sequences

def check_sequence_status(engine, table_name, sequence_name):
    """Check the current sequence status and existing data for a table."""
    try:
        with engine.connect() as conn:
            # Get current sequence value using last_value (safer approach)
            result = conn.execute(text(f"SELECT last_value, is_called FROM {sequence_name}"))
            seq_info = result.fetchone()
            last_value = seq_info[0]
            is_called = seq_info[1]
            
            # If is_called is False, the sequence hasn't been used yet
            current_seq = last_value if is_called else 0
            next_seq = last_value + 1 if is_called else last_value
            
            # Get maximum ID in the table
            result = conn.execute(text(f"SELECT MAX(id) as max_id FROM {table_name}"))
            max_id = result.scalar()
            
            # Get count of records
            result = conn.execute(text(f"SELECT COUNT(*) as record_count FROM {table_name}"))
            record_count = result.scalar()
            
            print(f"\n📊 {table_name.upper()} Sequence Status:")
            print(f"   Last Sequence Value: {last_value}")
            print(f"   Sequence Called: {is_called}")
            print(f"   Current Effective Value: {current_seq}")
            print(f"   Next Value Would Be: {next_seq}")
            print(f"   Maximum ID in table: {max_id}")
            print(f"   Total records: {record_count}")
            
            return current_seq, next_seq, max_id, record_count
            
    except Exception as e:
        print(f"❌ Error checking sequence status for {table_name}: {e}")
        return None, None, None, None

def fix_sequence(engine, table_name, sequence_name, max_id):
    """Fix the PostgreSQL sequence by setting it to the correct value."""
    try:
        with engine.connect() as conn:
            # Calculate the next sequence value
            next_seq = (max_id or 0) + 1
            
            print(f"\n🔧 Fixing sequence for {table_name}...")
            print(f"   Setting sequence to: {max_id or 0} (next value will be {next_seq})")
            
            # Set the sequence to the maximum ID
            conn.execute(text(f"SELECT setval('{sequence_name}', {max_id or 0}, true)"))
            conn.commit()
            
            print(f"✅ Sequence fixed for {table_name}!")
            
            # Verify the fix
            result = conn.execute(text(f"SELECT last_value FROM {sequence_name}"))
            new_seq = result.scalar()
            print(f"   New sequence value: {new_seq}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error fixing sequence for {table_name}: {e}")
        return False

def test_table_insert(engine, table_name):
    """Test inserting a record into a table to verify the sequence works."""
    try:
        with engine.connect() as conn:
            print(f"\n🧪 Testing insert for {table_name}...")
            
            if table_name == "users":
                test_sql = text("""
                    INSERT INTO users (username, email, hashed_password, full_name, age, gender, height, weight, medical_conditions, medications)
                    VALUES (:username, :email, :hashed_password, :full_name, :age, :gender, :height, :weight, :medical_conditions, :medications)
                    RETURNING id
                """)
                test_params = {
                    'username': f'test_user_{table_name}',
                    'email': f'test_{table_name}@example.com',
                    'hashed_password': '$2b$12$test_hash',
                    'full_name': f'Test User {table_name}',
                    'age': 25,
                    'gender': 'Other',
                    'height': 170.0,
                    'weight': 70.0,
                    'medical_conditions': 'None',
                    'medications': 'None'
                }
            elif table_name == "blood_pressure_readings":
                test_sql = text("""
                    INSERT INTO blood_pressure_readings (user_id, systolic, diastolic, pulse, notes, interpretation)
                    VALUES (:user_id, :systolic, :diastolic, :pulse, :notes, :interpretation)
                    RETURNING id
                """)
                test_params = {
                    'user_id': 1,  # Assuming user 1 exists
                    'systolic': 120,
                    'diastolic': 80,
                    'pulse': 70,
                    'notes': 'Test reading',
                    'interpretation': 'Normal'
                }
            else:
                # For other tables, we'll skip the test as they require more complex setup
                print(f"   Skipping insert test for {table_name} (requires specific setup)")
                return True
            
            result = conn.execute(test_sql, test_params)
            new_id = result.scalar()
            conn.commit()
            
            print(f"✅ Test record created successfully with ID: {new_id}")
            
            # Clean up the test record
            conn.execute(text(f"DELETE FROM {table_name} WHERE id = {new_id}"))
            conn.commit()
            print("🧹 Test record cleaned up")
            
            return True
            
    except Exception as e:
        print(f"❌ Test insert failed for {table_name}: {e}")
        return False

def main():
    """Main function to fix all PostgreSQL sequence issues."""
    print("CardioMed AI - Complete PostgreSQL Sequence Fix")
    print("=" * 60)
    
    # Get database connection
    engine = get_postgresql_engine()
    if not engine:
        sys.exit(1)
    
    # Get all tables with sequences
    tables_with_sequences = get_tables_with_sequences(engine)
    if not tables_with_sequences:
        print("❌ No tables with sequences found!")
        sys.exit(1)
    
    print(f"\n🔍 Found {len(tables_with_sequences)} tables with sequences")
    
    fixed_count = 0
    
    for table_name, sequence_name in tables_with_sequences:
        print(f"\n{'='*50}")
        print(f"Processing: {table_name}")
        print(f"{'='*50}")
        
        # Check current status
        current_seq, next_seq, max_id, record_count = check_sequence_status(engine, table_name, sequence_name)
        if current_seq is None:
            continue
        
        # Determine if fix is needed
        if max_id is None or max_id == 0:
            print(f"✅ No existing records in {table_name}. Sequence should work correctly.")
            continue
        
        if next_seq > max_id:
            print(f"✅ Sequence for {table_name} appears to be correct.")
            print(f"   Next sequence value ({next_seq}) > Max ID ({max_id})")
        else:
            # Fix is needed
            print(f"⚠️  Sequence issue detected for {table_name}!")
            print(f"   Next sequence value ({next_seq}) <= Max ID ({max_id})")
            print(f"   This will cause duplicate key violations.")
            
            # Apply the fix
            if fix_sequence(engine, table_name, sequence_name, max_id):
                fixed_count += 1
        
        # Test the sequence (for key tables only)
        if table_name in ["users", "blood_pressure_readings"]:
            test_table_insert(engine, table_name)
    
    print("\n" + "=" * 60)
    print(f"SEQUENCE FIX SUMMARY")
    print("=" * 60)
    print(f"✅ Processed {len(tables_with_sequences)} tables")
    print(f"🔧 Fixed {fixed_count} sequences")
    
    if fixed_count > 0:
        print(f"\n🎉 Successfully fixed {fixed_count} sequence issues!")
        print("   All tables should now work correctly for new record creation.")
    else:
        print(f"\n✅ All sequences were already correctly synchronized!")
    
    print("\n💡 You can now use all endpoints without duplicate key errors.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)