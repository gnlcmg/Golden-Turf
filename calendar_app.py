from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import date

app = Flask(__name__)

# Initialize DB
def init_db():
    conn = sqlite3.connect("jobs.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_date TEXT NOT NULL,
            job_status TEXT NOT NULL,
            job_details TEXT NOT NULL,
            job_notes TEXT
        )
    """)
    conn.commit()
    conn.close()

# Get all jobs for calendar
def get_all_jobs():
    conn = sqlite3.connect("jobs.db")
    c = conn.cursor()
    c.execute("SELECT job_id, job_date, job_status, job_details, job_notes FROM jobs")
    rows = c.fetchall()
    conn.close()

    events = []
    for row in rows:
        job_id, job_date, status, details, notes = row

        # Color based on status
        if status == "Scheduled":
            color = "red"
        elif status == "In Progress":
            color = "orange"
        else:
            color = "green"

        events.append({
            "id": job_id,
            "title": details,
            "start": job_date,
            "color": color,
            "extendedProps": {
                "status": status,
                "notes": notes
            }
        })
    return events

@app.route("/")
def index():
    return render_template("calendar.html")

@app.route("/calendar")
def calendar():
    return render_template("calendar.html")

@app.route("/events")
def events():
    return jsonify(get_all_jobs())

@app.route("/update_date", methods=["POST"])
def update_date():
    data = request.get_json()
    job_id = data.get("id")
    new_date = data.get("date")

    conn = sqlite3.connect("jobs.db")
    c = conn.cursor()
    c.execute("UPDATE jobs SET job_date = ? WHERE job_id = ?", (new_date, job_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route("/job_details/<int:job_id>")
def job_details(job_id):
    conn = sqlite3.connect("jobs.db")
    c = conn.cursor()
    c.execute("SELECT job_id, job_date, job_status, job_details, job_notes FROM jobs WHERE job_id = ?", (job_id,))
    job = c.fetchone()
    conn.close()
    return jsonify({
        "job_id": job[0],
        "job_date": job[1],
        "job_status": job[2],
        "job_details": job[3],
        "job_notes": job[4]
    })

if __name__ == "__main__":
    init_db()
    # Example data
    conn = sqlite3.connect("jobs.db")
    c = conn.cursor()
    c.execute("DELETE FROM jobs")  # Clear old data
    c.executemany("INSERT INTO jobs (job_date, job_status, job_details, job_notes) VALUES (?, ?, ?, ?)", [
        ("2025-08-13", "Scheduled", "Client A - Roof Repair", "Bring ladder"),
        ("2025-08-15", "In Progress", "Client B - Painting", "Use eco paint"),
        ("2025-08-20", "Completed", "Client C - Plumbing", "Fixed leak"),
    ])
    conn.commit()
    conn.close()

    app.run(debug=True)
