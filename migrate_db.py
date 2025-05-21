import sqlite3
import os

def migrate_database():
    """
    Add the interpretation column to the blood_pressure_readings table
    """
    # Path to the SQLite database
    db_path = "./hypertension.db"
    
    # Check if the database file exists
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(blood_pressure_readings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "interpretation" not in columns:
            print("Adding 'interpretation' column to blood_pressure_readings table...")
            cursor.execute("ALTER TABLE blood_pressure_readings ADD COLUMN interpretation TEXT")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'interpretation' already exists.")
            
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
