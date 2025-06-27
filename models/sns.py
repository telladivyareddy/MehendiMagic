import boto3

sns = boto3.client('sns', region_name='us-east-1')

TOPIC_ARN = 'arn:aws:sns:us-east-1:861822896073:MehendiMagicNotifications'

def send_email_notification(subject, message):
    try:
        response = sns.publish(
            TopicArn=TOPIC_ARN,
            Subject=subject,
            Message=message
        )
        return response
    except Exception as e:
        print("Error sending SNS email:", e)
        return None

def send_booking_confirmation(client_email, artist_email, date, time):
    message = f"Booking confirmed!\n\nClient: {client_email}\nArtist: {artist_email}\nDate: {date}\nTime: {time}"
    
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:861822896073:MehendiMagicNotifications',  # replace with your ARN
        Message=message,
        Subject="MehendiMagic Booking Confirmation"
    )