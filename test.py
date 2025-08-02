# File: test_brevo.py
# A simple script to send one test email using the Brevo SMTP credentials in your .env file.

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# --- Step 1: CONFIGURE YOUR TEST DETAILS HERE ---

# IMPORTANT: Change this to one of your client's real sending email addresses
SENDER_EMAIL = "kimberly.parker@50starsstaffing.com" 

# IMPORTANT: Change this to your own personal email address where you want to receive the test
RECIPIENT_EMAIL = "altamash3328@gmail.com" 

# --- END OF CONFIGURATION ---


print("--- Brevo SMTP Test Script ---")

# Load environment variables from the .env file in the current directory
print("1. Loading credentials from .env file...")
load_dotenv()

# Get Brevo credentials from environment variables
SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get('BREVO_SMTP_USER')
SMTP_PASS = os.environ.get('BREVO_SMTP_PASS')

if not SMTP_USER or not SMTP_PASS:
    print("\nERROR: BREVO_SMTP_USER or BREVO_SMTP_PASS not found in .env file.")
    print("Please make sure your .env file is correct.")
    exit()

print("   Credentials loaded successfully.")

# Create the email message
message = MIMEMultipart("alternative")
message["Subject"] = "Brevo SMTP Test from Contabo Server"
message["From"] = SENDER_EMAIL
message["To"] = RECIPIENT_EMAIL

text_part = "Hello,\n\nThis is a test email sent from your application server using Brevo's SMTP service.\n\nIf you received this, the connection is working correctly!"
html_part = "<html><body><p>Hello,</p><p>This is a test email sent from your application server using <b>Brevo's SMTP service</b>.</p><p>If you received this, the connection is working correctly!</p></body></html>"

message.attach(MIMEText(text_part, "plain"))
message.attach(MIMEText(html_part, "html"))

# Send the email
context = ssl.create_default_context()
try:
    print(f"\n2. Connecting to {SMTP_HOST}...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=context)
        print("   Connection secured with STARTTLS.")
        server.login(SMTP_USER, SMTP_PASS)
        print("   Login successful.")
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, message.as_string())
        print(f"   Email sent successfully to {RECIPIENT_EMAIL}!")

    print("\n--- Test Complete: SUCCESS ---")

except Exception as e:
    print(f"\n--- Test Complete: FAILED ---")
    print(f"An error occurred: {e}")