import keyboard
import sqlite3

# Mapping of key codes to descriptive labels
key_label_mapping = {
    "6": "Pee Diaper for Baby A",
    "1": "Poo Diaper for Baby A",
    "5": "Pee Diaper for Baby B",
    "2": "Poo Diaper for Baby B",
    "4": "Placeholder 1",
    "3": "Placeholder 2",
    # Add other mappings as needed
}

key_counts = {label: 0 for label in key_label_mapping.values()}

def update_db(key_label):
    try:
        conn = sqlite3.connect('tally.db')
        print("Connected to the database successfully.")
        cur = conn.cursor()
        cur.execute("SELECT count FROM keypresses WHERE key_label = ?", (key_label,))
        row = cur.fetchone()
        if row:
            new_count = row[0] + 1
            cur.execute("UPDATE keypresses SET count = ? WHERE key_label = ?", (new_count, key_label))
        else:
            cur.execute("INSERT INTO keypresses (key_label, count) VALUES (?, 1)", (key_label,))
        conn.commit()
        conn.close()
        print(f"Database updated for key: {key_label}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def on_key_event(event):
    if event.event_type == 'down':
        key_code = event.name
        if key_code in key_label_mapping:
            key_label = key_label_mapping[key_code]
            print(f"Detected key: {key_code}")
            key_counts[key_label] += 1
            print(f"Key {key_code} pressed. Label: {key_label}, Count: {key_counts[key_label]}")
            update_db(key_label)

def start_keyboard_listener():
    keyboard.hook(on_key_event)
    print("Press CTRL+C to stop.")
    keyboard.wait('esc')

if __name__ == "__main__":
    start_keyboard_listener()
