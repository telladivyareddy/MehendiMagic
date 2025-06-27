from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import (
    save_user,
    get_user_by_email,
    save_appointment,
    get_appointments_for_artist,
    get_artist_booking_counts,
    get_all_users,
    get_appointments_for_client,
    appointments_table,
    queries_table,
    users_table,
    get_all_appointments
    
)

from models.sns import send_email_notification,send_booking_confirmation
import uuid
import hashlib
from datetime import datetime
from boto3.dynamodb.conditions import Attr



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

def get_artists_by_filter(location, date):
    response = users_table.scan(
        FilterExpression=Attr('role').eq('artist') & 
                         Attr('location').eq(location) & 
                         Attr('available_dates').contains(date)
    )
    return response.get('Items', [])

@app.route('/client_dashboard', methods=['GET', 'POST'])
def client_dashboard():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))

    client_email = session['user']['email']

    # Fetch client appointments (already done)
    client_appointments = get_appointments_for_client(client_email)

    # Fetch artists based on location/date filter
    location = request.args.get('location')
    date = request.args.get('date')
    artists = get_artists_by_filter(location, date)

    # ✅ Fetch queries for this client
    response = queries_table.scan()
    all_queries = response.get('Items', [])
    client_queries = [q for q in all_queries if q['client_email'] == client_email]

    return render_template('client_dashboard.html',
                           user=session['user'],
                           client_appointments=client_appointments,
                           artists=artists,
                           queries=client_queries)


def get_queries_for_artist(artist_email):
    response = queries_table.scan()
    all_queries = response.get('Items', [])
    artist_queries = [q for q in all_queries if q.get('artist_email') == artist_email]
    return artist_queries

@app.route('/artist_dashboard')
def artist_dashboard():
    if 'user' in session and session['user']['role'] == 'artist':
        artist_email = session['user']['email']
        appointments = get_appointments_for_artist(artist_email)
        queries = get_queries_for_artist(artist_email)  # 👈 Add this

        # Get all clients' data
        from models.db import get_user_by_email
        for appt in appointments:
            client = get_user_by_email(appt['client_email'])
            appt['client_location'] = client.get('location', 'Not Provided')

        return render_template('artist_dashboard.html', user=session['user'], appointments=appointments, queries=queries)
    return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))

    client_email = session['user']['email']  # Logged-in client
    artist_email = request.form['artist_email']  # Selected artist
    date = request.form['date']
    time = request.form['time']

    appointment_id = str(uuid.uuid4())
    status = 'pending'

    # Save appointment
    save_appointment(client_email, artist_email, date, time, status, appointment_id)

    # Optional: send SNS notification
    #send_booking_confirmation(client_email, artist_email, date, time)

    return redirect(url_for('client_dashboard'))


from models.sns import send_booking_confirmation

@app.route('/update_status', methods=['POST'])
def update_status():
    if 'user' in session and session['user']['role'] == 'artist':
        appointment_id = request.form['appointment_id']
        new_status = request.form['new_status']

        # Fetch the appointment details (for email content)
        response = appointments_table.get_item(Key={'appointment_id': appointment_id})
        appointment = response.get('Item', {})

        # Update the status
        appointments_table.update_item(
            Key={'appointment_id': appointment_id},
            UpdateExpression='SET #s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': new_status}
        )

        # ✅ Only send confirmation email if accepted
        if new_status == 'accepted':
            send_booking_confirmation(
                appointment['client_email'],
                appointment['artist_email'],
                appointment['date'],
                appointment['time']
            )

        return redirect(url_for('artist_dashboard'))
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))

    # Get all users
    response = users_table.scan()
    users = response.get('Items', [])

    # Get all appointments
    response = appointments_table.scan()
    appointments = response.get('Items', [])

    # Artist booking stats
    artist_stats = {}
    for appt in appointments:
        if appt['status'] != 'rejected':
            artist = appt['artist_email']
            artist_stats[artist] = artist_stats.get(artist, 0) + 1

    # ✅ Fetch all client queries
    response = queries_table.scan()
    queries = response.get('Items', [])

    return render_template('admin_dashboard.html',
                           users=users,
                           appointments=appointments,
                           artist_stats=artist_stats,
                           queries=queries)



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

@app.route('/reschedule', methods=['POST'])
def reschedule():
    if 'user' not in session or session['user']['role'] != 'artist':
        return redirect(url_for('login'))

    appointment_id = request.form['appointment_id']
    new_date = request.form['new_date']
    new_time = request.form['new_time']

    appointments_table.update_item(
        Key={'appointment_id': appointment_id},
        UpdateExpression='SET #d = :date, #t = :time',
        ExpressionAttributeNames={'#d': 'date', '#t': 'time'},
        ExpressionAttributeValues={':date': new_date, ':time': new_time}
    )
    return redirect(url_for('artist_dashboard'))

@app.route('/update_availability', methods=['POST'])
def update_availability():
    if 'user' not in session or session['user']['role'] != 'artist':
        return redirect(url_for('login'))

    artist_email = session['user']['email']
    raw_dates = request.form['available_dates']
    dates = [d.strip() for d in raw_dates.split(',') if d.strip()]

    users_table.update_item(
        Key={'email': artist_email},
        UpdateExpression='SET available_dates = :dates',
        ExpressionAttributeValues={':dates': dates}
    )

    # Refresh session with updated data (optional)
    updated_user = get_user_by_email(artist_email)
    session['user'] = updated_user

    return redirect(url_for('artist_dashboard'))

@app.route('/ask_query', methods=['POST'])
def ask_query():
    if 'user' not in session or session['user']['role'] != 'client':
        return redirect(url_for('login'))

    artist_email = request.form.get('artist_email')
    message = request.form.get('message')

    print("🎯 artist_email:", artist_email)
    print("💬 message:", message)

    if not artist_email or not message:
        return "⚠️ Missing artist_email or message", 400

    query_id = str(uuid.uuid4())
    client_email = session['user']['email']
    timestamp = datetime.now().isoformat()

    queries_table.put_item(Item={
        'query_id': query_id,
        'client_email': client_email,
        'artist_email': artist_email,
        'message': message,
        'reply': '',
        'timestamp': timestamp
    })

    return redirect(url_for('client_dashboard'))



@app.route('/reply_query', methods=['POST'])
def reply_query():
    if 'user' not in session or session['user']['role'] != 'artist':
        return redirect(url_for('login'))

    query_id = request.form['query_id']
    reply = request.form['reply']

    queries_table.update_item(
        Key={'query_id': query_id},
        UpdateExpression='SET reply = :reply',
        ExpressionAttributeValues={':reply': reply}
    )
    return redirect(url_for('artist_dashboard'))



if __name__ == '__main__':
    app.run(debug=True)
