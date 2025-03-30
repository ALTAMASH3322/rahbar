from flask import Flask, render_template
from flask_mail import Mail, Message

app = Flask(__name__)

# ✅ Flask-Mail Configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "themajesticesports@gmail.com"  # Change this
app.config["MAIL_PASSWORD"] = "daxhwrbnzrmynyvr"  # Change this
app.config["MAIL_DEFAULT_SENDER"] = "themajesticesports@gmail.com"

mail = Mail(app)

# ✅ Test Email Route
@app.route('/send-test-email')
def send_test_email():
    try:
        msg = Message("Test Email from Flask", 
                      recipients=["altamash3321@gmail.com"])  # Change recipient
        msg.body = "Hello! This is a test email from Flask-Mail."
        mail.send(msg)
        return "✅ Email sent successfully!"
    except Exception as e:
        return f"❌ Error sending email: {e}"

if __name__ == '__main__':
    app.run(debug=True)
