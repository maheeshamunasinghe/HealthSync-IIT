import boto3
from botocore.exceptions import ClientError
import random
from flask import Flask, request, jsonify
import os
from datetime import datetime

# Initialize the Flask app
app = Flask(__name__)

# DynamoDB Client
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
appointments_table = dynamodb.Table('appointments')  # Table Name in DynamoDB

# Add Appointment (with new ID format)
@app.route('/appointments/add', methods=['POST'])
def add_appointment():
    data = request.json

    # Extract the data from the request
    patient_id = data['patient_id']
    doctor_id = data['doctor_id']
    appointment_date = data['appointment_date']  # Expected format: 'YYYY-MM-DD'
    appointment_time = data['appointment_time']
    reason = data['reason']
    status = data['status']
    
    # Extract year, month, and day from appointment date
    appointment_date_obj = datetime.strptime(appointment_date, "%Y-%m-%d")
    year = appointment_date_obj.year
    month = appointment_date_obj.month
    day = appointment_date_obj.day
    
    # Generate appointment_id by concatenating year, month, day, patient_id, doctor_id, and a random digit
    appointment_id = f"{year}{month:02d}{day:02d}{patient_id}{doctor_id}{random.randint(0, 9)}"
    
    # Create the appointment item to be inserted into DynamoDB
    appointment_item = {
        'appointment_id': appointment_id,
        'patient_id': patient_id,
        'doctor_id': doctor_id,
        'appointment_date': appointment_date,
        'appointment_time': appointment_time,
        'reason': reason,
        'appointment_status': status
    }
    
    try:
        # Insert the appointment into DynamoDB
        response = appointments_table.put_item(Item=appointment_item)
        return jsonify({'appointment_id': appointment_id}), 201
    except ClientError as e:
        return jsonify({'error': str(e)}), 500

# View Appointment
@app.route('/appointments/view/<appointment_id>', methods=['GET'])
def view_appointment(appointment_id):
    try:
        response = appointments_table.get_item(Key={'appointment_id': appointment_id})
        if 'Item' in response:
            return jsonify(response['Item']), 200
        else:
            return jsonify({'error': 'Appointment not found'}), 404
    except ClientError as e:
        return jsonify({'error': str(e)}), 500

# Update Appointment
@app.route('/appointments/update/<appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    data = request.json
    try:
        # Update the appointment details in DynamoDB
        update_expression = "SET appointment_date = :date, appointment_time = :time, reason = :reason, appointment_status = :appointment_status"
        expression_values = {
            ":date": data['appointment_date'],
            ":time": data['appointment_time'],
            ":reason": data['reason'],
            ":appointment_status": data['status']
        }

        appointments_table.update_item(
            Key={'appointment_id': appointment_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        return jsonify({'message': 'Appointment updated successfully'}), 200
    except ClientError as e:
        return jsonify({'error': str(e)}), 500

# Delete Appointment
@app.route('/appointments/delete/<appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    try:
        appointments_table.delete_item(Key={'appointment_id': appointment_id})
        return jsonify({'message': 'Appointment deleted successfully'}), 200
    except ClientError as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
