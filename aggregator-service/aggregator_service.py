from ast import Return
import boto3
import pandas as pd
from datetime import datetime
import psycopg2
import os

# DynamoDB configuration
DYNAMO_TABLE = "appointments"
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
table = dynamodb.Table(DYNAMO_TABLE)

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_TABLE = os.getenv("POSTGRES_TABLE")
DB_PORT = os.getenv("DB_PORT")

RS_HOST= os.getenv("REDSHIFT_HOST")
RS_PORT=os.getenv("REDSHIFT_PORT")
RS_DBNAME=os.getenv("REDSHIFT_DATABASE")
RS_USER=os.getenv("REDSHIFT_USER")
RS_PASSWORD=os.getenv("REDSHIFT_PASSWORD")

def aggregate_total_appointments():
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    # Fetch all appointments from DynamoDB
    response = table.scan()
    appointments_data = response['Items']
    
    # Aggregate total appointments per doctor
    appointments_df = pd.DataFrame(appointments_data)
    total_appointments_per_doctor = appointments_df.groupby('doctor_id').size().reset_index(name='total_appointments')
    
    # Fetch doctor names from PostgreSQL
    doctor_ids = total_appointments_per_doctor['doctor_id'].tolist()
    doctor_query = f"SELECT id, name FROM doctors WHERE id IN ({','.join(map(str, doctor_ids))})"
    cursor.execute(doctor_query)
    doctors_data = cursor.fetchall()
    doctors_df = pd.DataFrame(doctors_data, columns=['doctor_id', 'doctor_name'])

    appointments_df['doctor_id'] = appointments_df['doctor_id'].astype(int)
    doctors_df['doctor_id'] = doctors_df['doctor_id'].astype(int)
    total_appointments_per_doctor['doctor_id'] = total_appointments_per_doctor['doctor_id'].astype(int)
    
    # Merge with doctor names
    merged_df = total_appointments_per_doctor.merge(doctors_df, on='doctor_id', how='left')
    test = pd.DataFrame(merged_df , columns=['doctor_name', 'total_appointments'])
    
    return test

def aggregate_doctors_per_specialty():
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    doctor_query = "SELECT specialty, COUNT(*) FROM doctors GROUP BY specialty"
    cursor.execute(doctor_query)
    specialty_data = cursor.fetchall()
    
    specialty_df = pd.DataFrame(specialty_data, columns=['specialty', 'doctor_count'])
    
    return specialty_df

def aggregate_appointments_per_month():

    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    # Fetch all appointments from DynamoDB
    response = table.scan()
    appointments_data = response['Items']
    
    # Convert to DataFrame
    appointments_df = pd.DataFrame(appointments_data)
    
    # Convert appointment date to datetime
    appointments_df['appointment_date'] = pd.to_datetime(appointments_df['appointment_date'])
    
    # Extract month-year and doctor name
    appointments_df['month_year'] = appointments_df['appointment_date'].dt.strftime('%B %Y')
    
    # Group by month_year and doctor
    month_appointments = appointments_df.groupby(['month_year', 'doctor_id']).size().reset_index(name='appointment_count')
    
    # Fetch doctor names from PostgreSQL
    doctor_ids = month_appointments['doctor_id'].tolist()
    doctor_query = f"SELECT id, name FROM doctors WHERE id IN ({','.join(map(str, doctor_ids))})"
    cursor.execute(doctor_query)
    doctors_data = cursor.fetchall()
    doctors_df = pd.DataFrame(doctors_data, columns=['doctor_id', 'doctor_name'])

    doctors_df['doctor_id'] = doctors_df['doctor_id'].astype(int)
    month_appointments['doctor_id'] = month_appointments['doctor_id'].astype(int)
    
    # Merge with doctor names
    merged_df = month_appointments.merge(doctors_df, on='doctor_id', how='left')
    
    return merged_df[['month_year', 'doctor_name', 'appointment_count']]

