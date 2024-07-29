import os
import socket
from twilio.rest import Client

def get_ip_address():
    # Create a UDP socket (does not need to be connected)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a remote server to determine the local IP address
        s.connect(('8.8.8.8', 80))  # Google's public DNS server, not actually used
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = 'Unable to determine IP address'
    finally:
        s.close()
    return local_ip

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

if __name__ == "__main__":
    ip_address = get_ip_address()
    message = f'Raspberry Pi Robot IP Address: {ip_address}'
    target_numbers = ['+4528564640', '+4528302988']
    send_sms(message, target_numbers)
