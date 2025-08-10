# main.py
import os
import json
import time
from datetime import date, datetime
from dotenv import load_dotenv
import google.generativeai as genai
from pyairtable import Api
from tenacity import retry, stop_after_attempt, wait_exponential

# --- CONFIGURATION ---
load_dotenv()
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Airtable client
airtable_api = Api(AIRTABLE_API_KEY)

# Configure Gemini client
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Airtable table objects
applicants_table = airtable_api.table(AIRTABLE_BASE_ID, "Applicants")
personal_details_table = airtable_api.table(AIRTABLE_BASE_ID, "Personal Details")
work_experience_table = airtable_api.table(AIRTABLE_BASE_ID, "Work Experience")
salary_prefs_table = airtable_api.table(AIRTABLE_BASE_ID, "Salary Preferences")
shortlisted_leads_table = airtable_api.table(AIRTABLE_BASE_ID, "Shortlisted Leads")

TIER_1_COMPANIES = ["google", "meta", "openai", "amazon", "apple", "netflix", "microsoft"]

# --- 1. JSON COMPRESSION ---
def compress_applicant_data(applicant_record):
    """Gathers linked records and compresses them into a single JSON object."""
    applicant_id = applicant_record['fields'].get('Applicant ID')
    print(f"Processing Applicant ID: {applicant_id}...")

    # Fetch linked records
    personal_record = personal_details_table.first(formula=f"{{Applicant ID}}='{applicant_id}'")
    experience_records = work_experience_table.all(formula=f"{{Applicant ID}}='{applicant_id}'")
    salary_record = salary_prefs_table.first(formula=f"{{Applicant ID}}='{applicant_id}'")

    # Build JSON structure
    compressed_data = {
        "personal": personal_record['fields'] if personal_record else {},
        "experience": [exp['fields'] for exp in experience_records],
        "salary": salary_record['fields'] if salary_record else {}
    }

    # Clean up linked fields from the JSON to avoid redundancy
    for key in ["personal", "salary"]:
        if compressed_data.get(key):
            compressed_data[key].pop('Applicant ID', None)
    for exp in compressed_data.get("experience", []):
        exp.pop('Applicant ID', None)

    return json.dumps(compressed_data, indent=2)

# --- 2. LEAD SHORTLISTING ---
def shortlist_applicant(applicant_record, compressed_json):
    """Evaluates an applicant against defined rules and shortlists if they qualify."""
    data = json.loads(compressed_json)
    reasons = []
    
    # Rule 1: Experience
    experience_ok = False
    total_years = 0
    worked_at_tier_1 = False
    for exp in data.get("experience", []):
        if exp.get("Start") and exp.get("End"):
            try:
                start = datetime.strptime(exp["Start"], '%Y-%m-%d').date()
                end = datetime.strptime(exp["End"], '%Y-%m-%d').date()
                total_years += (end - start).days / 365.25
            except (ValueError, TypeError):
                continue # Skip if dates are invalid
        if exp.get("Company", "").lower() in TIER_1_COMPANIES:
            worked_at_tier_1 = True
    
    if total_years >= 4:
        experience_ok = True
        reasons.append(f"Met experience threshold with {total_years:.1f} years.")
    if worked_at_tier_1:
        experience_ok = True
        reasons.append("Has experience at a Tier-1 company.")

    # Rule 2: Compensation
    compensation_ok = False
    salary = data.get("salary", {})
    if salary.get("Preferred Rate", float('inf')) <= 100 and \
       salary.get("Currency") == "USD" and \
       salary.get("Availability (hrs/wk)", 0) >= 20:
        compensation_ok = True
        reasons.append(f"Compensation expectations are within budget (Rate: ${salary.get('Preferred Rate')}/hr, Availability: {salary.get('Availability (hrs/wk)')} hrs/wk).")

    # Rule 3: Location
    location_ok = False
    allowed_locations = ["us", "usa", "united states", "canada", "uk", "united kingdom", "germany", "india"]
    location_str = data.get("personal", {}).get("Location", "").lower()
    if any(loc in location_str for loc in allowed_locations):
        location_ok = True
        reasons.append(f"Located in an approved region: {data.get('personal', {}).get('Location')}.")

    # Final Decision
    if experience_ok and compensation_ok and location_ok:
        print(f"  -> RESULT: Shortlisted.")
        shortlisted_leads_table.create({
            "Applicant": [applicant_record['id']],
            "Score Reason": "\n".join(reasons)
        })
        applicants_table.update(applicant_record['id'], {"Shortlist Status": "Shortlisted"})
    else:
        print(f"  -> RESULT: Not shortlisted.")
        applicants_table.update(applicant_record['id'], {"Shortlist Status": "Not a fit"})


