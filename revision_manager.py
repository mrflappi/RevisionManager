import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import sqlite3
import json
import os
import sys
from PIL import Image, ImageTk
from datetime import datetime, timedelta

DATABASE_FILE = "timetable.db"
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "auto_reschedule": True,
    "max_tasks_lesson": 1,
    "max_tasks_afternoon": 3,
    "week_rotation_length": 2,
    "use_lettered_weeks": False,
    "start_week_date": "2024-11-18"
}

def get_assets_path():
    if getattr(sys, "frozen", False):
        # If the program is running as a bundled executable
        base_path = sys._MEIPASS
    else:
        # If running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "assets")


def get_data_path():
    if getattr(sys, "frozen", False):
        # If the program is running as a bundled executable
        base_path = sys._MEIPASS
    else:
        # If running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "data")

def load_data(datafile):
    with open(os.path.join(get_data_path(), f"{datafile}.json")) as file:
        data = json.load(file)

    return data

# Save Data Management Class
class SaveManager:

    # Initialize Settings
    def init_settings():

        # Check if the settings file exists
        if not os.path.exists(SETTINGS_FILE):
            print("Settings file not found. Creating default settings file...")
            SaveManager.save_settings(DEFAULT_SETTINGS)  # Create the file with default settings

        # Update settings to contain any variables not found
        else:
            updated_settings = DEFAULT_SETTINGS
            settings = SaveManager.load_settings()

            # Input existing values over default values
            for key, value in settings.items():
                updated_settings.update({key: value})

            SaveManager.save_settings(updated_settings)

    # Load settings from the file
    def load_settings():
        with open(SETTINGS_FILE, "r") as file:
            settings = json.load(file)

        return settings

    # Save settings to the file
    def save_settings(settings):
        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)

    # Change the value of a setting
    def update_setting(key, value):
        settings = SaveManager.load_settings() # Load current settings
        settings[key] = value # Update the specific key
        SaveManager.save_settings(settings) # Save the updated settings

    # Change the values of many settings
    def update_many_settings(updated_settings):
        settings = SaveManager.load_settings()  # Load current settings
        for key, value in updated_settings.items():
            if key in settings: # Check if each key is in settings
                settings[key] = value # Update this key

        SaveManager.save_settings(settings) # Save the updated settings

    # Initialize the Database
    def init_db():
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        # Create a Subjects table for recurring weekly subjects
        c.execute("""CREATE TABLE IF NOT EXISTS Subjects (
                        id INTEGER PRIMARY KEY,
                        week TEXT,
                        day TEXT,
                        period TEXT,
                        subject TEXT
                    )"""
        )

        # Create a Tasks table for date-specific tasks
        c.execute("""CREATE TABLE IF NOT EXISTS Tasks (
                        id INTEGER PRIMARY KEY,
                        task TEXT,
                        date TEXT,
                        period TEXT,
                        completed BOOLEAN DEFAULT 0
                    )"""
        )

        # Create a Holidays table for holiday dates
        c.execute("""CREATE TABLE IF NOT EXISTS Holidays (
                        date TEXT PRIMARY KEY
                    )"""
        )

        conn.commit()
        conn.close()

        SaveManager.update_db()

    # class called update_db which checks if the database uses the old letter-based week system and updates it to the new number-based system
    def update_db():
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        # Check if the Subjects table has the week column
        c.execute("PRAGMA table_info(Subjects)")
        columns = c.fetchall()
        column_names = [col[1] for col in columns]

        if "week" in column_names:
            # Check if the week column is in the old letter-based system
            c.execute("SELECT DISTINCT week FROM Subjects")
            weeks = c.fetchall()
            if weeks and weeks[0][0] in ["A", "B"]:
                # Update the week column to the new number-based system
                c.execute("UPDATE Subjects SET week = 1 WHERE week = 'A'")
                c.execute("UPDATE Subjects SET week = 2 WHERE week = 'B'")
                conn.commit()

        conn.close()

