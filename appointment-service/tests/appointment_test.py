import requests

BASE_URL = "http://localhost:8080"  # Update with your service URL


def test_patient_operations():
    # Step 1: Add a new patient
    data = {
    "appointment_date": "2024-12-09",
    "status": "Scheduled",
    "appointment_time": "19:30",
    "doctor_id": "1",
    "patient_id": "2",
    "reason": "Testing"
}

    response = requests.post(f"{BASE_URL}/appointments/add", json=data)
    assert response.status_code == 201  # Ensure the request was successful

    patient_id = response.json().get("id")
    assert patient_id is not None, "Patient ID should be returned"

    # Step 3: View the patient using the patient_id
    response = requests.get(f"{BASE_URL}/appointments/view/{patient_id}")
    assert response.status_code == 200  # Ensure we get a valid response
    assert response.json().get("reason") == "Testing"  # Ensure the data is correct

    # Step 4: Delete the patient using the patient_id
    response = requests.delete(f"{BASE_URL}/appointments/delete/{patient_id}")
    assert response.status_code == 200  # Ensure the delete was successful

    # Step 5: Ensure the patient is deleted
    response = requests.get(f"{BASE_URL}/appointments/view/{patient_id}")
    assert response.status_code == 404  # The patient should not be found anymore