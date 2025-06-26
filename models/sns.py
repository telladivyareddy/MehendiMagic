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