# Main App Class
class RevisionManagerApp:

    # --Main Program and Timetable Management--

    def __init__(self, root):
        self.root = root
        self.root.title("Revision Manager")
        self.system_setup()
        self.schedule_auto_rescheduling()

    def system_setup(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # Load settings
        settings = SaveManager.load_settings()

        # Define the start date for Week 1 and initialize variables
        self.start_date = datetime.strptime(settings.get("start_week_date", "2024-11-18"), "%Y-%m-%d")
        self.today_date = datetime.today()
        self.current_week_date = self.start_date + timedelta(weeks=(self.today_date - self.start_date).days // 7)

        # Load custom week rotation length and week display type from settings
        self.week_rotation_length = settings.get("week_rotation_length", 2)
        self.use_lettered_weeks = settings.get("use_lettered_weeks", False)
        self.current_week_number = self.get_week_number_for_date(self.today_date)

        # Store subjects and tasks
        self.subjects = {}
        self.tasks = {}

        # UI elements
        self.settings_frame = tk.Frame(self.root)
        self.settings_frame.place(x=10, y=10)

        self.version = load_data("app").get("version", "not found")
        tk.Label(self.settings_frame, text=f"Version: {self.version}").pack(anchor="w")

        settings_image = Image.open(os.path.join(get_assets_path(), "settings.png")).resize(size=[24, 24])
        self.settings_photoimage = ImageTk.PhotoImage(settings_image) 
        tk.Button(self.settings_frame, image=self.settings_photoimage, command=self.open_settings).pack(anchor="w")

        self.week_label = tk.Label(self.root, font=('Arial', 16))
        self.week_label.pack(pady=10)

        self.navigation_frame = tk.Frame(self.root)
        self.navigation_frame.pack(pady=10)

        prevweek_image = Image.open(os.path.join(get_assets_path(), "left.png")).resize(size=[24, 24])
        self.prevweek_photoimage = ImageTk.PhotoImage(prevweek_image)
        tk.Button(self.navigation_frame, image=self.prevweek_photoimage, command=self.prev_week).grid(row=0, column=0, padx=5)

        currweek_image = Image.open(os.path.join(get_assets_path(), "today.png")).resize(size=[32, 32])
        self.currweek_photoimage = ImageTk.PhotoImage(currweek_image)
        tk.Button(self.navigation_frame, image=self.currweek_photoimage, command=self.go_to_current_week).grid(row=0, column=1, padx=5)

        nextweek_image = Image.open(os.path.join(get_assets_path(), "right.png")).resize(size=[24, 24], resample=Image.Resampling.BILINEAR)
        self.nextweek_photoimage = ImageTk.PhotoImage(nextweek_image)
        tk.Button(self.navigation_frame, image=self.nextweek_photoimage, command=self.next_week).grid(row=0, column=2, padx=5)

        self.timetable_frame = tk.Frame(self.root)
        self.timetable_frame.pack(pady=(0, 15), padx=15)

        self.show_schedule()

    def show_schedule(self):
        # Load data from the database for the current week
        self.load_data_from_db()

        week_label = self.current_week_number
        if (SaveManager.load_settings()["use_lettered_weeks"]):
            week_label = chr(week_label + 64)

        # Update the week label
        self.week_label.config(text=f"Week {week_label} Starting {self.current_week_date.strftime('%Y-%m-%d')}")

        # Clear the timetable frame
        for widget in self.timetable_frame.winfo_children():
            widget.destroy()

        # Setup timetable headers
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        periods = ["1", "2", "3", "4", "5", "After School"]

        # Table headers (periods along the top)
        for col, period in enumerate(["Day"] + periods):
            tk.Label(self.timetable_frame, text=period, borderwidth=1, relief="solid", width=15).grid(row=0, column=col, sticky="nsew")

        holiday_image = Image.open(os.path.join(get_assets_path(), "sleep.png")).resize(size=[15, 15])
        self.holiday_photoimage = ImageTk.PhotoImage(holiday_image) 

        # Days and clickable cells
        for row, day in enumerate(days, start=1):
            day_frame = tk.Frame(self.timetable_frame, borderwidth=1, relief="solid", width=6, height=2)
            day_frame.grid(row=row, column=0, sticky="nsew")

            # Display the name of the day
            tk.Label(day_frame, text=day, font=('Arial italic', 10), fg="#444444").place(relx=0.5, rely=0.5, anchor="center")

            # Provide a button to toggle the holiday status of the day
            this_date = self.get_date_for_day(day, self.current_week_date)

            # Make the button green if it's a holiday already
            button_color = "lightgreen" if self.is_holiday(this_date) else "SystemButtonFace"
            tk.Button(day_frame, image=self.holiday_photoimage, bg=button_color, command=lambda this_date=this_date: self.toggle_date_holiday(this_date)).place(relx=0.05, rely=0.05, anchor="nw")

            for col, period in enumerate(periods, start=1):
                task_label = tk.Label(self.timetable_frame, borderwidth=1, relief="solid", width=15, height=5)
                task_label.grid(row=row, column=col)
                task_label.bind("<Button-1>", lambda event, period=period, day=day: self.open_period_options(period, day))
                self.load_timetable_entry(task_label, day, period)

    def load_data_from_db(self):
        # Clear current subjects and tasks
        self.subjects.clear()
        self.tasks.clear()

        # Connect to the database and load subjects and tasks for the current week
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        # Load subjects for the current week type
        subjects = self.get_subjects_for_week(self.current_week_date)

        for day, period, subject in subjects:
            self.subjects[(self.current_week_number, day, period)] = subject
       
        # Load tasks that are date-specific
        c.execute("SELECT id, task, date, period, completed FROM Tasks")
        tasks = c.fetchall()

        for task_id, task, date_str, period, completed in tasks:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if (date, period) not in self.tasks:
                self.tasks[(date, period)] = []
            self.tasks[(date, period)].append((task_id, task, completed))  # Store task with its completed status

        conn.close()

    def load_timetable_entry(self, task_label, day, period):
        # Get date of current day in week
        date = self.get_date_for_day(day, self.current_week_date)

        # Retrieve subject and tasks for this specific day and period
        subject = self.subjects.get((self.current_week_number, day, period))
        tasks = self.tasks.get((date, period), [])  # date-specific task storage

        # Assume no subjects or tasks
        task_label.config(text="", font=('Arial', 10))

        # Configure text based on subject and tasks
        if subject:
            task_label.config(text=subject)
            if tasks:
                tasks_text = f"{str(len(tasks))} task{"s" if len(tasks) > 1 else ""}"
                task_label.config(text=f"{subject}:\n{tasks_text}")
        elif tasks:
            # Display tasks only if there is no subject
            tasks_text = str(len(tasks)) + " tasks"
            task_label.config(text=tasks_text)

    # --Week Navigation--

    def prev_week(self):
        # Navigate to the previous week
        self.current_week_date -= timedelta(weeks=1)
        self.current_week_number = self.get_week_number_for_date(self.current_week_date)
        self.show_schedule()

    def next_week(self):
        # Navigate to the next week
        self.current_week_date += timedelta(weeks=1)
        self.current_week_number = self.get_week_number_for_date(self.current_week_date)
        self.show_schedule()

    def go_to_current_week(self):
        # Reset to the current week
        self.current_week_date = self.start_date + timedelta(weeks=(self.today_date - self.start_date).days // 7)
        self.current_week_number = self.get_week_number_for_date(self.today_date)
        self.show_schedule()

    # --Period Options--

    def open_period_options(self, period, day):
        options_window = tk.Toplevel(self.root, padx=10, pady=10)
        options_window.title(f"Options for {day} Period {period}")
        self.show_period_options(period, day, options_window)

    def show_period_options(self, period, day, options_window):
        for widget in options_window.winfo_children():
            widget.destroy()

        date = self.get_date_for_day(day, self.current_week_date)
        tasks = self.tasks.get((date, period), [])

        subject_frame = tk.Frame(options_window)
        subject_frame.pack(anchor="w")

        # Show the subject
        subject_label = tk.Label(subject_frame, text="Subject:", pady=10)
        subject_label.grid(row=0, column=0)

        subject = self.subjects.get((self.current_week_number, day, period))
        subject_text = tk.Label(subject_frame, text=subject if subject else "Free")
        subject_text.grid(row=0, column=1, sticky="w")

        # Buttons for subject management
        if subject:
            tk.Button(subject_frame, text="Remove Subject", command=lambda: self.remove_subject(period, day, options_window)).grid(row=0, column=2)
        else:
            tk.Button(subject_frame, text="Set Subject", command=lambda: self.set_subject(period, day, options_window)).grid(row=0, column=2)

        separatora = ttk.Separator(options_window, orient="horizontal")
        separatora.pack(fill="x", pady=5)

        tasks_frame = tk.Frame(options_window)
        tasks_frame.pack(pady=10, anchor="w")

        if tasks:
            # Show task headers
            tasks_label = tk.Label(tasks_frame, text="Tasks:")
            tasks_label.grid(row=2, column=0, sticky="w")

            complete_label = tk.Label(tasks_frame, text="Complete:")
            complete_label.grid(row=2, column=2, sticky="w")

            # Show tasks
            for i, (task_id, task, completed) in enumerate(tasks):
                number_label = tk.Label(tasks_frame, text=str(i + 1))
                number_label.grid(row=3+i, column=0)

                task_frame = tk.Frame(tasks_frame)
                task_frame.grid(row=3+i, column=1)

                task_label = tk.Label(tasks_frame, text=task, anchor="w", justify="left")
                task_label.grid(row=3+i, column=1, sticky="w")

                # Add checkbox to mark task as completed
                completed_var = tk.BooleanVar(value=completed)
                complete_checkbox = tk.Checkbutton(tasks_frame, variable=completed_var, command=lambda tid=task_id, var=completed_var: self.toggle_task_completion(tid, var))
                complete_checkbox.grid(row=3+i, column=2)

                # Add a reschedule button for each task
                tk.Button(tasks_frame, text=f"Reschedule", command=lambda tid=task_id: self.reschedule_task(tid, period, day, options_window)).grid(row=3 + i, column=3)

                # Add a rename button for each task
                tk.Button(tasks_frame, text=f"Rename", command=lambda tid=task_id: self.rename_task(tid, period, day, options_window)).grid(row=3 + i, column=4)

                # Add a remove button for each task
                tk.Button(tasks_frame, text=f"Remove", command=lambda tid=task_id: self.remove_task(tid, period, day, options_window)).grid(row=3 + i, column=5)
        else:
            no_label = tk.Label(tasks_frame, text = "No tasks")
            no_label.grid(row=2, column=0, sticky="w")

        # Buttons for task management
        tasks_management_frame = tk.Frame(options_window)
        tasks_management_frame.pack(anchor="w")

        tk.Button(tasks_management_frame, text="Add Task", command=lambda: self.add_task(period, day, options_window)).grid(row=0, column=0)
        if tasks:
            tk.Button(tasks_management_frame, text="Clear Tasks", command=lambda: self.clear_tasks(period, day, options_window)).grid(row=0, column=1)

    # --Holiday Management--
    def is_holiday(self, date):
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM Holidays WHERE date=?", (date.strftime("%Y-%m-%d"),))
        result = c.fetchone()
        conn.close()
        return result

    def toggle_date_holiday(self, date):
        if self.is_holiday(date):
            self.remove_date_from_holidays(date)
        else:
            self.add_date_to_holidays(date)

    def add_date_to_holidays(self, date):
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO Holidays (date) VALUES (?)", (date.strftime("%Y-%m-%d"),))
        conn.commit()
        conn.close()
        self.show_schedule()

    def remove_date_from_holidays(self, date):
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM Holidays WHERE date=?", (date.strftime("%Y-%m-%d"),))
        conn.commit()
        conn.close()
        self.show_schedule()

    # --Subject Management--

    def set_subject(self, period, day, options_window):
        # Set or replace the subject for the selected period
        set_subject_window = tk.Toplevel(self.root)
        set_subject_window.title("Set Subject")

        tk.Label(set_subject_window, text="Subject:").grid(row=0, column=0)
        subject_var = tk.StringVar()
        tk.Entry(set_subject_window, textvariable=subject_var).grid(row=0, column=1)

        def save_subject():
            subject_text = subject_var.get()
            conn = sqlite3.connect(DATABASE_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM Subjects WHERE week=? AND day=? AND period=?", 
                      (self.current_week_number, day, period))
            c.execute("INSERT INTO Subjects (week, day, period, subject) VALUES (?, ?, ?, ?)", 
                      (self.current_week_number, day, period, subject_text))
            conn.commit()
            conn.close()
            self.show_schedule()
            self.show_period_options(period, day, options_window)
            set_subject_window.destroy()

        tk.Button(set_subject_window, text="Save Subject", command=save_subject).grid(row=1, column=0, columnspan=2, pady=5)

    def remove_subject(self, period, day, options_window):
        # Remove the subject from the selected period
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM Subjects WHERE week=? AND day=? AND period=? AND subject IS NOT NULL", 
                  (self.current_week_number, day, period))
        conn.commit()
        conn.close()
        self.show_schedule()
        self.show_period_options(period, day, options_window)

    # --Tasks Management

    def add_task(self, period, day, options_window):
        add_task_window = tk.Toplevel(self.root)
        add_task_window.title("Add Task")

        tk.Label(add_task_window, text="Task:").grid(row=0, column=0)
        task_var = tk.StringVar()
        tk.Entry(add_task_window, textvariable=task_var).grid(row=0, column=1)

        def save_task():
            task_text = task_var.get()
            date_str = self.get_date_for_day(day, self.current_week_date).strftime("%Y-%m-%d")

            # Retrieve subject ID for the specific period and day
            conn = sqlite3.connect(DATABASE_FILE)
            c = conn.cursor()

            # Insert task into the Tasks table with subject_id
            c.execute("INSERT INTO Tasks (task, date, period, completed) VALUES (?, ?, ?, ?)",
                    (task_text, date_str, period, 0))
            conn.commit()

            conn.close()
            self.show_schedule()
            self.show_period_options(period, day, options_window)
            add_task_window.destroy()

        tk.Button(add_task_window, text="Save Task", command=save_task).grid(row=1, column=0, columnspan=2)

    def clear_tasks(self, period, day, options_window):
        # Clear all tasks from the selected period
        date_str = self.get_date_for_day(day, self.current_week_date).strftime("%Y-%m-%d")
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM Tasks WHERE date=? AND period=? AND task IS NOT NULL", 
                  (date_str, period))
        conn.commit()
        conn.close()
        self.show_schedule()
        self.show_period_options(period, day, options_window)

    def remove_task(self, task_id, period, day, options_window):
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM Tasks WHERE id=? AND task IS NOT NULL", [(task_id)])
        conn.commit()
        conn.close()
        self.show_schedule()
        self.show_period_options(period, day, options_window)

    def toggle_task_completion(self, task_id, completed_var):
        new_status = 1 if completed_var.get() else 0
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("UPDATE Tasks SET completed=? WHERE id=?", (new_status, task_id))
        conn.commit()
        conn.close()
        self.show_schedule()

    def reschedule_task(self, task_id, period, day, options_window):
        # Create the rescheduling window
        reschedule_window = tk.Toplevel(self.root)
        reschedule_window.title("Reschedule Task")

        # Date selection using tkcalendar DateEntry
        tk.Label(reschedule_window, text="New Date:").grid(row=0, column=0, padx=5, pady=5)
        date_entry = DateEntry(reschedule_window, width=12, background='darkblue',
                               foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        date_entry.grid(row=0, column=1, padx=5, pady=5)

        # Period selection using a dropdown menu
        tk.Label(reschedule_window, text="New Period:").grid(row=1, column=0, padx=5, pady=5)
        period_options = ["1", "2", "3", "4", "5", "After School"]
        period_var = tk.StringVar(value="1")
        period_dropdown = ttk.Combobox(reschedule_window, textvariable=period_var, values=period_options, state="readonly")
        period_dropdown.grid(row=1, column=1, padx=5, pady=5)

        # Save button to update the task in the database
        def save_reschedule():
            new_date = date_entry.get_date()
            new_period = period_var.get()

            conn = sqlite3.connect(DATABASE_FILE)
            c = conn.cursor()

            # Update the task's date and period in the database
            c.execute("UPDATE Tasks SET date = ?, period = ? WHERE id = ?", (new_date, new_period, task_id))
            conn.commit()
            reschedule_window.destroy()
            self.show_schedule()
            self.show_period_options(period, day, options_window)

        save_button = tk.Button(reschedule_window, text="Save", command=save_reschedule)
        save_button.grid(row=2, column=0, columnspan=2, pady=10)

    def rename_task(self, task_id, period, day, options_window):
        # Create the rescheduling window
        rename_window = tk.Toplevel(self.root)
        rename_window.title("Rename Task")

        # Date selection using tkcalendar DateEntry
        tk.Label(rename_window, text="New Name:").grid(row=0, column=0, padx=5, pady=5)
        name_var = tk.StringVar()
        tk.Entry(rename_window, textvariable=name_var).grid(row=0, column=1, padx=5, pady=5)

        # Save button to update the task in the database
        def save_rename():
            new_name = name_var.get()

            conn = sqlite3.connect(DATABASE_FILE)
            c = conn.cursor()

            # Update the task's date and period in the database
            c.execute("UPDATE Tasks SET task = ? WHERE id = ?", (new_name, task_id))
            conn.commit()
            rename_window.destroy()
            self.show_schedule()
            self.show_period_options(period, day, options_window)

        save_button = tk.Button(rename_window, text="Save", command=save_rename)
        save_button.grid(row=1, column=0, columnspan=2, pady=10)

    # --Auto Rescheduling--

    def auto_reschedule_tasks(self):
        """Automate rescheduling tasks at 3:00 PM and midnight."""

        # Only perform reschedule if auto-rescheduling is enabled
        if SaveManager.load_settings()["auto_reschedule"] == True:
            now = datetime.now()
            self.clear_old_completed_tasks()  # Clear old completed tasks first
            if now.hour >= 16:
                # 3:30 PM rescheduling
                self.reschedule_incomplete_tasks_to_afternoon(datetime.today())
            else:
                # Midnight rescheduling for the next day
                self.reschedule_incomplete_tasks_to_next_day(datetime.today())

            self.show_schedule()

        # Schedule this function to check every minute for trigger times
        self.root.after(60000, self.auto_reschedule_tasks)

    def schedule_auto_rescheduling(self):
        # Start the auto-rescheduling check
        self.auto_reschedule_tasks()

    def clear_old_completed_tasks(self):
        """Remove all completed tasks from the database if they are from a previous week."""
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        cutoff_date = self.today_date - timedelta(days=self.today_date.weekday())  # Start of current week
        c.execute("DELETE FROM Tasks WHERE completed = 1 AND date < ?", (cutoff_date.strftime("%Y-%m-%d"),))
        conn.commit()
        conn.close()

    def reschedule_incomplete_tasks_to_afternoon(self, date):
        """Move incomplete tasks to 'After School' at 3:30 PM and redistribute if necessary."""
        today_date = date.strftime("%Y-%m-%d")

        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        # Get all incomplete tasks for the current day that aren't in "After School"
        c.execute("SELECT id, task FROM Tasks WHERE date = ? AND period != 'After School' AND completed = 0", (today_date,))
        tasks = c.fetchall()
        conn.close()

        # Move tasks to "After School" initially
        for task_id, task in tasks:
            self.reschedule_task_to_afternoon(task_id, date)

    def reschedule_incomplete_tasks_to_next_day(self, date):
        """Move today's incomplete tasks to tomorrow's available periods."""
        today_date = date.strftime("%Y-%m-%d")

        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        # Get all incomplete tasks from yesterday
        c.execute("SELECT id FROM Tasks WHERE date < ? AND completed = 0", (today_date,))
        tasks = c.fetchall()
        conn.close()

        # Attempt to reschedule these tasks to the next day
        for task_id, in tasks:
            self.redistribute_task_to_next_available_period(task_id, date)

    def reschedule_task_to_afternoon(self, task_id, date):
        today_date = date.strftime("%Y-%m-%d")
        tomorrow_date = date + timedelta(days=1)

        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        # Get the maximum number of tasks which can be rescheduled for after school
        max_tasks = SaveManager.load_settings()["max_tasks_afternoon"]

        # If under the limit
        if self.count_tasks_in_period(today_date, 'After School') < max_tasks:
            # Reschedule task to afternoon
            c.execute("UPDATE Tasks SET period = 'After School', date = ? WHERE id = ?", (today_date, task_id,))
            conn.commit()
            conn.close()

        # Else reschedule to next day
        else:
            conn.close()
            self.redistribute_task_to_next_available_period(task_id, tomorrow_date)

    def redistribute_task_to_next_available_period(self, task_id, date):
        """Find the next available period for a task on the target date and reschedule it."""
        today_date = date.strftime("%Y-%m-%d")
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        periods = ["1", "2", "3", "4", "5"]
        week_type = self.get_week_number_for_date(date)
        day = self.get_day_for_date(date)

        max_tasks = SaveManager.load_settings()["max_tasks_lesson"]
        scheduled = False
        for period in periods:
            subject = self.get_subject_for_date_period(date, period)

            if self.count_tasks_in_period(today_date, period) < max_tasks and ((not subject) or subject == "Supp"):

                # Reschedule task
                c.execute("UPDATE Tasks SET date = ?, period = ? WHERE id = ?", (today_date, period, task_id))
                scheduled = True
                conn.commit()
                return

        conn.close()

        if not scheduled:
            self.reschedule_task_to_afternoon(task_id, date)

    # --Settings--

    def open_settings(self):
        settings_window = tk.Toplevel(self.root, padx=15, pady=5)
        settings_window.title(f"Settings")
        settings = SaveManager.load_settings()
        self.show_settings(settings_window, settings)

    def show_settings(self, settings_window, settings):
        for widget in settings_window.winfo_children():
            widget.destroy()

        rechedule_settings_frame = tk.LabelFrame(settings_window, text="Auto-rescheduling", pady=10)
        rechedule_settings_frame.pack()

        # Toggle for auto rescheduling
        auto_reschedule = tk.BooleanVar(value=settings["auto_reschedule"])
        tk.Label(rechedule_settings_frame, text="Auto-reschedule tasks: ").grid(row=0, column=0, sticky="e")
        tk.Checkbutton(rechedule_settings_frame, variable=auto_reschedule).grid(row=0, column=1, sticky="w")

        # Maximum number of tasks in a period before reschedule algorithm moves on
        max_tasks_lesson = tk.IntVar(value=settings["max_tasks_lesson"])
        tk.Label(rechedule_settings_frame, text="Max tasks per lesson: ").grid(row=1, column=0, sticky="e")
        tk.Spinbox(rechedule_settings_frame, from_=0, to_=100, textvariable=max_tasks_lesson, validate="key", validatecommand=(rechedule_settings_frame.register(lambda val: val.isdigit() or val == ""), "%P")).grid(row=1, column=1, sticky="w")

        # Maximum number of tasks after school before reschedule algorithm moves on
        max_tasks_afternoon = tk.IntVar(value=settings["max_tasks_afternoon"])
        tk.Label(rechedule_settings_frame, text="Max tasks after school: ").grid(row=2, column=0, sticky="e")
        tk.Spinbox(rechedule_settings_frame, from_=0, to_=100, textvariable=max_tasks_afternoon, validate="key", validatecommand=(rechedule_settings_frame.register(lambda val: val.isdigit() or val == ""), "%P")).grid(row=2, column=1, sticky="w")

        week_settings_frame = tk.LabelFrame(settings_window, text="Week Rotation", pady=10)
        week_settings_frame.pack()

        # Week rotation length
        week_rotation_length = tk.IntVar(value=settings["week_rotation_length"])
        tk.Label(week_settings_frame, text="Week rotation length: ").grid(row=3, column=0, sticky="e")
        tk.Spinbox(week_settings_frame, from_=1, to_=100, textvariable=week_rotation_length, validate="key", validatecommand=(rechedule_settings_frame.register(lambda val: val.isdigit() or val == ""), "%P")).grid(row=3, column=1, sticky="w")

        # Toggle for using lettered weeks
        use_lettered_weeks = tk.BooleanVar(value=settings["use_lettered_weeks"])
        tk.Label(week_settings_frame, text="Use lettered weeks: ").grid(row=4, column=0, sticky="e")
        tk.Checkbutton(week_settings_frame, variable=use_lettered_weeks).grid(row=4, column=1, sticky="w")

        # Start week selection
        start_week_date = tk.StringVar(value=settings["start_week_date"])
        tk.Label(week_settings_frame, text="Start week: ").grid(row=5, column=0, sticky="e")
        week_selector = DateEntry(week_settings_frame, textvariable=start_week_date, date_pattern="yyyy-mm-dd")
        week_selector.set_date(datetime.strptime(settings["start_week_date"], "%Y-%m-%d"))
        week_selector.grid(row=5, column=1, sticky="w")

        # Save settings to json file
        tk.Button(settings_window, text="Save", command=lambda: save_settings()).pack()

        # Restrict date selection to Mondays only
        def validate_settings():
            selected_start_week_date = datetime.strptime(start_week_date.get(), "%Y-%m-%d")
            monday_date = selected_start_week_date - timedelta(days=selected_start_week_date.weekday())
            start_week_date.set(monday_date.strftime("%Y-%m-%d"))

            if max_tasks_lesson.get() < 1 and max_tasks_afternoon.get() < 1:
                auto_reschedule.set(False)

        def save_settings():
            validate_settings()            

            settings["auto_reschedule"] = auto_reschedule.get()
            settings["max_tasks_lesson"] = max_tasks_lesson.get()
            settings["max_tasks_afternoon"] = max_tasks_afternoon.get()
            settings["week_rotation_length"] = week_rotation_length.get()
            settings["use_lettered_weeks"] = use_lettered_weeks.get()
            settings["start_week_date"] = start_week_date.get()
            SaveManager.update_many_settings(settings)

            settings_window.destroy()
            self.system_setup()

    # --General Functions--

    def get_task_id(self, task_text, date, period):
        """ Helper function to retrieve task_id for a specific task text and date."""
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM Tasks WHERE task=? AND date=? AND period=?",
                (task_text, date.strftime("%Y-%m-%d"), period))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def count_tasks_in_period(self, date, period):
        """Helper function to count tasks in a given period on a specific date."""
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Tasks WHERE date = ? AND period = ?", (date, period))
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_date_for_day(self, day, week_start_date):
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        delta_days = days_of_week.index(day)
        return week_start_date + timedelta(days=delta_days)

    def get_day_for_date(self, date):
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days_of_week[date.weekday()]

    def get_week_number_for_date(self, date):
        weeks_since_start = (date - self.start_date).days // 7
        week_number = (weeks_since_start % self.week_rotation_length) + 1
        return week_number

    def get_unique_subjects(self):
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        # Fetch unique subject names
        c.execute("SELECT DISTINCT subject FROM Subjects")
        unique_subjects = [row[0] for row in c.fetchall()]

        conn.close()
        return unique_subjects

    # Get the subject for a specific date
    def get_subject_for_date_period(self, date, period):
        day = self.get_day_for_date(date)
        week_number = self.get_week_number_for_date(date)
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()

        if self.is_holiday(date):
            return None

        c.execute("SELECT subject FROM Subjects WHERE week=? AND day=? AND period=?", (week_number, day, period))
        subject = c.fetchone()
        conn.close()
        return subject[0] if subject else None

    # Get the subject for a week
    def get_subjects_for_week(self, week_start_date):
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        week_number = self.get_week_number_for_date(week_start_date)

        c.execute("SELECT day, period, subject FROM Subjects WHERE week=?", (week_number,))
        subjects = c.fetchall()

        # Remove subjects with dates in the Holidays table
        holidays = set(row[0] for row in c.execute("SELECT date FROM Holidays").fetchall())

        subjects = [row for row in subjects if self.get_date_for_day(row[0], week_start_date).strftime("%Y-%m-%d") not in holidays]

        conn.close()
        return subjects

# Initialize save data and start app
SaveManager.init_db()
SaveManager.init_settings()

root = tk.Tk()
appicon = tk.PhotoImage(file=os.path.join(get_assets_path(), "icon.png"))
root.iconphoto(False, appicon)

app = RevisionManagerApp(root)
root.mainloop()
