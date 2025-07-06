import sqlite3
import os

def migrate_database():
    """
    Add the interpretation column to the blood_pressure_readings table
    and create the medication_reminders table if it doesn't exist
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

        # Check if medication_reminders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='medication_reminders'")
        table_exists = cursor.fetchone()

        if not table_exists:
            print("Creating 'medication_reminders' table...")
            cursor.execute("""
                CREATE TABLE medication_reminders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL,
                    dosage VARCHAR NOT NULL,
                    schedule_datetime DATETIME NOT NULL,
                    schedule_dosage VARCHAR NOT NULL,
                    is_taken BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()
            print("Table 'medication_reminders' created successfully.")
        else:
            print("Table 'medication_reminders' already exists.")

        # Check if bp_check_reminders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bp_check_reminders'")
        bp_table_exists = cursor.fetchone()

        if not bp_table_exists:
            print("Creating 'bp_check_reminders' table...")
            cursor.execute("""
                CREATE TABLE bp_check_reminders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    reminder_datetime DATETIME NOT NULL,
                    bp_category VARCHAR NOT NULL,
                    is_completed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()
            print("Table 'bp_check_reminders' created successfully.")
        else:
            print("Table 'bp_check_reminders' already exists.")

        # Check if doctor_appointment_reminders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='doctor_appointment_reminders'")
        doctor_table_exists = cursor.fetchone()

        if not doctor_table_exists:
            print("Creating 'doctor_appointment_reminders' table...")
            cursor.execute("""
                CREATE TABLE doctor_appointment_reminders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    appointment_datetime DATETIME NOT NULL,
                    doctor_name VARCHAR NOT NULL,
                    appointment_type VARCHAR,
                    location VARCHAR,
                    is_completed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()
            print("Table 'doctor_appointment_reminders' created successfully.")
        else:
            print("Table 'doctor_appointment_reminders' already exists.")

        # Check if workout_reminders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workout_reminders'")
        workout_table_exists = cursor.fetchone()

        if not workout_table_exists:
            print("Creating 'workout_reminders' table...")
            cursor.execute("""
                CREATE TABLE workout_reminders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    workout_datetime DATETIME NOT NULL,
                    workout_type VARCHAR NOT NULL,
                    duration_minutes INTEGER,
                    location VARCHAR,
                    is_completed BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            conn.commit()
            print("Table 'workout_reminders' created successfully.")
        else:
            print("Table 'workout_reminders' already exists.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
