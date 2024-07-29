import os
from twilio.rest import Client

def send_sms(message):
    # Twilio credentials
    account_sid = ''
    auth_token = ''
    twilio_number = ''

    client = Client(account_sid, auth_token)
    
    for number in target_numbers:
        client.messages.create(
            body=message,
            from_=twilio_number,
            to=number
        )

if __name__ == "__main__":
    ip_address = os.popen('hostname -I').read().strip()
    message = f'Raspberry Pi Robot IP Address: {ip_address}'
    target_numbers = ['+4528564640', '+4528302988']
    send_sms(message, target_numbers)
