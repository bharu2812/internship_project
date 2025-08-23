import csv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

def create_sample_csv(filename="students.csv"):
    fields = ["student name", "student registration number", "university", "semester"]
    rows = [
        ["Alice Smith", "REG123", "ABC University", "5"],
        ["Bob Johnson", "REG456", "XYZ University", "6"],
        ["Carol Lee", "REG789", "LMN University", "7"]
    ]
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fields)
        writer.writerows(rows)
    print(f"Sample CSV created at {filename}")

def fill_forms_from_csv(filename):
    if not os.path.isfile(filename):
        print("CSV file not found.")
        return
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Simulate form filling (replace with actual form/database logic)
            print(f"Filling form for: {row['student name']} | Reg#: {row['student registration number']} | University: {row['university']} | Semester: {row['semester']}")

def extract_emails_from_csv(csv_path: str) -> List[str]:
    emails = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            email = (
                row.get('email') or
                row.get('student email') or
                row.get('Email ID') or
                row.get('Email') or
                row.get('email_id')
            )
            if email:
                emails.append(email)
    return emails

def send_password_setup_email(recipient_email: str, setup_url: str, sender_email: str, sender_password: str):
    import re
    # Basic email validation
    if not recipient_email or not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
        print(f"Invalid email address: {recipient_email}")
        return False
    subject = "Set up your password for Internship Portal"
    body = f"Hello,\n\nPlease set up your password using the following link:\n{setup_url}\n\nRegards,\nPortal Owner"
    from email.message import EmailMessage
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    try:
        import smtplib
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        print(f"Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        return False

def prompt_and_process_csv():
    csv_path = input("Enter the path to your CSV file: ").strip()
    if not os.path.isfile(csv_path):
        print("File not found. Please check the path and try again.")
        return
    selected_fields = [
        "student name",
        "student registration number",
        "university",
        "semester"
    ]
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        print(f"Processing file: {csv_path}\n")
        for row in reader:
            output = {field: row.get(field, None) for field in selected_fields}
            print(output)

if __name__ == "__main__":
    create_sample_csv()  # This creates students.csv
    fill_forms_from_csv("students.csv")  # This reads and simulates filling forms
