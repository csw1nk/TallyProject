from flask import Flask, render_template, jsonify
from flask import request
import sqlite3
from datetime import datetime, timedelta
import pytz
import os
from pytz import timezone
import json
import logging

app = Flask(__name__)
DATABASE = 'tally.db'
TIMEZONE = 'America/New_York'
IMAGE_DIR = os.path.join('static', 'assets', 'hospital_images')  # Adjust based on your structure

logging.basicConfig(level=logging.DEBUG)

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
    try:
        utc_tz = pytz.utc
        local_timezone = timezone(local_tz)
        utc_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        utc_dt = utc_tz.localize(utc_dt)  # Localize as UTC
        local_dt = utc_dt.astimezone(local_timezone)  # Convert to local timezone
        # Format with the appropriate suffix for the day
        suffix = ["th", "st", "nd", "rd"][(local_dt.day % 10) - 1 if local_dt.day % 10 < 4 and not 11 <= local_dt.day <= 13 else 0]
        formatted_datetime = local_dt.strftime(f"%B {local_dt.day}{suffix}, %Y at %I:%M%p")
        return formatted_datetime
    except ValueError as e:
        # Handle invalid datetime strings gracefully
        return f"Invalid datetime: {datetime_str}"

def fetch_and_format_last_updated():
    """Fetch the most recent update timestamp from the database and format it for display."""
    query = "SELECT MAX(timestamp) as last_updated FROM keypresses"
    with get_db_connection() as conn:
        cur = conn.execute(query)
        result = cur.fetchone()
        if result and result['last_updated']:
            try:
                # Assuming your database stores timestamps in the same timezone as your application's setting (e.g., America/New_York)
                local_tz = timezone(TIMEZONE)
                # Parse the timestamp without assuming it's in UTC
                local_dt = datetime.strptime(result['last_updated'], "%Y-%m-%d %H:%M:%S")
                local_dt = local_tz.localize(local_dt)  # Make it timezone-aware
                # Format the datetime object
                formatted_datetime = local_dt.strftime("%B %d, %Y at %I:%M%p")
                return formatted_datetime
            except ValueError as e:
                logging.error(f"Error formatting datetime: {e} - Data: {result['last_updated']}")
                return "Invalid datetime format"
        else:
            return "No recent updates"

def get_image_files():
    """List all image files in the specified directory."""
    image_files = []
    for filename in os.listdir(IMAGE_DIR):
        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            # Note: Adjust the path based on how you want to reference it in the template
            image_files.append(os.path.join('assets/hospital_images', filename))
    return image_files

def get_events_last_3_days():
    conn = get_db_connection()
    events = {'Feeding': {}, 'Diapers': {}}
    three_days_ago = datetime.now(pytz.timezone(TIMEZONE)) - timedelta(days=3)
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
            if category not in events:
                events[category] = {}
            events[category][label] = [{
                'key_label': row['key_label'],
                'timestamp': format_datetime(row['timestamp'], TIMEZONE)
            } for row in fetched_events]
    conn.close()
    return events

def get_activities_last_X_days_for_twin(twin_name):
    """
    Fetch activity counts for the specified twin for the last 4 days.
    Activities include feeding, pees, and poos.
    """
    # Assuming `twin_name` could be part of the `key_label` like 'Feeding Harper'
    end_date = datetime.now(pytz.timezone(TIMEZONE))
    start_date = end_date - timedelta(days=6)  # Last 4 days including today
    activities = ['Feeding', 'Pee', 'Poo']
    data = {activity: [] for activity in activities}
    dates = [(start_date + timedelta(days=d)).strftime('%Y-%m-%d') for d in range(7)]
    
    with get_db_connection() as conn:
        for activity in activities:
            for date in dates:
                cur = conn.execute(f"""
                    SELECT COUNT(*) as count
                    FROM keypresses
                    WHERE key_label = ? AND DATE(timestamp) = ?
                """, (f'{activity} {twin_name}', date))
                count = cur.fetchone()[0]
                data[activity].append(count)
    
    return {'dates': dates, 'data': data}

@app.route('/add_note', methods=['POST'])
def add_note():
    note_text = request.form['noteText']
    # Optionally, capture other form data like date or specific IDs related to the note
    with get_db_connection() as conn:
        conn.execute('INSERT INTO notes (text) VALUES (?)', (note_text,))
        conn.commit()
    return 'Note added successfully!'  # Or redirect to another page with redirect(url_for('index'))

@app.route('/')
def index():    
    # Fetch event times and image files
    last_event_times = get_last_event_times()
    image_files = get_image_files()
    last_updated = fetch_and_format_last_updated()
    
    # Fetch events for the last 3 days
    events_last_3_days = get_events_last_3_days()
    
    # Fetch activity data for Harper and Sophie
    harper_data = get_activities_last_X_days_for_twin('Harper')
    sophie_data = get_activities_last_X_days_for_twin('Sophie')
    
    # Convert the twin data to JSON for the JavaScript charts
    harper_data_json = json.dumps(harper_data)
    sophie_data_json = json.dumps(sophie_data)

    with get_db_connection() as conn:
        notes = conn.execute('SELECT text, created_at FROM notes ORDER BY created_at DESC').fetchall()
    
    return render_template('index.html',
                           notes=notes, 
                           key_counts=get_key_counts(),
                           last_event_times=last_event_times,
                           today_counts=get_today_counts(),
                           average_counts_per_day=get_average_counts_per_day(),
                           last_updated=last_updated,
                           image_files=image_files,
                           events_last_3_days=events_last_3_days,
                           harper_data_json=harper_data_json, 
                           sophie_data_json=sophie_data_json)

@app.route('/notes')
def notes_page():
    with get_db_connection() as conn:
        notes = conn.execute('SELECT text, created_at FROM notes ORDER BY created_at DESC').fetchall()
    return render_template('notes.html', notes=notes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
