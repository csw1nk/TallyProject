from flask import Flask, render_template
import sqlite3
from datetime import datetime
import pytz

app = Flask(__name__)
DATABASE = 'tally.db'
TIMEZONE = 'America/New_York'

def get_db_connection():
    """Create a database connection with context management."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    """Query database and return results."""
    with get_db_connection() as conn:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

def get_key_counts():
    """Get counts of each key press from the database."""
    return {row['key_label']: row['count'] for row in query_db("SELECT key_label, COUNT(*) as count FROM keypresses GROUP BY key_label")}

def get_most_recent_keypress():
    """Get the most recent key press timestamp."""
    query = "SELECT MAX(timestamp) FROM keypresses"
    result = query_db(query, one=True)
    return result['MAX(timestamp)'] if result and result['MAX(timestamp)'] else None

def get_last_event_times():
    """Get the last event time for each key press, split by category."""
    categories = {
        'Feeding': ['Feeding Sophie', 'Feeding Harper'],
        'Diapers': ['Pee Harper', 'Poo Sophie', 'Poo Harper', 'Pee Sophie']
    }
    last_events = {'Feeding': {}, 'Diapers': {}}

    with get_db_connection() as conn:
        for category, labels in categories.items():
            for label in labels:
                cur = conn.execute("SELECT key_label, MAX(timestamp) FROM keypresses WHERE key_label = ? GROUP BY key_label", (label,))
                row = cur.fetchone()
                if row:
                    last_events[category][row['key_label']] = format_datetime(row['MAX(timestamp)'])
    
    return last_events

def get_today_counts():
    """Get count of today's key presses."""
    today = datetime.now().strftime('%Y-%m-%d')
    return {row['key_label']: row['COUNT(*)'] for row in query_db("SELECT key_label, COUNT(*) FROM keypresses WHERE DATE(timestamp) = ? GROUP BY key_label", [today])}

def get_average_counts_per_day():
    """Calculate the average count per day for each key press."""
    return {row['key_label']: row['total_count'] / row['days'] for row in query_db("SELECT key_label, COUNT(*) as total_count, COUNT(DISTINCT DATE(timestamp)) as days FROM keypresses GROUP BY key_label") if row['days'] > 0}

def format_datetime(datetime_str, local_tz=TIMEZONE):
    """Format datetime string to a more readable form, converting UTC to local timezone."""
    utc_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
    local_dt = utc_dt.astimezone(pytz.timezone(local_tz))
    suffix = ["th", "st", "nd", "rd"][(local_dt.day % 10) - 1 if local_dt.day % 10 < 4 and not 11 <= local_dt.day <= 13 else 0]
    return local_dt.strftime(f"%B {local_dt.day}{suffix}, %Y at %I:%M%p")

@app.route('/')
def index():
    most_recent_keypress = get_most_recent_keypress()
    simplified_last_update = format_datetime(most_recent_keypress) if most_recent_keypress else "No recent updates"
    last_event_times = get_last_event_times()  # This now contains both 'Feeding' and 'Diapers' categories

    return render_template('index.html', 
                           key_counts=get_key_counts(), 
                           last_event_times=last_event_times,  # Pass the structured dict as is
                           today_counts=get_today_counts(), 
                           average_counts_per_day=get_average_counts_per_day(),
                           last_updated=simplified_last_update)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
