# decompress.py
import os
import json
import sys
from dotenv import load_dotenv
from pyairtable import Api

# --- CONFIGURATION ---
load_dotenv()
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Initialize clients
airtable_api = Api(AIRTABLE_API_KEY)

# Airtable table objects
applicants_table = airtable_api.table(AIRTABLE_BASE_ID, "Applicants")
personal_details_table = airtable_api.table(AIRTABLE_BASE_ID, "Personal Details")
work_experience_table = airtable_api.table(AIRTABLE_BASE_ID, "Work Experience")
salary_prefs_table = airtable_api.table(AIRTABLE_BASE_ID, "Salary Preferences")

def decompress_json_to_tables(applicant_id_str):
    """
    Reads the Compressed JSON for an applicant and upserts the data
    back into the normalized child tables.
    """
    print(f"Starting decompression for Applicant ID: {applicant_id_str}")
    
    # 1. Fetch the main applicant record and its JSON
    applicant_record = applicants_table.first(formula=f"{{Applicant ID}}={applicant_id_str}")
    if not applicant_record or not applicant_record['fields'].get('Compressed JSON'):
        print("Error: Applicant not found or no JSON data available.")
        return

    compressed_json = applicant_record['fields']['Compressed JSON']
    data = json.loads(compressed_json)
    applicant_link = [applicant_record['id']]

    # 2. Upsert Personal Details (One-to-One)
    personal_data = data.get('personal')
    if personal_data:
        existing_personal = personal_details_table.first(formula=f"{{Applicant ID}}='{applicant_id_str}'")
        personal_data_with_link = {**personal_data, "Applicant ID": applicant_link}
        if existing_personal:
            print("  Updating Personal Details...")
            personal_details_table.update(existing_personal['id'], personal_data_with_link)
        else:
            print("  Creating Personal Details...")
            personal_details_table.create(personal_data_with_link)

    # 3. Upsert Salary Preferences (One-to-One)
    salary_data = data.get('salary')
    if salary_data:
        existing_salary = salary_prefs_table.first(formula=f"{{Applicant ID}}='{applicant_id_str}'")
        salary_data_with_link = {**salary_data, "Applicant ID": applicant_link}
        if existing_salary:
            print("  Updating Salary Preferences...")
            salary_prefs_table.update(existing_salary['id'], salary_data_with_link)
        else:
            print("  Creating Salary Preferences...")
            salary_prefs_table.create(salary_data_with_link)
    
    # 4. Sync Work Experience (One-to-Many)
    experience_data = data.get('experience', [])
    if experience_data:
        existing_experiences = work_experience_table.all(formula=f"{{Applicant ID}}='{applicant_id_str}'")
        if existing_experiences:
            print(f"  Deleting {len(existing_experiences)} old work experience records...")
            work_experience_table.batch_delete([rec['id'] for rec in existing_experiences])
        
        print(f"  Creating {len(experience_data)} new work experience records...")
        records_to_create = [
            {**exp, "Applicant ID": applicant_link} for exp in experience_data
        ]
        work_experience_table.batch_create(records_to_create)

    print("Decompression complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_applicant_id = sys.argv[1]
        decompress_json_to_tables(target_applicant_id)
    else:
        print("Usage: python decompress.py <ApplicantID>")
        print("Example: python decompress.py 1")