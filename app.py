from flask import Flask, render_template, jsonify
from flask import request, redirect, url_for, flash
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
IMAGE_DIR = os.path.join(app.root_path, 'static')

logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    """Create a database connection with context management."""
    conn = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
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
    """Calculate the average count per day for each key press, rounded to two decimal places."""
    return {row['key_label']: round(row['total_count'] / row['days'], 2) for row in query_db("SELECT key_label, COUNT(*) as total_count, COUNT(DISTINCT DATE(timestamp)) as days FROM keypresses GROUP BY key_label") if row['days'] > 0}

def format_datetime(datetime_str, local_tz='America/New_York'):
    """Format datetime string to a more readable form, converting UTC to local timezone."""
    try:
        # Ensure the datetime string is valid before attempting to parse and convert it
        if datetime_str is None or datetime_str.lower() == 'timestamp':
            return "No valid datetime provided"

        utc_tz = pytz.utc
        local_timezone = timezone(local_tz)
        # Parse the datetime string
        utc_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        utc_dt = utc_tz.localize(utc_dt)  # Localize as UTC
        local_dt = utc_dt.astimezone(local_timezone)  # Convert to local timezone

        # Format with the appropriate suffix for the day
        day = local_dt.day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = ["st", "nd", "rd"][day % 10 - 1]

        formatted_datetime = local_dt.strftime(f"%B {day}{suffix}, %Y at %I:%M %p")
        return formatted_datetime
    except ValueError as e:
        # Handle invalid datetime strings gracefully
        return f"Invalid datetime: {datetime_str}"

def get_last_record_timestamp():
    """Get the timestamp of the last record from the keypresses table."""
    query = "SELECT timestamp FROM keypresses ORDER BY id DESC LIMIT 1"
    result = query_db(query, one=True)
    return format_datetime(result['timestamp']) if result and result['timestamp'] else "No records found"

def get_image_files():
    """List all image files in the 'hospital_images' directory."""
    image_files = []
    hospital_images_dir = 'assets/hospital_images'  # Assuming 'assets' is inside the 'static' directory
    
    full_path = os.path.join(IMAGE_DIR, hospital_images_dir)
    if os.path.exists(full_path):
        for filename in os.listdir(full_path):
            if filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                image_files.append(os.path.join(hospital_images_dir, filename))
    
    return image_files

def get_events_last_3_days():
    conn = get_db_connection()
    events = {'Feeding': {}, 'Diapers': {}}
    three_days_ago = datetime.now(pytz.timezone(TIMEZONE)) - timedelta(days=1)
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

def get_diaper_count():
    """Calculate the total number of unique diaper changes within a 1-minute window."""
    diaper_changes = 0
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Fetch all relevant events, ordered by timestamp
        cur.execute("""
            SELECT timestamp FROM keypresses
            WHERE key_label IN ('Pee Harper', 'Poo Harper', 'Pee Sophie', 'Poo Sophie')
            ORDER BY timestamp ASC
        """)
        events = cur.fetchall()

        # Placeholder for the last event to compare with
        last_event_time = None

        for event in events:
            event_time = datetime.strptime(event[0], '%Y-%m-%d %H:%M:%S')
            # If this is the first event or more than 1 minute from the last event, count it as a new diaper change
            if last_event_time is None or event_time - last_event_time > timedelta(minutes=1):
                diaper_changes += 1
            last_event_time = event_time

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()

    return diaper_changes

