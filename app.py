from flask import Flask, render_template
import sqlite3
from datetime import datetime, timedelta
import pytz
import os
from pytz import timezone

app = Flask(__name__)
DATABASE = 'tally.db'
TIMEZONE = 'America/New_York'
IMAGE_DIR = os.path.join('static', 'assets', 'images')  # Adjust based on your structure

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
        'Diapers': ['Pee Harper','Poo Harper', 'Pee Sophie', 'Poo Sophie']
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

def format_datetime(datetime_str, local_tz='America/New_York'):
    """Format datetime string to a more readable form, converting UTC to local timezone."""
    utc_tz = pytz.utc
    local_timezone = timezone(local_tz)
    utc_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    utc_dt = utc_tz.localize(utc_dt)  # Localize as UTC
    local_dt = utc_dt.astimezone(local_timezone)  # Convert to local timezone
    # Format with the appropriate suffix for the day
    suffix = ["th", "st", "nd", "rd"][(local_dt.day % 10) - 1 if local_dt.day % 10 < 4 and not 11 <= local_dt.day <= 13 else 0]
    formatted_datetime = local_dt.strftime(f"%B {local_dt.day}{suffix}, %Y at %I:%M%p")
    return formatted_datetime

def get_image_files():
    """List all image files in the specified directory."""
    image_files = []
    for filename in os.listdir(IMAGE_DIR):
        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            # Note: Adjust the path based on how you want to reference it in the template
            image_files.append(os.path.join('assets/images', filename))
    return image_files

def get_events_last_3_days():
    conn = get_db_connection()
    events = {'Feeding': [], 'Diapers': []}
    three_days_ago = datetime.now(pytz.timezone(TIMEZONE)) - timedelta(days=3)
    # Assuming these are the correct labels for categorization
    labels = {
        'Feeding': ['Feeding Harper', 'Feeding Sophie'],
        'Diapers': ['Pee Harper','Poo Harper', 'Pee Sophie', 'Poo Sophie']
    }
    for category, label_list in labels.items():
        for label in label_list:
            cur = conn.execute("""
                SELECT key_label, timestamp
                FROM keypresses
                WHERE DATE(timestamp) >= ? AND key_label = ?
                ORDER BY timestamp DESC
            """, (three_days_ago.strftime('%Y-%m-%d'), label))
            fetched_events = cur.fetchall()
            print(f"Events fetched for {label}: {fetched_events}")  # Debugging line
            for row in fetched_events:
                events[category].append({
                    'key_label': row['key_label'],
                    'timestamp': format_datetime(row['timestamp'], TIMEZONE)
                })
    conn.close()
    print(f"Events categorized: {events}")  # Debugging line
    return events

def get_activity_counts_last_7_days():
    conn = get_db_connection()
    cur = conn.cursor()
    seven_days_ago = datetime.now(pytz.timezone(TIMEZONE)) - timedelta(days=6)  # Include today, so go back 6 days
    data = {
        'dates': [],
        'feedings': [],
        'pees': [],
        'poos': [],
    }
    for i in range(7):
        date = seven_days_ago + timedelta(days=i)
        data['dates'].append(date.strftime('%Y-%m-%d'))
        for activity in ['Feeding Harper', 'Feeding Sophie', 'Pee Harper', 'Pee Sophie', 'Poo Harper', 'Poo Sophie']:
            cur.execute("""
                SELECT COUNT(*) FROM keypresses
                WHERE DATE(timestamp) = ? AND key_label = ?
            """, (date.strftime('%Y-%m-%d'), activity))
            count = cur.fetchone()[0]
            if 'Feeding' in activity:
                data['feedings'].append(count)
            elif 'Pee' in activity:
                data['pees'].append(count)
            elif 'Poo' in activity:
                data['poos'].append(count)
    return data

@app.route('/')
def index():
    most_recent_keypress = get_most_recent_keypress()
    simplified_last_update = format_datetime(most_recent_keypress) if most_recent_keypress else "No recent updates"
    last_event_times = get_last_event_times()  # This now contains both 'Feeding' and 'Diapers' categories
    image_files = get_image_files()  # Get list of image files
    events_last_3_days = get_events_last_3_days()  # Fetch events for the last 3 days
    activity_counts_last_7_days = get_activity_counts_last_7_days()

    return render_template('index.html', 
                           key_counts=get_key_counts(), 
                           last_event_times=last_event_times,  # Pass the structured dict as is
                           today_counts=get_today_counts(), 
                           average_counts_per_day=get_average_counts_per_day(),
                           last_updated=simplified_last_update,
                           image_files=image_files,
                           events_last_3_days=events_last_3_days,
                           activity_counts_last_7_days=activity_counts_last_7_days)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
