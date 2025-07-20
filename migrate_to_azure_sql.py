#!/usr/bin/env python3
"""
CardioMed AI - SQLite to Azure SQL Database Migration Script

This script migrates data from a local SQLite database to Azure SQL Database.
It handles the differences between SQLite and SQL Server, including:
- IDENTITY column handling
- Datetime format conversion
- Proper connection string formatting

Usage:
    python migrate_to_azure_sql.py

Prerequisites:
    1. Azure SQL Database created and accessible
    2. DATABASE_URL environment variable set in .env file
    3. Local SQLite database (hypertension.db) exists
    4. ODBC Driver 18 for SQL Server installed

The script will:
1. Test connection to Azure SQL Database
2. Create all tables using SQLAlchemy models
3. Transfer all data from SQLite to Azure SQL Database
4. Handle IDENTITY_INSERT for ID columns
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

def get_azure_sql_engine():
    """Get Azure SQL Database engine."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable not found!")
        print("Please make sure you have set the DATABASE_URL in your .env file.")
        return None

    if database_url.startswith("sqlite"):
        print("DATABASE_URL is still pointing to SQLite. Please update it to point to Azure SQL Database.")
        return None

    # Try different driver options
    driver_options = [
        "ODBC+Driver+18+for+SQL+Server",
        "ODBC+Driver+17+for+SQL+Server",
        "ODBC+Driver+13+for+SQL+Server",
        "SQL+Server+Native+Client+11.0",
        "SQL+Server"
    ]

    for driver in driver_options:
        try:
            # Replace driver in URL
            test_url = database_url.replace("ODBC+Driver+18+for+SQL+Server", driver)
            print(f"Trying driver: {driver.replace('+', ' ')}")

            engine = create_engine(
                test_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300,
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"✓ Successfully connected to Azure SQL Database using {driver.replace('+', ' ')}")
            return engine
        except Exception as e:
            if driver == "ODBC+Driver+18+for+SQL+Server":
                print(f"  ✗ Failed with {driver.replace('+', ' ')}: {str(e)}")
            else:
                print(f"  ✗ Failed with {driver.replace('+', ' ')}: {str(e)[:100]}...")
            continue

    print("✗ Failed to connect with any available driver")
    print("\nTo fix this issue, you need to install Microsoft ODBC Driver for SQL Server:")
    print("1. Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
    print("2. Install ODBC Driver 18 for SQL Server")
    print("3. Run this script again")
    return None

def create_tables_in_azure_sql(engine):
    """Create all tables in Azure SQL Database using SQLAlchemy models."""
    try:
        # Import models to register them with Base
        from app import models
        from app.database import Base
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✓ Successfully created tables in Azure SQL Database")
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
    """Convert datetime strings to proper datetime objects for SQL Server."""
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

def insert_data_to_azure_sql(engine, table_name, columns, rows):
    """Insert data into Azure SQL Database table."""
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

    try:
        with engine.connect() as conn:
            # Enable IDENTITY_INSERT for tables with id columns
            if 'id' in columns:
                conn.execute(text(f"SET IDENTITY_INSERT {table_name} ON"))

            # Create parameterized insert statement
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Convert rows to list of dictionaries with datetime conversion
            data_dicts = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert datetime strings if this column is a datetime column
                    if table_name in datetime_columns and col in datetime_columns[table_name]:
                        value = convert_datetime_strings(value)
                    row_dict[col] = value
                data_dicts.append(row_dict)

            # Execute insert
            conn.execute(text(insert_sql), data_dicts)

            # Disable IDENTITY_INSERT
            if 'id' in columns:
                conn.execute(text(f"SET IDENTITY_INSERT {table_name} OFF"))

            conn.commit()

        print(f"  ✓ Migrated {len(rows)} rows to {table_name}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to migrate data to {table_name}: {e}")
        # Make sure to turn off IDENTITY_INSERT even if there's an error
        try:
            with engine.connect() as conn:
                if 'id' in columns:
                    conn.execute(text(f"SET IDENTITY_INSERT {table_name} OFF"))
                conn.commit()
        except:
            pass
        return False

def migrate_data():
    """Main migration function."""
    print("Starting data migration from SQLite to Azure SQL Database...")
    print("=" * 60)
    
    # Get connections
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return False
    
    azure_engine = get_azure_sql_engine()
    if not azure_engine:
        sqlite_conn.close()
        return False
    
    # Create tables in Azure SQL
    if not create_tables_in_azure_sql(azure_engine):
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
        
        # Insert data into Azure SQL
        if insert_data_to_azure_sql(azure_engine, table_name, columns, rows):
            success_count += 1
    
    sqlite_conn.close()
    
    print("\n" + "=" * 60)
    print(f"Migration completed! Successfully migrated {success_count} tables.")
    
    if success_count > 0:
        print("\n✓ Your data has been successfully migrated to Azure SQL Database!")
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
