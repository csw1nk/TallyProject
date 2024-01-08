from flask import Flask, render_template
import threading
from TallyCode import start_keyboard_listener, key_counts

app = Flask(__name__)

@app.route('/')
def index():
    print("Request received at /")
    return render_template('index.html', key_counts=key_counts)

def run_keyboard_listener():
    start_keyboard_listener()

if __name__ == '__main__':
    threading.Thread(target=run_keyboard_listener).start()
    print("Starting Flask app...")
    app.run(host='10.0.0.237', port=5000)