def get_activities_timestamps_for_twin(twin_name, days=7):
    """
    Fetch event timestamps for the specified twin for the last X days.
    Events include feeding, pees, and poos.
    """
    end_date = datetime.now(pytz.timezone(TIMEZONE))
    start_date = end_date - timedelta(days=days)
    activities = ['Feeding', 'Pee', 'Poo']
    data = {activity: [] for activity in activities}

    with get_db_connection() as conn:
        for activity in activities:
            cur = conn.execute(f"""
                SELECT timestamp
                FROM keypresses
                WHERE key_label LIKE ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (f'{activity} {twin_name}%', start_date.strftime('%Y-%m-%d %H:%M:%S'), end_date.strftime('%Y-%m-%d %H:%M:%S')))
            # Keep timestamps in ISO 8601 string format or convert to UNIX timestamp
            timestamps = [row['timestamp'] for row in cur.fetchall()]
            data[activity] = timestamps

    return data

def get_growth_records(twin_name):
    """Fetch and return the growth records for the specified twin."""
    with get_db_connection() as conn:
        cur = conn.execute("""
            SELECT date_recorded, weight_pounds, weight_ounces, height_inches
            FROM growth_records
            WHERE twin_name = ?
            ORDER BY date_recorded DESC
        """, (twin_name,))
        growth_records = cur.fetchall()

    # Assuming growth_records are in a format that needs no modification for 'date_recorded'
    # Simply return the fetched records without formatting the 'date_recorded'
    return growth_records

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
    last_event_times = get_last_event_times()
    image_files = get_image_files()
    last_updated = get_last_record_timestamp()
    diaper_count = get_diaper_count()
    # Fetch events for the last 3 days
    events_last_3_days = get_events_last_3_days() 
    # Fetch activity data for Harper and Sophie
    harper_data = get_activities_last_X_days_for_twin('Harper')
    sophie_data = get_activities_last_X_days_for_twin('Sophie')
    # Convert the twin data to JSON for the JavaScript charts
    harper_data_json = json.dumps(harper_data)
    sophie_data_json = json.dumps(sophie_data)

    harper_activities = get_activities_timestamps_for_twin('Harper', days=7)
    sophie_activities = get_activities_timestamps_for_twin('Sophie', days=7)
    
    # Convert the data to JSON format for JavaScript to use in the Chart.js setup
    harper_activities_json = json.dumps(harper_activities)
    sophie_activities_json = json.dumps(sophie_activities)

    harper_growth_records = get_growth_records('Harper')
    sophie_growth_records = get_growth_records('Sophie')

    with get_db_connection() as conn:
        notes = conn.execute('SELECT text, created_at FROM notes ORDER BY created_at DESC').fetchall()

    return render_template('index.html',
                           notes=notes, 
                           key_counts=get_key_counts(),
                           last_event_times=last_event_times,
                           today_counts=get_today_counts(),
                           average_counts_per_day=get_average_counts_per_day(),
                           image_files=image_files,
                           events_last_3_days=events_last_3_days,
                           harper_data_json=harper_data_json, 
                           sophie_data_json=sophie_data_json,
			   last_updated=last_updated,
                           diaper_count=diaper_count,
			   harper_activities_json=harper_activities_json, 
                           sophie_activities_json=sophie_activities_json,
			   harper_growth_records=harper_growth_records,
                           sophie_growth_records=sophie_growth_records)

@app.route('/notes')
def notes_page():
    with get_db_connection() as conn:
        notes = conn.execute('SELECT text, created_at FROM notes ORDER BY created_at DESC').fetchall()
    return render_template('notes.html', notes=notes)

@app.route('/add_growth_record', methods=['POST'])
def add_growth_record():
    data = request.get_json()  # Parse JSON data from the request body

    twin_name = data['twinName']
    weight_pounds = data['weightPounds']
    weight_ounces = data['weightOunces']
    height_inches = data['heightInches']
    # Assuming the date_recorded is generated within the function and not passed from the client
    date_recorded = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')

    try:
        with get_db_connection() as conn:
            conn.execute("""
                INSERT INTO growth_records (twin_name, date_recorded, weight_pounds, weight_ounces, height_inches)
                VALUES (?, ?, ?, ?, ?)
            """, (twin_name, date_recorded, weight_pounds, weight_ounces, height_inches))
            conn.commit()

        return jsonify({'success': True, 'message': 'Growth record added successfully!', 'dateRecorded': date_recorded})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

