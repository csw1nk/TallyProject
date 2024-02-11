import sqlite3
import time
import keyboard
import csv
from datetime import datetime

# Mapping of key codes to descriptive labels
key_label_mapping = {
    "6": "Feeding Sophie",
    "1": "Pee Harper",
    "5": "Poo Sophie",
    "2": "Poo Harper",
    "4": "Pee Sophie",
    "3": "Feeding Harper",
}

key_counts = {label: 0 for label in key_label_mapping.values()}
last_key_states = {key: False for key in key_label_mapping.keys()}

# CSV backup file name
CSV_BACKUP = 'tally_backup.csv'

def update_csv_backup(key_label, index):
    """Append the latest key press event to the CSV backup file."""
    with open(CSV_BACKUP, 'a', newline='') as csvfile:
        fieldnames = ['id', 'timestamp', 'key_label']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if the file is newly created
        if csvfile.tell() == 0:
            writer.writeheader()
        
        # Get current UTC time
        utc_now = datetime.now(timezone.utc)
        
        # Write the row with index, timestamp, and key_label
        writer.writerow({'id': index, 'timestamp': utc_now.strftime('%Y-%m-%d %H:%M:%S'), 'key_label': key_label})

def update_db(key_label):
    """Insert the latest key press event into the SQLite database and update the CSV backup."""
    try:
        conn = sqlite3.connect('tally.db')
        cur = conn.cursor()
        cur.execute("INSERT INTO keypresses (key_label) VALUES (?)", (key_label,))
        conn.commit()
        print(f"Key label to insert: {key_label} - New row added for key: {key_label}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()
    
    # Update CSV backup after successful database insert
    update_csv_backup(key_label)
    print(f"CSV Backup Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Key Label: {key_label}")


def poll_keyboard_events():
    """Poll for keyboard events and update the database and CSV backup accordingly."""
    while True:
        for key in key_label_mapping:
            if keyboard.is_pressed(key) and not last_key_states[key]:
                key_label = key_label_mapping[key]
                key_counts[key_label] += 1
                print(f"Key {key} pressed. Label: {key_label}, Count: {key_counts[key_label]}")
                update_db(key_label)
                last_key_states[key] = True
            elif not keyboard.is_pressed(key) and last_key_states[key]:
                last_key_states[key] = False
        time.sleep(0.1)

if __name__ == "__main__":
    poll_keyboard_events()
