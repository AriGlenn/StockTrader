
import smtplib

class messageClient:
    def __init__(self, sender_email, sender_password, recipient_email):
        # Establish connection with Gmail SMTP server
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_message(self, subject, text):
        try:
            print("Sending message...")
            message = 'Subject: {}\n\n{}'.format(subject, text)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, self.recipient_email, message)
            server.quit()
            print("Message sent")
        except Exception as ex:
            print(f"Message to {self.recipient_email} failed. Error: {ex}")