import boto3
from boto3.dynamodb.conditions import Key
from collections import Counter

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # or your region
users_table = dynamodb.Table('Users')
appointments_table = dynamodb.Table('Appointments')

def save_user(email, name, password, role, location=None, available_dates=None):
    item = {
        'email': email,
        'name': name,
        'password': password,
        'role': role,
    }
    if location:
        item['location'] = location
    if available_dates:
        item['available_dates'] = available_dates.split(',')

    users_table.put_item(Item=item)


def get_user_by_email(email):
    response = users_table.get_item(Key={'email': email})
    return response.get('Item')

def get_appointments_for_artist(artist_email):
    response = appointments_table.scan(
        FilterExpression="artist_email = :email",
        ExpressionAttributeValues={":email": artist_email}
    )
    return response['Items']

def save_appointment(artist_email, client_email, date, time):
    appointment_id = str(uuid.uuid4())
    appointments_table.put_item(
        Item={
            'appointment_id': appointment_id,
            'artist_email': artist_email,
            'client_email': client_email,
            'date': date,
            'time': time,
            'status': 'pending'
        }
    )
    return appointment_id

def get_all_users():
    response = users_table.scan()
    return response['Items']

def get_all_appointments():
    response = appointments_table.scan()
    return response['Items']

 

def get_artist_booking_counts():
    response = appointments_table.scan()
    all_appointments = response['Items']
    artist_emails = [a['artist_email'] for a in all_appointments if 'artist_email' in a]
    return Counter(artist_emails)

def get_appointments_for_client(client_email):
    response = appointments_table.scan(
        FilterExpression='client_email = :email',
        ExpressionAttributeValues={':email': client_email}
    )
    return response['Items']

def get_appointments_for_client(client_email):
    response = appointments_table.scan()
    return [appt for appt in response.get('Items', []) if appt['client_email'] == client_email]
