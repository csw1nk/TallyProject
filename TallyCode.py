import keyboard
import sqlite3

key_counts = {"6": 0, "3": 0, "5": 0, "2": 0, "4": 0, "1": 0}

def update_db(key_name):
    try:
        conn = sqlite3.connect('tally.db')
        print("Connected to the database successfully.")
        cur = conn.cursor()
        cur.execute("SELECT count FROM keypresses WHERE key_name = ?", (key_name,))
        row = cur.fetchone()
        if row:
            new_count = row[0] + 1
            cur.execute("UPDATE keypresses SET count = ? WHERE key_name = ?", (new_count, key_name))
        else:
            cur.execute("INSERT INTO keypresses (key_name, count) VALUES (?, 1)", (key_name,))
        conn.commit()
        conn.close()
        print(f"Database updated for key: {key_name}")
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def on_key_event(key):
    if key.event_type == 'down':
        print(f"Detected key: {key.name}")
        if key.name in key_counts:
            key_counts[key.name] += 1
            print(f"Key {key.name} pressed. Count: {key_counts[key.name]}")
            update_db(key.name)

def start_keyboard_listener():
    keyboard.hook(on_key_event)
    print("Press CTRL+C to stop.")
    keyboard.wait('esc')
