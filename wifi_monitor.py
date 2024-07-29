import os
import time
from twilio.rest import Client

def send_sms(message, target_numbers):
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

def is_connected():
    response = os.system("ping -c 1 google.com > /dev/null 2>&1")
    return response == 0

if __name__ == "__main__":
    was_connected = is_connected()
    target_numbers = ['+4528564640', '+4528302988']  # Add your target numbers here

    while True:
        time.sleep(60)  # Check every 60 seconds
        connected = is_connected()

        if was_connected and not connected:
            send_sms("Chicken coop has lost WiFi connection, check that the power supply is up and running.", target_numbers)
        elif not was_connected and connected:
            ip_address = os.popen('hostname -I').read().strip()
            send_sms(f"Chicken coop raspberry Pi has reconnected to WiFi. IP Address: {ip_address}", target_numbers)

        was_connected = connected
