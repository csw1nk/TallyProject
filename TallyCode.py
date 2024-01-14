import sqlite3
import time
import keyboard

# Mapping of key codes to descriptive labels
key_label_mapping = {
    "6": "Placeholder 2",
    "1": "Pee Diaper for Harper",
    "5": "Poo Diaper for Halston",
    "2": "Pee Diaper for Halston",
    "4": "Poo Diaper for Harper",
    "3": "Placeholder 1",
    # Add other mappings as needed
}

key_counts = {label: 0 for label in key_label_mapping.values()}
last_key_states = {key: False for key in key_label_mapping.keys()}

def update_db(key_label):
    try:
        conn = sqlite3.connect('tally.db')
        print("Connected to the database successfully.")
        cur = conn.cursor()
        print(f"Key label to insert: {key_label}")  # Adjusted for clarity
        # Insert a new row for each keypress
        cur.execute("INSERT INTO keypresses (key_label) VALUES (?)", (key_label,))
        conn.commit()
        conn.close()
        print(f"New row added for key: {key_label}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def poll_keyboard_events():
    while True:
        for key in key_label_mapping:
            if keyboard.is_pressed(key) and not last_key_states[key]:
                # Key is pressed
                key_label = key_label_mapping[key]
                key_counts[key_label] += 1
                print(f"Key {key} pressed. Label: {key_label}, Count: {key_counts[key_label]}")
                update_db(key_label)
                last_key_states[key] = True
            elif not keyboard.is_pressed(key) and last_key_states[key]:
                last_key_states[key] = False
        time.sleep(0.1)  # Adjust the polling interval as needed

if __name__ == "__main__":
    poll_keyboard_events()
