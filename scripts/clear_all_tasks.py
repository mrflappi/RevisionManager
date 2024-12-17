import sqlite3

DATABASE_FILE = "timetable.db"

# Connect to the SQLite database
conn = sqlite3.connect(DATABASE_FILE)
cursor = conn.cursor()

# Drop tasks table
cursor.execute("DROP TABLE IF EXISTS Tasks")

# Commit changes and close the connection
conn.commit()
conn.close()

print("Task data has been cleared sucessfully.")