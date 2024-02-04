from flask import Flask, render_template
import sqlite3
from datetime import datetime
import pytz  # Ensure pytz is installed

app = Flask(__name__)

# It's better to define utility functions like utc_to_local and format_datetime
# where they're used unless timestamp_str is used for demonstration only.
# In that case, it's better to integrate its usage within relevant functions.

def get_db_connection():
    conn = sqlite3.connect('tally.db')
    conn.row_factory = sqlite3.Row  # This allows you to access columns by name
    return conn

def get_key_counts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT key_label, COUNT(*) as count FROM keypresses GROUP BY key_label")
    counts = {row['key_label']: row['count'] for row in cur.fetchall()}
    conn.close()
    return counts

def get_last_event_times():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT key_label, MAX(timestamp)
        FROM keypresses
        GROUP BY key_label
    """)
    last_times = {row['key_label']: row['MAX(timestamp)'] for row in cur.fetchall()}
    conn.close()
    return last_times

def get_last_updated_timestamp():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(timestamp) FROM keypresses")
    last_updated = cur.fetchone()[0]  # Assuming the first column contains the timestamp
    conn.close()
    if last_updated is not None:
        # Convert the timestamp to a more readable format, if needed
        return format_datetime(last_updated, 'America/New_York')
    else:
        return "No data available"

def get_last_update_time():
    conn = get_db_connection()
    cur = conn.cursor()
    # Assuming there's a table `updates_log` with a column `last_updated`
    cur.execute("SELECT last_updated FROM updates_log ORDER BY last_updated DESC LIMIT 1")
    last_update = cur.fetchone()
    conn.close()
    if last_update:
        return last_update['last_updated']
    else:
        # If no updates have been logged, return the current time or a default value
        return datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %H:%M:%S')

def get_today_counts():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT key_label, COUNT(*)
        FROM keypresses
        WHERE DATE(timestamp) = ?
        GROUP BY key_label
    """, (today,))
    today_counts = {row['key_label']: row['COUNT(*)'] for row in cur.fetchall()}
    conn.close()
    return today_counts

def get_average_counts_per_day():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT key_label, COUNT(*) as total_count, COUNT(DISTINCT DATE(timestamp)) as days
        FROM keypresses
        GROUP BY key_label
    """)
    averages = {row['key_label']: row['total_count'] / row['days'] for row in cur.fetchall() if row['days'] > 0}
    conn.close()
    return averages

def format_datetime(datetime_str, local_tz='UTC'):
    utc_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    utc_dt = utc_dt.replace(tzinfo=pytz.utc)
    local_dt = utc_dt.astimezone(pytz.timezone(local_tz))

    # Handle the suffix for the day
    day = local_dt.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]

    return local_dt.strftime(f"%B {day}{suffix}, %Y at %I:%M%p")

@app.route('/')
def index():
    key_counts = get_key_counts()
    last_event_times = {key: format_datetime(value, 'America/New_York') for key, value in get_last_event_times().items()}
    today_counts = get_today_counts()
    average_counts_per_day = get_average_counts_per_day()
    last_updated = get_last_updated_timestamp() 
    
    return render_template('index.html', key_counts=key_counts, last_event_times=last_event_times,
                           today_counts=today_counts, average_counts_per_day=average_counts_per_day,
                           last_updated=last_updated)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

