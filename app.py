from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import (
    save_user,
    get_user_by_email,
    save_appointment,
    get_appointments_for_artist,
    get_artist_booking_counts
)

from models.sns import send_email_notification

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
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        existing_user = get_user_by_email(email)
        if existing_user:
            return "User already exists!"

        save_user(name, email, password, role)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = get_user_by_email(email)
        if not user or not check_password_hash(user['password'], password):
            return "Invalid credentials!"

        session['user'] = user
        if user['role'] == 'client':
            return redirect(url_for('client_dashboard'))
        else:
            return redirect(url_for('artist_dashboard'))

    return render_template('login.html')

@app.route('/client_dashboard')
def client_dashboard():
    if 'user' in session and session['user']['role'] == 'client':
        return render_template('client_dashboard.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/artist_dashboard')
def artist_dashboard():
    if 'user' in session and session['user']['role'] == 'artist':
        return render_template('artist_dashboard.html', user=session['user'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/book', methods=['POST'])
def book_appointment():
    if 'user' in session and session['user']['role'] == 'client':
        artist_email = request.form['artist_email']
        date = request.form['date']
        time = request.form['time']
        client_email = session['user']['email']

        appointment_id = save_appointment(artist_email, client_email, date, time)

        client = get_user_by_email(client_email)
        artist = get_user_by_email(artist_email)

        subject = "🎨 MehendiMagic Appointment Booked"
        message = (
            f"✅ New Appointment Confirmed!\n\n"
            f"Client: {client['name']} ({client['email']})\n"
            f"Artist: {artist['name']} ({artist['email']})\n"
            f"Date: {date}\nTime: {time}\n"
            f"Appointment ID: {appointment_id}\n\n"
            f"Thanks,\nMehendiMagic Team"
        )

        send_email_notification(subject, message)

        return f"✅ Appointment booked! Notification sent via SNS email."
    
    return redirect(url_for('login'))

@app.route('/artist_dashboard')
def artist_dashboard():
    if 'user' in session and session['user']['role'] == 'artist':
        appointments = get_appointments_for_artist(session['user']['email'])
        return render_template('artist_dashboard.html', user=session['user'], appointments=appointments)
    return redirect(url_for('login'))

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
        return render_template('admin_dashboard.html', users=users, appointments=appointments)
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


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' in session and session['user']['role'] == 'admin':
        users = get_all_users()
        appointments = get_all_appointments()
        artist_stats = get_artist_booking_counts()
        return render_template('admin_dashboard.html', users=users, appointments=appointments, artist_stats=artist_stats)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
