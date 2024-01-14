from flask import Flask, render_template
import sqlite3
from TallyCode import key_counts

app = Flask(__name__)

def get_key_counts():
    conn = sqlite3.connect('tally.db')
    cur = conn.cursor()
    cur.execute("SELECT key_label, COUNT(*) as count FROM keypresses GROUP BY key_label")
    counts = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return counts

@app.route('/')
def index():
    key_counts = get_key_counts()
    return render_template('index.html', key_counts=key_counts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
