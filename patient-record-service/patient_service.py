import email
from flask import Flask, request, jsonify
import psycopg2
import os
import json

app = Flask(__name__)

# Database connection
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()
except Exception as e:
    print("Error connecting to the database:", e)

# Add a new patient
@app.route('/patients/add', methods=['POST'])
def add_patient():
    data = request.json

    name = data['name']
    age = data['age']
    gender = data['gender']
    address = data['address']
    email = data['email']
    contact = data['contact']

    try:
        # Insert into patients table
        cursor.execute(
            "INSERT INTO patients (name, age, gender, address , email , contact) VALUES (%s, %s, %s, %s) RETURNING id",
            (name, age, gender, address , email , contact)
        )
        patient_id = cursor.fetchone()[0]

        # Insert medical history
        for history in data.get('medical_history', []):
            cursor.execute(
                "INSERT INTO medical_history (patient_id, description) VALUES (%s, %s)",
                (patient_id, history)
            )

        # Insert prescriptions
        for prescription in data.get('prescriptions', []):
            cursor.execute(
                "INSERT INTO prescriptions (patient_id, medication_name, dosage, notes) VALUES (%s, %s, %s, %s)",
                (patient_id, prescription['medication_name'], prescription['dosage'], prescription['notes'])
            )

        # Insert lab results
        for result in data.get('lab_results', []):
            cursor.execute(
                "INSERT INTO lab_results (patient_id, test_name, result, date) VALUES (%s, %s, %s, %s)",
                (patient_id, result['test_name'], result['result'], result['date'])
            )

        conn.commit()
        return jsonify({'id': patient_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

# View a patient
@app.route('/patients/view/<int:patient_id>', methods=['GET'])
def view_patient(patient_id):
    try:
        # Fetch patient details
        cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            return jsonify({'error': 'Patient not found'}), 404

        # Fetch related data
        cursor.execute("SELECT description FROM medical_history WHERE patient_id = %s", (patient_id,))
        medical_history = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT medication_name, dosage, notes FROM prescriptions WHERE patient_id = %s", (patient_id,))
        prescriptions = [
            {"medication_name": row[0], "dosage": row[1], "notes": row[2]} for row in cursor.fetchall()
        ]

        cursor.execute("SELECT test_name, result, date FROM lab_results WHERE patient_id = %s", (patient_id,))
        lab_results = [
            {"test_name": row[0], "result": row[1], "date": str(row[2])} for row in cursor.fetchall()
        ]

        # Build response
        return jsonify({
            "id": patient[0],
            "name": patient[1],
            "age": patient[2],
            "gender": patient[3],
            "address": patient[4],
            "medical_history": medical_history,
            "prescriptions": prescriptions,
            "lab_results": lab_results
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Partial update of a patient's details using PATCH
@app.route('/patients/update/<int:patient_id>', methods=['PATCH'])
def patch_patient(patient_id):
    data = request.json  # Receive data in JSON format
    update_fields = []

    # Build a dynamic update query based on the fields provided in the request body
    set_clause = []
    values = []
    
    if 'name' in data:
        set_clause.append("name = %s")
        values.append(data['name'])
    if 'age' in data:
        set_clause.append("age = %s")
        values.append(data['age'])
    if 'gender' in data:
        set_clause.append("gender = %s")
        values.append(data['gender'])
    if 'address' in data:
        set_clause.append("address = %s")
        values.append(data['address'])
    if 'email' in data:
        set_clause.append("email = %s")
        values.append(data['email'])
    if 'contact' in data:
        set_clause.append("contact = %s")
        values.append(data['contact'])
    if 'medical_history' in data:
        set_clause.append("medical_history = %s")
        values.append(data['medical_history'])
    if 'prescriptions' in data:
        set_clause.append("prescriptions = %s")
        values.append(data['prescriptions'])
    if 'lab_results' in data:
        set_clause.append("lab_results = %s")
        values.append(data['lab_results'])

    if not set_clause:
        return jsonify({'error': 'No fields to update'}), 400

    # Add the patient ID to the values list
    values.append(patient_id)

    # Create the query string
    query = f"""
        UPDATE patients
        SET {', '.join(set_clause)}
        WHERE id = %s
    """

    try:
        cursor.execute(query, tuple(values))
        conn.commit()

        # Check if the patient was updated
        if cursor.rowcount == 0:
            return jsonify({'error': 'Patient not found'}), 404
        return jsonify({'message': 'Patient updated successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

# Delete a patient
# Delete a patient by ID
@app.route('/patients/delete/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    try:
        # Delete query
        cursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
        conn.commit()

        # Check if the patient was deleted
        if cursor.rowcount == 0:
            return jsonify({'error': 'Patient not found'}), 404
        return jsonify({'message': 'Patient deleted successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