# --- 3. LLM EVALUATION (with Gemini) ---
@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def evaluate_with_llm(applicant_record_id, compressed_json):
    """Sends applicant JSON to Gemini for qualitative review with retry logic."""
    print("  -> Sending to Gemini for evaluation...")

    prompt = f"""
    You are a highly experienced recruiting analyst. Your task is to evaluate a candidate's profile provided in JSON format.
    Analyze the data and provide four specific things in your response:
    1. A concise professional summary of the applicant in 75 words or less.
    2. An overall quality score from 1 to 10, where 10 is outstanding.
    3. A list of any significant data gaps, inconsistencies, or red flags you notice.
    4. A list of up to three insightful follow-up questions to ask the candidate to clarify their profile.

    Here is the applicant's JSON profile:
    {compressed_json}

    Return your response in the following exact format, with each item on a new line:
    Summary: <Your summary text here>
    Score: <A single integer from 1-10>
    Issues: <A comma-separated list of issues, or 'None'>
    Follow-Ups:
    - <Question 1>
    - <Question 2>
    """

    try:
        response = gemini_model.generate_content(prompt)
        content = response.text
        print("  -> Gemini response received.")
        
        # Parse the structured response
        llm_data = {}
        follow_ups_index = content.find("Follow-Ups:")
        
        main_content = content[:follow_ups_index] if follow_ups_index != -1 else content
        follow_ups_content = content[follow_ups_index:] if follow_ups_index != -1 else ""

        for line in main_content.strip().split('\n'):
            if line.startswith("Summary:"):
                llm_data["LLM Summary"] = line.replace("Summary:", "").strip()
            elif line.startswith("Score:"):
                score_text = line.replace("Score:", "").strip()
                if score_text.isdigit():
                    llm_data["LLM Score"] = int(score_text)
                else:
                    llm_data["LLM Score"] = 0
            elif line.startswith("Issues:"):
                # This field is not in our Airtable schema, so we ignore it.
                pass
        
        if follow_ups_content:
            llm_data["LLM Follow-Ups"] = follow_ups_content.replace("Follow-Ups:", "").strip()

        # Update Airtable
        if llm_data:
            applicants_table.update(applicant_record_id, llm_data)

    except Exception as e:
        print(f"  -> An error occurred with the Gemini API call: {e}")
        raise e # Reraise to trigger tenacity's retry mechanism

# --- MAIN EXECUTION ---
def main():
    """Main function to run the entire pipeline."""
    print("Starting applicant processing run...")
    unprocessed_applicants = applicants_table.all(
        formula="OR({Compressed JSON} = '', {Shortlist Status} = 'Not Evaluated')"
    )

    if not unprocessed_applicants:
        print("No new applicants to process.")
        return

    for applicant in unprocessed_applicants:
        try:
            # Step 1: Compress data to JSON
            compressed_json = compress_applicant_data(applicant)
            applicants_table.update(applicant['id'], {"Compressed JSON": compressed_json})
            
            # Step 2: Evaluate for shortlisting
            shortlist_applicant(applicant, compressed_json)

            # Step 3: Send to LLM for enrichment (with budget guardrail)
            if not applicant['fields'].get('LLM Score'):
                 evaluate_with_llm(applicant['id'], compressed_json)
            
            print("-" * 20)
            time.sleep(1) # To respect API rate limits

        except Exception as e:
            print(f"FAILED to process Applicant ID {applicant['fields'].get('Applicant ID')}. Error: {e}")
            continue

    print("Processing run complete.")

if __name__ == "__main__":
    main()