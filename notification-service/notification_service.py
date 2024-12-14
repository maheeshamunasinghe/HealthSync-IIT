import boto3
import os
from flask import Flask, jsonify
from datetime import datetime, timedelta
import psycopg2
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


app = Flask(__name__)

# Database connection
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

# AWS SNS client
ses_client = boto3.client('ses',  aws_access_key_id=aws_access_key_id,
                                  aws_secret_access_key=aws_secret_access_key,
                                   region_name='ap-southeast-1'
)
# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
appointments_table = dynamodb.Table('appointments')  # Table Name in DynamoDB

patients_table = 'patients'  # Assuming patient data is in PostgreSQL

def get_patient_email(patient_id):
    """ Fetch patient email from PostgreSQL """
    try:
        # PostgreSQL connection for patient data
        db_connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = db_connection.cursor()
        cursor.execute("SELECT name , email FROM patients WHERE id = %s", (patient_id,))
        patient = cursor.fetchone()
        cursor.close()
        db_connection.close()
        print(patient)
        
        if patient:
            return patient  # Return the email address
        return None
    except Exception as e:
        print(f"Error fetching patient email: {e}")
        return None

def get_doctor(doctor_id):
    """ Fetch patient email from PostgreSQL """
    try:
        # PostgreSQL connection for patient data
        db_connection = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM doctors WHERE id = %s", (doctor_id,))
        doctor = cursor.fetchone()
        cursor.close()
        db_connection.close()
        print(doctor)
        
        if doctor:
            return doctor[0]  # Return the email address
        return None
    except Exception as e:
        print(f"Error fetching patient email: {e}")
        return None


def get_appointments():
    try:
        # Calculate the target date (today + 1 day)
        today = datetime.today().date()
        one_day_later = today + timedelta(days=1)
        test = one_day_later.strftime('%Y-%m-%d')

        # Scan DynamoDB for appointments
        response = appointments_table.scan(
            FilterExpression=Attr('appointment_date').eq(test) & 
                             Attr('appointment_status').eq('Scheduled')
        )
        appointments = response.get('Items', [])
        print(appointments)
        return appointments

    except Exception as e:
        print(f"Error fetching appointments: {str(e)}")
        return []

def send_reminder(patient_name ,patient_email, appointment_date, appointment_time, reason, doctor):
     # Define the email content
    sender = 'tharindu.20232726@iit.ac.lk'
    recipient = patient_email
    subject = 'Appointment Reminder'

    html_body =f"""
Reminder: Upcoming Appointment

Dear {patient_name}

We would like to remind you about your upcoming appointment with {doctor} on {appointment_date} at {appointment_time}

Reason for visit: {reason}
Looking forward to seeing you soon

Best regards
The Healthcare Team
"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient


    msg.attach(MIMEText(html_body, 'plain'))

    try:
        response = ses_client.send_raw_email(
        Source=sender,
        Destinations=[recipient],
        RawMessage={"Data": msg.as_string()}
    )
        return response
        print("Email sent successfully!")
    except ClientError as e:
        print(f"Error sending email: {e}")
        return None


@app.route('/send_reminders', methods=['POST'])
def send_reminders():
    appointments = get_appointments()
    if not appointments:
        return jsonify({"message": "No upcoming appointments for today."}), 200

    for appointment in appointments:
        appointment_id = appointment.get('appointment_id')
        patient_id = appointment.get('patient_id')
        doctor_id = appointment.get('doctor_id')
        appointment_date = appointment.get('appointment_date')
        appointment_time = appointment.get('appointment_time')
        reason = appointment.get('reason')

        # Get the patient's email from the database
        patient_dets = get_patient_email(patient_id)
        patient_name = patient_dets[0]
        patient_email = patient_dets[1]
        doctor = get_doctor(doctor_id)

        if patient_email:
            # Send reminder using SNS
            sns_response = send_reminder(patient_name ,patient_email, appointment_date, appointment_time, reason, doctor)
            if sns_response:
                print(f"Reminder sent to {patient_email} for appointment {appointment_id}.")
                return jsonify({"message": f"Reminder sent to {patient_email} for appointment {appointment_id}."}), 200

            else:
                print(f"Failed to send reminder for appointment {appointment_id}.")
                return jsonify({"message": f"Failed to send reminder for appointment {appointment_id}."}), 200

        else:
            print(f"Patient ID {patient_id} not found in the database.")
            return jsonify({"message": f"Patient ID {patient_id} not found in the database."}), 200


    return jsonify({"message": "Reminders sent for today's appointments."}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
