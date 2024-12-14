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
# Add a new doctor
@app.route('/doctors/add', methods=['POST'])
def add_doctor():
    data = request.json
    name = data['name']
    doctor_id = data['doctor_id']
    specialty = data['specialty']
    contact_info = data['contact_info']
    experience = data['experience']

    try:
        cursor.execute(
            """
            INSERT INTO doctors (name, doctor_id, specialty, contact_info, experience)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
            """,
            (name, doctor_id, specialty, contact_info, experience)
        )
        doctor_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({'id': doctor_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500


# View a patient
# View doctor details
@app.route('/doctors/view/<int:doctor_id>', methods=['GET'])
def view_doctor(doctor_id):
    if not doctor_id:
        return jsonify({'error': 'doctor_id is required'}), 400
    
    try:
        cursor.execute(
            "SELECT * FROM doctors WHERE id = %s",
            (doctor_id,)
        )
        doctor = cursor.fetchone()
        if doctor:
            return jsonify({
                'id': doctor[0],
                'name': doctor[1],
                'doctor_id': doctor[2],
                'specialty': doctor[3],
                'contact_info': doctor[4],
                'experience': doctor[5]
            }), 200
        else:
            return jsonify({'error': 'Doctor not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Partial update of a patient's details using PATCH
# Partial update of a doctor's details using PATCH
@app.route('/doctors/update/<string:doctor_id>', methods=['PATCH'])
def patch_doctor(doctor_id):
    data = request.json  # Receive data in JSON format
    update_fields = []

    # Build a dynamic update query based on the fields provided in the request body
    set_clause = []
    values = []

    if 'name' in data:
        set_clause.append("name = %s")
        values.append(data['name'])
    if 'specialty' in data:
        set_clause.append("specialty = %s")
        values.append(data['specialty'])
    if 'contact_info' in data:
        set_clause.append("contact_info = %s")
        values.append(data['contact_info'])
    if 'experience' in data:
        set_clause.append("experience = %s")
        values.append(data['experience'])

    if not set_clause:
        return jsonify({'error': 'No fields to update'}), 400

    # Create the query string
    query = f"""
        UPDATE doctors
        SET {', '.join(set_clause)}
        WHERE id = %s
    """

    try:
        values.append(doctor_id)
        cursor.execute(query, tuple(values))
        conn.commit()

        # Check if the doctor was updated
        if cursor.rowcount == 0:
            return jsonify({'error': 'Doctor not found'}), 404
        return jsonify({'message': 'Doctor updated successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

# Delete a patient
# Delete a patient by ID
# Delete a doctor
@app.route('/doctors/delete/<string:doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    try:
        cursor.execute(
            "DELETE FROM doctors WHERE id = %s",
            (doctor_id,)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': 'Doctor not found'}), 404
        return jsonify({'message': 'Doctor deleted successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
