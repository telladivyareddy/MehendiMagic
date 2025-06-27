from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import (
    save_user,
    get_user_by_email,
    save_appointment,
    get_appointments_for_artist,
    get_artist_booking_counts,
    get_all_users,
    get_appointments_for_client
)

from models.sns import send_email_notification,send_booking_confirmation
import uuid
import hashlib
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        location = request.form.get('location')
        available_dates = request.form.get('available_dates')

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        save_user(email, name, hashed_password, role, location, available_dates)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        user = get_user_by_email(email)
        if not user or user['password'] != hashed_password:
            return "Invalid credentials!"

        session['user'] = user
        if user['role'] == 'client':
            return redirect(url_for('client_dashboard'))
        elif user['role'] == 'artist':
            return redirect(url_for('artist_dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html')

@app.route('/client_dashboard', methods=['GET'])
def client_dashboard():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))

    location = request.args.get('location')
    date = request.args.get('date')

    all_users = get_all_users()
    artists = [u for u in all_users if u['role'] == 'artist']

    if location:
        artists = [a for a in artists if a.get('location', '').lower() == location.lower()]
    if date:
        artists = [a for a in artists if 'available_dates' in a and date in a['available_dates']]

    client_email = session['user']['email']
    appointments = get_appointments_for_client(client_email)

    return render_template('client_dashboard.html', user=session['user'], artists=artists, client_appointments=appointments)


@app.route('/artist_dashboard')
def artist_dashboard():
    if 'user' in session and session['user']['role'] == 'artist':
        email = session['user']['email']
        appointments = get_appointments_for_artist(artist_email)
        return render_template('artist_dashboard.html', user=session['user'], appointments=appointments)
    return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))

    client_email = session['user']['email']
    artist_email = request.form['artist_email']
    date = request.form['date']
    time = request.form['time']

    # Save appointment using helper function
    save_appointment(client_email, artist_email, date, time)

    # Optional: Send SNS notification
    send_booking_confirmation(client_email, artist_email, date, time)

    return redirect(url_for('client_dashboard'))




@app.route('/update_status', methods=['POST'])
def update_status():
    if 'user' in session and session['user']['role'] == 'artist':
        appointment_id = request.form['appointment_id']
        new_status = request.form['status']

        appointments_table.update_item(
            Key={'appointment_id': appointment_id},
            UpdateExpression='SET #s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': new_status}
        )
        return redirect(url_for('artist_dashboard'))
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' in session and session['user']['role'] == 'admin':
        users = get_all_users()
        appointments = get_all_appointments()
        artist_stats = get_artist_booking_counts()
        return render_template('admin_dashboard.html', users=users, appointments=appointments, artist_stats=artist_stats)
    return redirect(url_for('login'))


@app.route('/admin_add_user', methods=['POST'])
def admin_add_user():
    if 'user' in session and session['user']['role'] == 'admin':
        email = request.form['email']
        name = request.form['name']
        role = request.form['role']
        password = request.form['password']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        save_user(email, name, hashed_password, role)
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/admin_delete_user', methods=['POST'])
def admin_delete_user():
    if 'user' in session and session['user']['role'] == 'admin':
        email = request.form['email']
        users_table.delete_item(Key={'email': email})
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))




if __name__ == '__main__':
    app.run(debug=True)
