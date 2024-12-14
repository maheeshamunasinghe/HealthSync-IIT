import requests

BASE_URL = "http://localhost:8080"  # Update with your service URL


def test_patient_operations():
    # Step 1: Add a new patient
    data = {
    "name": "Testing",
    "age": 35,
    "gender": "Male",
    "address": "Testing",
    "email": "testing",
    "contact" : "1234567891",
    "medical_history": [
        "Allergies: Testing",
        "Chronic Conditions: Testing"
    ],
    "prescriptions": [
        {
            "medication_name": "Testing",
            "dosage": "Testing",
            "notes": "Testing"
        }
    ],
    "lab_results": [
        {
            "test_name": "Test",
            "result": "Test",
            "date": "2024-12-01"
        }
    ]
}

    response = requests.post(f"{BASE_URL}/patients/add", json=data)
    assert response.status_code == 201  # Ensure the request was successful

    # Step 2: Extract patient_id from the response
    patient_id = response.json().get("id")
    assert patient_id is not None, "Patient ID should be returned"

    # Step 3: View the patient using the patient_id
    response = requests.get(f"{BASE_URL}/patients/view/{patient_id}")
    assert response.status_code == 200  # Ensure we get a valid response
    assert response.json().get("name") == "Testing"  # Ensure the data is correct

    # Step 4: Delete the patient using the patient_id
    response = requests.delete(f"{BASE_URL}/patients/delete/{patient_id}")
    assert response.status_code == 200  # Ensure the delete was successful

    # Step 5: Ensure the patient is deleted
    response = requests.get(f"{BASE_URL}/patients/view/{patient_id}")
    assert response.status_code == 404  # The patient should not be found anymore