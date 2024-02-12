import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('tally.db')
cur = conn.cursor()

# Fetch a single timestamp
cur.execute("SELECT timestamp FROM keypresses ORDER BY id DESC LIMIT 1")
row = cur.fetchone()

if row:
    print("Raw timestamp from database:", row[0])
    # Attempt to parse the timestamp
    parsed_timestamp = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
    print("Parsed timestamp:", parsed_timestamp)
else:
    print("No records found.")

# Close the connection
conn.close()