def aggregate_today_appointments():

    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    today = pd.to_datetime('today').strftime('%Y-%m-%d')
    
    # Fetch today's appointments from DynamoDB
    response = table.scan(
        FilterExpression="appointment_date = :today",
        ExpressionAttributeValues={":today": today}
    )
    appointments_data = response['Items']
    
    appointments_df = pd.DataFrame(appointments_data)

    if len(appointments_df) == 0:
        return appointments_df
    
    total_appointments = appointments_df.groupby('doctor_id').size().reset_index(name='total_appointments')
    completed_appointments = appointments_df[appointments_df['appointment_status'] == 'Completed'].groupby('doctor_id').size().reset_index(name='completed_appointments')
    remaining_appointments = appointments_df[appointments_df['appointment_status'] == 'Scheduled'].groupby('doctor_id').size().reset_index(name='remaining_appointments')
    
    # Merge the data
    today_appointments = total_appointments.merge(completed_appointments, on='doctor_id', how='left')\
                                            .merge(remaining_appointments, on='doctor_id', how='left')
    
    # Fetch doctor names from PostgreSQL
    doctor_ids = today_appointments['doctor_id'].tolist()
    doctor_query = f"SELECT id, name FROM doctors WHERE id IN ({','.join(map(str, doctor_ids))})"
    cursor.execute(doctor_query)
    doctors_data = cursor.fetchall()
    doctors_df = pd.DataFrame(doctors_data, columns=['doctor_id', 'doctor_name'])

    doctors_df['doctor_id'] = doctors_df['doctor_id'].astype(int)
    today_appointments['doctor_id'] = today_appointments['doctor_id'].astype(int)
    
    # Merge with doctor names
    merged_df = today_appointments.merge(doctors_df, on='doctor_id', how='left')
    merged_df = merged_df.fillna(0)
    
    return merged_df[['doctor_name', 'total_appointments', 'completed_appointments', 'remaining_appointments']]

def insert_total_appointments_per_doctor(aggregated_df):

    try:
        conn_rs = psycopg2.connect(
            host=RS_HOST,
            port="5439",
            dbname=RS_DBNAME,
            user=RS_USER,
            password=RS_PASSWORD
        )
        cur_rs  = conn_rs.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    # Iterate through the DataFrame and insert/update records in Redshift
    for index, row in aggregated_df.iterrows():
        doctor_name = row['doctor_name']
        total_appointments = row['total_appointments']

        # Step 1: Update existing records
        update_query = """
            UPDATE total_appointments_per_doctor
            SET total_appointments = %s
            WHERE doctor_name = %s;
        """
        cur_rs.execute(update_query, (total_appointments, doctor_name))

        # Step 2: If no records were updated, insert the new record
        insert_query = """
            INSERT INTO total_appointments_per_doctor (doctor_name, total_appointments)
            SELECT %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM total_appointments_per_doctor WHERE doctor_name = %s
            );
        """
        cur_rs.execute(insert_query, (doctor_name, total_appointments, doctor_name))

    # Commit and close the connection
    conn_rs.commit()
    cur_rs.close()
    conn_rs.close()

def insert_appointments_per_month_per_doctor(aggregated_df):

    try:
        conn_rs = psycopg2.connect(
            host= RS_HOST,
            port=RS_PORT,
            dbname=RS_DBNAME,
            user=RS_USER,
            password=RS_PASSWORD
        )

        cur_rs  = conn_rs.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    # Iterate through the DataFrame and insert/update records in Redshift
    for index, row in aggregated_df.iterrows():
        month_year = row['month_year']
        doctor_name = row['doctor_name']
        total_appointments = row['appointment_count']

        # Step 1: Update existing records
        update_query = """
            UPDATE appointments_per_month_per_doctor_formatted
            SET appointment_count  = %s
            WHERE month_year = %s AND doctor_name = %s;
        """
        cur_rs.execute(update_query, (total_appointments, month_year, doctor_name))

        # Step 2: If no records were updated, insert the new record
        insert_query = """
            INSERT INTO appointments_per_month_per_doctor_formatted (month_year, doctor_name, appointment_count )
            SELECT %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM appointments_per_month_per_doctor_formatted 
                WHERE month_year = %s AND doctor_name = %s
            );
        """
        cur_rs.execute(insert_query, (month_year, doctor_name, total_appointments, month_year, doctor_name))

    # Commit and close the connection
    conn_rs.commit()
    cur_rs.close()
    conn_rs.close()

