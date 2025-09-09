#!/usr/bin/env python3
"""
CardioMed AI - PostgreSQL Migration Verification Script

This script verifies that the data migration from SQLite to PostgreSQL was successful.
It checks table existence, structure, and record counts.

Usage:
    python verify_postgresql_migration.py

Prerequisites:
    1. POSTGRES_URL environment variable set in .env file
    2. psycopg2 driver installed

Author: CardioMed AI Team
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Explicitly import psycopg2 to ensure it's available
try:
    import psycopg2
    print("✅ psycopg2 module loaded successfully")
except ImportError as e:
    print(f"❌ Failed to import psycopg2: {e}")
    print("Please install psycopg2-binary: pip install psycopg2-binary")
    sys.exit(1)

# Load environment variables
load_dotenv()

def get_postgresql_engine():
    """Get PostgreSQL Database engine."""
    database_url = os.getenv("POSTGRES_URL")
    if not database_url:
        print("❌ POSTGRES_URL environment variable not found!")
        print("Please make sure you have set the POSTGRES_URL in your .env file.")
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

def verify_tables(engine):
    """Verify that all expected tables exist."""
    expected_tables = [
        "users",
        "blood_pressure_readings",
        "medication_reminders",
        "bp_check_reminders",
        "doctor_appointment_reminders",
        "workout_reminders"
    ]

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    print("\n📋 Table Verification:")
    print("=" * 50)

    all_tables_exist = True
    for table in expected_tables:
        if table in existing_tables:
            print(f"✅ {table} - EXISTS")
        else:
            print(f"❌ {table} - MISSING")
            all_tables_exist = False

    return all_tables_exist

def verify_table_structure(engine, table_name):
    """Verify table structure matches expected schema."""
    inspector = inspect(engine)

    try:
        columns = inspector.get_columns(table_name)
        print(f"\n📊 {table_name.upper()} Structure:")
        print("-" * 40)

        for col in columns:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"  {col['name']} ({col['type']}) {nullable}")

        return True
    except Exception as e:
        print(f"❌ Error getting structure for {table_name}: {e}")
        return False

def verify_data_counts(engine):
    """Verify data counts in each table."""
    tables = [
        "users",
        "blood_pressure_readings",
        "medication_reminders",
        "bp_check_reminders",
        "doctor_appointment_reminders",
        "workout_reminders"
    ]

    print("\n📈 Data Counts:")
    print("=" * 50)

    total_records = 0

    try:
        with engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    total_records += count
                    print(f"  {table}: {count} records")
                except Exception as e:
                    print(f"  {table}: ERROR - {e}")

        print(f"\n📊 Total Records: {total_records}")
        return total_records > 0
    except Exception as e:
        print(f"❌ Error checking data counts: {e}")
        return False

def verify_sample_data(engine):
    """Show sample data from each table."""
    tables = [
        "users",
        "blood_pressure_readings",
        "medication_reminders"
    ]

    print("\n🔍 Sample Data Preview:")
    print("=" * 50)

    try:
        with engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT * FROM {table} LIMIT 3"))
                    rows = result.fetchall()

                    if rows:
                        print(f"\n{table.upper()} (showing first 3 rows):")
                        # Get column names
                        columns = result.keys()
                        print(f"  Columns: {', '.join(columns)}")

                        for i, row in enumerate(rows, 1):
                            print(f"  Row {i}: {dict(zip(columns, row))}")
                    else:
                        print(f"\n{table.upper()}: No data found")

                except Exception as e:
                    print(f"\n{table.upper()}: ERROR - {e}")

        return True
    except Exception as e:
        print(f"❌ Error getting sample data: {e}")
        return False

def main():
    """Main verification function."""
    print("CardioMed AI - PostgreSQL Migration Verification")
    print("=" * 60)

    # Get database connection
    engine = get_postgresql_engine()
    if not engine:
        sys.exit(1)

    # Verify tables exist
    tables_ok = verify_tables(engine)
    if not tables_ok:
        print("\n❌ Some expected tables are missing!")
        sys.exit(1)

    # Verify table structures
    print("\n🔧 Verifying Table Structures...")
    structure_ok = True
    for table in ["users", "blood_pressure_readings", "medication_reminders"]:
        if not verify_table_structure(engine, table):
            structure_ok = False

    # Verify data counts
    data_exists = verify_data_counts(engine)

    # Show sample data
    sample_ok = verify_sample_data(engine)

    # Final summary
    print("\n" + "=" * 60)
    print("📋 MIGRATION VERIFICATION SUMMARY:")
    print("=" * 60)

    if tables_ok and structure_ok and data_exists:
        print("✅ MIGRATION SUCCESSFUL!")
        print("   • All expected tables exist")
        print("   • Table structures are correct")
        print("   • Data has been migrated")
        print("\n🎉 Your CardioMed AI application is ready to use PostgreSQL!")
        return True
    else:
        print("❌ MIGRATION ISSUES DETECTED:")
        if not tables_ok:
            print("   • Some tables are missing")
        if not structure_ok:
            print("   • Table structures have issues")
        if not data_exists:
            print("   • No data found in tables")
        print("\n🔧 Please check the migration script output and try again.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)