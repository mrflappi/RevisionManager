import sqlite3

DATABASE_FILE = "timetable.db"

# Connect to the SQLite database
conn = sqlite3.connect(DATABASE_FILE)
cursor = conn.cursor()

# Drop table if it already exists
cursor.execute("DROP TABLE IF EXISTS Subjects")

# Create the Subjects table
cursor.execute("""
CREATE TABLE Subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    week TEXT NOT NULL,
    period TEXT NOT NULL,
    subject TEXT NOT NULL
)
""")

# Timetable data with corrections and full subject names
week1_data = {
    "Monday": ["EPQ", None, "Supp", "Computer Science", "Art"],
    "Tuesday": ["Computer Science", "Art", None, "Maths", None],
    "Wednesday": ["Art", "EPQ", "Maths", None, "Computer Science"],
    "Thursday": ["Maths", "Supp", "Computer Science", "Art", None],
    "Friday": ["Supp", "Computer Science", "Art", None, "Maths"]  # Corrected "Ar" to period 3
}

week2_data = {
    "Monday": ["Computer Science", "Art", None, "Maths", None],
    "Tuesday": ["Maths", "Supp", "Computer Science", "Art", None],
    "Wednesday": ["Supp", "Computer Science", "Art", None, "Maths"],
    "Thursday": [None, "EPQ", "Maths", "Supp", None],  # Corrected row
    "Friday": [None, "Maths", "PSHE", "Computer Science", "Art"]   # Corrected row
}

# Insert data into Subjects table
for week, data in [("A", week1_data), ("B", week2_data)]:  # Using integers for weeks
    for day, subjects in data.items():
        for period, subject in enumerate(subjects, start=1):
            if subject:  # Only insert if there's a subject in that period
                cursor.execute("""
                INSERT INTO Subjects (day, week, period, subject)
                VALUES (?, ?, ?, ?)
                """, (day, week, str(period), subject))  # Store period as a string

# Commit changes and close the connection
conn.commit()
conn.close()

print("Timetable data has been inserted into the Subjects table successfully.")