def insert_today_appointments(today_appointments_df):

    try:
        conn_rs = psycopg2.connect(
            host= RS_HOST,
            port=RS_PORT,
            dbname=RS_DBNAME,
            user=RS_USER,
            password=RS_PASSWORD
        )

        cur_rs  = conn_rs.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    if len(today_appointments_df) == 0:
            merge_query = f"""
            BEGIN;

            DELETE * FROM today_appointments;

            INSERT INTO today_appointments (doctor_name, total_appointments , completed_appointments , remaining_appointments)
            VALUES (%s, %s, %s, %s);

            COMMIT;
        """
            cur_rs.execute(merge_query, ("None", 0, 0, 0))
            conn_rs.commit()
            cur_rs.close()
            conn_rs.close()
            return


    # Iterate through the DataFrame and insert/update records in Redshift
    for index, row in today_appointments_df.iterrows():
        doctor_name = row["doctor_name"]
        total = row["total_appointments"]
        completed = row["completed_appointments"]
        remaining = row["remaining_appointments"]

        # Use a Redshift-compatible UPSERT (MERGE) query
        merge_query = f"""
            BEGIN;

            DELETE FROM today_appointments
            WHERE doctor_name = %s;

            INSERT INTO today_appointments (doctor_name, total_appointments , completed_appointments , remaining_appointments)
            VALUES (%s, %s, %s, %s);

            COMMIT;
        """
        cur_rs.execute(merge_query, (doctor_name, doctor_name, total, completed, remaining))

    # Commit and close the connection
    conn_rs.commit()
    cur_rs.close()
    conn_rs.close()

def insert_doctors_per_speciality(doctors_per_speciality_df):
    # Assuming you already have a connection to Redshift
    try:
        conn_rs = psycopg2.connect(
            host= RS_HOST,
            port=RS_PORT,
            dbname=RS_DBNAME,
            user=RS_USER,
            password=RS_PASSWORD
        )

        cur_rs  = conn_rs.cursor()
    except Exception as e:
        print("Error connecting to the database:", e)

    # Iterate through the DataFrame and insert/update records in Redshift
    for index, row in doctors_per_speciality_df.iterrows():
        specialty = row["specialty"]
        doctor_count = row["doctor_count"]

        # Use a Redshift-compatible UPSERT (MERGE) query
        merge_query = f"""
            BEGIN;

            DELETE FROM doctors_per_speciality 
            WHERE specialty = %s;

            INSERT INTO doctors_per_speciality (specialty, doctor_count)
            VALUES (%s, %s);

            COMMIT;
        """
        cur_rs.execute(merge_query, (specialty, specialty, doctor_count))

    # Commit and close the connection
    conn_rs.commit()
    cur_rs.close()
    conn_rs.close()


def main():
    aggregated_df = aggregate_total_appointments()
    insert_total_appointments_per_doctor(aggregated_df)

    aggregated_df = aggregate_appointments_per_month()
    insert_appointments_per_month_per_doctor(aggregated_df)

    today_appointments_df = aggregate_today_appointments()
    insert_today_appointments(today_appointments_df)

    doctors_per_speciality_df = aggregate_doctors_per_specialty()
    insert_doctors_per_speciality(doctors_per_speciality_df)

if __name__ == "__main__":
    main()