"""Web-Based Event Booking and Ticketing System using Flask and SQLite3."""

import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

# App Configuration
app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'database.db'

def init_db():
    """Initializes the SQLite database and required tables."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cursor = conn.cursor()

        # Create events table
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                date TEXT,
                location TEXT,
                available_tickets INTEGER
            )
            '''
        )

        # Create bookings table
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                name TEXT,
                email TEXT,
                tickets INTEGER,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
            '''
        )

        # Create admin table
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            '''
        )

        # Insert default admin user if not exists
        admin_user = cursor.execute("SELECT * FROM admin WHERE username = ?", ("admin",)).fetchone()
        if not admin_user:
            hashed_pw = generate_password_hash("admin123", method='pbkdf2:sha256')
            cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ("admin", hashed_pw))

        conn.commit()

@app.route('/')
def home():
    """Landing home page."""
    return render_template('home.html')

@app.route('/events')
def index():
    """Displays all upcoming events."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        events = conn.execute("SELECT * FROM events ORDER BY date").fetchall()
    return render_template('index.html', events=events)

@app.route('/event/<int:event_id>', methods=['GET', 'POST'])
def book_event(event_id):
    """Allows a user to book tickets for a selected event."""
    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cursor = conn.cursor()
        event = cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            tickets = int(request.form.get('tickets', '0'))

            if tickets <= 0 or tickets > event[5]:
                flash("Invalid number of tickets.", "danger")
            else:
                cursor.execute(
                    '''
                    INSERT INTO bookings (event_id, name, email, tickets)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (event_id, name, email, tickets)
                )
                cursor.execute(
                    '''
                    UPDATE events
                    SET available_tickets = available_tickets - ?
                    WHERE id = ?
                    ''',
                    (tickets, event_id)
                )
                conn.commit()
                flash("Booking successful!", "success")
                return redirect(url_for('index'))

    return render_template('book.html', event=event)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin dashboard to create and view events."""
    if 'admin_logged_in' not in session:
        flash("You must log in to access the admin area.", "warning")
        return redirect(url_for('login'))

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            date = request.form.get('date')
            location = request.form.get('location')
            tickets = int(request.form.get('available_tickets', '0'))

            cursor.execute(
                '''
                INSERT INTO events (title, description, date, location, available_tickets)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (title, description, date, location, tickets)
            )
            conn.commit()
            flash("Event created successfully!", "success")
            return redirect(url_for('admin'))

        events = cursor.execute("SELECT * FROM events ORDER BY date").fetchall()

    return render_template('admin.html', events=events)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login route."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        with sqlite3.connect(DATABASE, timeout=10) as conn:
            cursor = conn.cursor()
            admin = cursor.execute(
                "SELECT * FROM admin WHERE username = ?", (username,)
            ).fetchone()

            if admin and check_password_hash(admin[2], password):
                session['admin_logged_in'] = True
                session['admin_user'] = username
                flash("Logged in successfully!", "success")
                return redirect(url_for('admin'))

        flash("Invalid username or password", "danger")

    return render_template('login.html')

@app.route('/admin/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    """Allows admin to edit an existing event."""
    if 'admin_logged_in' not in session:
        flash("You must log in to access the admin area.", "warning")
        return redirect(url_for('login'))

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cursor = conn.cursor()

        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            date = request.form.get('date')
            location = request.form.get('location')
            tickets = int(request.form.get('available_tickets', '0'))

            cursor.execute(
                '''
                UPDATE events
                SET title = ?, description = ?, date = ?, location = ?, available_tickets = ?
                WHERE id = ?
                ''',
                (title, description, date, location, tickets, event_id)
            )
            conn.commit()
            flash("Event updated successfully!", "success")
            return redirect(url_for('admin'))

        event = cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    return render_template('edit_event.html', event=event)

@app.route('/admin/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    """Allows admin to delete an event."""
    if 'admin_logged_in' not in session:
        flash("You must log in to access the admin area.", "warning")
        return redirect(url_for('login'))

    with sqlite3.connect(DATABASE, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()

    flash("Event deleted successfully!", "info")
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    """Admin logout route."""
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)