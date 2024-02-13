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
