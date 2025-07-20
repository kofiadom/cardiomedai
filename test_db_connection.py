#!/usr/bin/env python3
"""
Simple script to test Azure SQL Database connection
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test database connection using different methods"""
    
    # Get credentials from environment
    db_host = os.getenv("DB_HOST", "cardiomed-ai-db-server.database.windows.net")
    db_name = os.getenv("DB_NAME", "cardiomed-ai-db")
    db_user = os.getenv("DB_USER", "harold")
    db_password = os.getenv("DB_PASSWORD")
    
    print("=== Database Connection Test ===")
    print(f"Host: {db_host}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {'*' * len(db_password) if db_password else 'NOT SET'}")
    print()
    
    if not db_password:
        print("❌ ERROR: DB_PASSWORD environment variable not set!")
        return False
    
    # Test 1: Try with pyodbc (if available)
    print("🔍 Testing with pyodbc...")
    try:
        import pyodbc
        
        # Connection string for Azure SQL
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={db_host};"
            f"DATABASE={db_name};"
            f"UID={db_user};"
            f"PWD={db_password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30"
        )
        
        print("Attempting connection...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        print(f"✅ pyodbc connection successful! Test query result: {result[0]}")
        
        # Test actual table access
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"✅ Users table accessible. Count: {user_count}")
        except Exception as e:
            print(f"⚠️  Users table access failed: {e}")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print("❌ pyodbc not installed. Install with: pip install pyodbc")
    except Exception as e:
        print(f"❌ pyodbc connection failed: {e}")
    
    # Test 2: Try with SQLAlchemy (if available)
    print("\n🔍 Testing with SQLAlchemy...")
    try:
        from sqlalchemy import create_engine, text
        
        # SQLAlchemy connection string
        database_url = (
            f"mssql+pyodbc://{db_user}:{db_password}@{db_host}:1433/{db_name}"
            f"?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30"
        )
        
        print("Creating SQLAlchemy engine...")
        engine = create_engine(database_url, echo=False)
        
        print("Testing connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            print(f"✅ SQLAlchemy connection successful! Test query result: {test_value}")
            
            # Test actual table access
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.fetchone()[0]
                print(f"✅ Users table accessible. Count: {user_count}")
            except Exception as e:
                print(f"⚠️  Users table access failed: {e}")
        
        return True
        
    except ImportError:
        print("❌ SQLAlchemy not installed. Install with: pip install sqlalchemy")
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
    
    return False

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("\n=== Environment Variables Check ===")
    
    required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    all_set = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == "DB_PASSWORD":
                print(f"✅ {var}: {'*' * len(value)}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_set = False
    
    return all_set

if __name__ == "__main__":
    print("CardioMed AI - Database Connection Test")
    print("=" * 50)
    
    # Test environment variables first
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n❌ Some environment variables are missing!")
        print("Make sure your .env file contains all required variables.")
        sys.exit(1)
    
    # Test database connection
    connection_ok = test_connection()
    
    if connection_ok:
        print("\n🎉 Database connection test PASSED!")
        print("Your database credentials are working correctly.")
    else:
        print("\n❌ Database connection test FAILED!")
        print("Check your credentials and network connectivity.")
        sys.exit(1)
