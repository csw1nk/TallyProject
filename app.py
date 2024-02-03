from flask import Flask, render_template
import sqlite3
from TallyCode import key_counts
from datetime import datetime

timestamp_str = "2024-02-03 22:40:56"
timestamp_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

app = Flask(__name__)

def get_key_counts():
    conn = sqlite3.connect('tally.db')
    cur = conn.cursor()
    cur.execute("SELECT key_label, COUNT(*) as count FROM keypresses GROUP BY key_label")
    counts = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return counts

def get_last_event_times():
    conn = sqlite3.connect('tally.db')
    cur = conn.cursor()
    # Query the latest time for each type of event
    cur.execute("""
        SELECT key_label, MAX(timestamp)
        FROM keypresses
        GROUP BY key_label
    """)
    last_times = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return last_times

def get_today_counts():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('tally.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT key_label, COUNT(*)
        FROM keypresses
        WHERE DATE(timestamp) = ?
        GROUP BY key_label
    """, (today,))
    today_counts = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return today_counts

def get_average_counts_per_day():
    conn = sqlite3.connect('tally.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT key_label, COUNT(*) as total_count, COUNT(DISTINCT DATE(timestamp)) as days
        FROM keypresses
        GROUP BY key_label
    """)
    averages = {}
    for row in cur.fetchall():
        key_label, total_count, days = row
        averages[key_label] = total_count / days if days > 0 else 0
    conn.close()
    return averages

def format_datetime(datetime_obj):
    # Handle the suffix for the day
    day = datetime_obj.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    
    formatted_datetime = datetime_obj.strftime(f"%B {day}{suffix}, %Y at %I:%M%p")
    return formatted_datetime

@app.route('/')
def index():
    key_counts = get_key_counts()
    last_event_times = get_last_event_times()
    formatted_last_times = {key: format_datetime(datetime.strptime(value, "%Y-%m-%d %H:%M:%S")) for key, value in last_event_times.items()}
    today_counts = get_today_counts()
    average_counts_per_day = get_average_counts_per_day()
    last_updated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current time formatted as a string
    return render_template('index.html', key_counts=key_counts, last_event_times=formatted_last_times, 
                           today_counts=today_counts, average_counts_per_day=average_counts_per_day,
                           last_updated=last_updated)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
