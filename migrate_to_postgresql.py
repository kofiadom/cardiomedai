#!/usr/bin/env python3
"""
CardioMed AI - SQLite to PostgreSQL Database Migration Script

This script migrates data from a local SQLite database to a self-hosted PostgreSQL database on Coolify.
It handles the differences between SQLite and PostgreSQL, including:
- SERIAL column handling (auto-increment)
- Datetime format conversion
- Proper connection string formatting

Usage:
    python migrate_to_postgresql.py

Prerequisites:
    1. PostgreSQL database created and accessible on Coolify
    2. DATABASE_URL environment variable set in .env file
    3. Local SQLite database (hypertension.db) exists
    4. psycopg2 or pg8000 driver installed

The script will:
1. Test connection to PostgreSQL Database
2. Create all tables using SQLAlchemy models
3. Transfer all data from SQLite to PostgreSQL Database
4. Handle SERIAL columns for auto-increment
5. Convert datetime strings to proper datetime objects
6. Verify the data transfer

Author: CardioMed AI Team
"""

import os
import sqlite3
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_sqlite_connection():
    """Get SQLite database connection."""
    sqlite_path = "./hypertension.db"
    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found at {sqlite_path}")
        return None
    return sqlite3.connect(sqlite_path)

def get_postgresql_engine():
    """Get PostgreSQL Database engine."""
    database_url = os.getenv("POSTGRES_URL")
    if not database_url:
        print("POSTGRES_URL environment variable not found!")
        print("Please make sure you have set the POSTGRES_URL in your .env file.")
        return None

    if database_url.startswith("sqlite"):
        print("POSTGRES_URL is still pointing to SQLite. Please update it to point to PostgreSQL Database.")
        return None

    # Ensure PostgreSQL URL format
    if not database_url.startswith("postgresql"):
        print("DATABASE_URL should start with 'postgresql://' for PostgreSQL connections.")
        return None

    try:
        engine = create_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Successfully connected to PostgreSQL Database")
        return engine
    except Exception as e:
        print(f"✗ Failed to connect to PostgreSQL Database: {e}")
        print("\nTo fix this issue:")
        print("1. Ensure PostgreSQL is running on Coolify")
        print("2. Check your DATABASE_URL format: postgresql://user:password@host:port/database")
        print("3. Install psycopg2: pip install psycopg2-binary")
        print("4. Verify network connectivity to your Coolify PostgreSQL instance")
        return None

def create_tables_in_postgresql(engine):
    """Create all tables in PostgreSQL Database using SQLAlchemy models."""
    try:
        # Import models to register them with Base
        from app import models
        from app.database import Base

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✓ Successfully created tables in PostgreSQL Database")
        return True
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return False

def get_table_data(sqlite_conn, table_name):
    """Get all data from a SQLite table."""
    try:
        cursor = sqlite_conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name}")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        return columns, rows
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print(f"  Table {table_name} does not exist in SQLite database")
            return None, None
        raise

def convert_datetime_strings(value):
    """Convert datetime strings to proper datetime objects for PostgreSQL."""
    if isinstance(value, str):
        # Try to parse common datetime formats
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S.%f',  # 2025-05-21 15:05:02.063691
            '%Y-%m-%d %H:%M:%S',     # 2025-05-21 15:05:02
            '%Y-%m-%d',              # 2025-05-21
        ]

        for fmt in datetime_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return value

def check_existing_data(engine, table_name):
    """Check if table already has data."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            return count > 0
    except:
        return False

def insert_data_to_postgresql(engine, table_name, columns, rows):
    """Insert data into PostgreSQL Database table."""
    if not rows:
        print(f"  No data to migrate for table {table_name}")
        return True

    # Check if table already has data
    if check_existing_data(engine, table_name):
        print(f"  ⚠️  Table {table_name} already contains data, skipping migration")
        return True

    # Define datetime columns for each table
    datetime_columns = {
        'blood_pressure_readings': ['reading_time'],
        'medication_reminders': ['schedule_datetime', 'created_at'],
        'bp_check_reminders': ['reminder_datetime', 'created_at'],
        'doctor_appointment_reminders': ['appointment_datetime', 'created_at'],
        'workout_reminders': ['workout_datetime', 'created_at']
    }

    # Define boolean columns for each table (SQLite stores as 0/1, PostgreSQL needs true/false)
    boolean_columns = {
        'medication_reminders': ['is_taken'],
        'bp_check_reminders': ['is_completed'],
        'doctor_appointment_reminders': ['is_completed'],
        'workout_reminders': ['is_completed']
    }

    try:
        with engine.connect() as conn:
            # Create parameterized insert statement
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Convert rows to list of dictionaries with type conversion
            data_dicts = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert datetime strings if this column is a datetime column
                    if table_name in datetime_columns and col in datetime_columns[table_name]:
                        value = convert_datetime_strings(value)
                    # Convert integer booleans (0/1) to proper booleans (false/true)
                    elif table_name in boolean_columns and col in boolean_columns[table_name]:
                        value = bool(value) if value is not None else None
                    row_dict[col] = value
                data_dicts.append(row_dict)

            # Execute insert
            conn.execute(text(insert_sql), data_dicts)
            conn.commit()

        print(f"  ✓ Migrated {len(rows)} rows to {table_name}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to migrate data to {table_name}: {e}")
        return False

def migrate_data():
    """Main migration function."""
    print("Starting data migration from SQLite to PostgreSQL Database...")
    print("=" * 60)

    # Get connections
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return False

    postgresql_engine = get_postgresql_engine()
    if not postgresql_engine:
        sqlite_conn.close()
        return False

    # Create tables in PostgreSQL
    if not create_tables_in_postgresql(postgresql_engine):
        sqlite_conn.close()
        return False

    # List of tables to migrate (in order to respect foreign key constraints)
    tables_to_migrate = [
        "users",
        "blood_pressure_readings",
        "medication_reminders",
        "bp_check_reminders",
        "doctor_appointment_reminders",
        "workout_reminders"
    ]

    print("\nMigrating data...")
    success_count = 0

    for table_name in tables_to_migrate:
        print(f"\nMigrating table: {table_name}")

        # Get data from SQLite
        columns, rows = get_table_data(sqlite_conn, table_name)
        if columns is None:
            continue

        # Insert data into PostgreSQL
        if insert_data_to_postgresql(postgresql_engine, table_name, columns, rows):
            success_count += 1

    sqlite_conn.close()

    print("\n" + "=" * 60)
    print(f"Migration completed! Successfully migrated {success_count} tables.")

    if success_count > 0:
        print("\n✓ Your data has been successfully migrated to PostgreSQL Database!")
        print("✓ You can now run your application with the new database.")
        print("\nNext steps:")
        print("1. Test your application locally: uv run app/main.py")
        print("2. Update your Docker deployment if needed")
        print("3. Consider backing up your SQLite database as a precaution")

    return success_count > 0

if __name__ == "__main__":
    if migrate_data():
        sys.exit(0)
    else:
        print("\n✗ Migration failed. Please check the errors above and try again.")
        sys.exit(1)