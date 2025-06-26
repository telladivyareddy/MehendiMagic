import boto3
import hashlib

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('Users')  # Replace with your actual table name

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin():
    admin = {
        'email': 'admin@mehendi.com',
        'name': 'Admin',
        'role': 'admin',
        'password': hash_password('admin123')  # Use your login logic’s hash function
    }

    users_table.put_item(Item=admin)
    print("✅ Admin user created.")

create_admin()
