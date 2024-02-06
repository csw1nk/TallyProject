from flask import Flask, render_template
import sqlite3
from datetime import datetime
from contextlib import closing
import pytz

app = Flask(__name__)
DATABASE = 'tally.db'
TIMEZONE = 'America/New_York'

def query_db(query, args=(), one=False):
    """Simplify database queries using context managers."""
    with closing(sqlite3.connect(DATABASE)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

def get_key_counts():
    """Get counts of each key press from the database."""
    return {row['key_label']: row['count'] for row in query_db("SELECT key_label, COUNT(*) as count FROM keypresses GROUP BY key_label")}

def get_last_event_times():
    """Get the last event time for each key press."""
    return {row['key_label']: row['MAX(timestamp)'] for row in query_db("SELECT key_label, MAX(timestamp) FROM keypresses GROUP BY key_label")}

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
    return render_template('index.html', 
                           key_counts=get_key_counts(), 
                           last_event_times={key: format_datetime(value) for key, value in get_last_event_times().items()},
                           today_counts=get_today_counts(), 
                           average_counts_per_day=get_average_counts_per_day(),
                           last_updated=datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
