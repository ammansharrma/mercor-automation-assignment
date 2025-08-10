# <a name="_ofm24wun8ybh"></a>**Airtable Contractor Automation with Gemini AI 🤖**
This project is a complete system for automating the collection, processing, and evaluation of contractor applications. It uses Airtable as a database, a local Python script for core logic, and Google's Gemini AI for qualitative analysis and data enrichment.

-----
## <a name="_nmt2cckh83v0"></a>**✨ Features**
- **Data Aggregation**: Automatically gathers applicant data from multiple Airtable tables and compresses it into a single, clean JSON object.
- **Rule-Based Shortlisting**: Evaluates applicants against a customizable set of rules (experience, compensation, location) to automatically identify promising leads.
- **AI-Powered Evaluation**: Leverages Google's Gemini AI to generate a professional summary, assign a quality score, and suggest follow-up questions for each applicant.
- **Data Synchronization**: Includes a utility script to "decompress" JSON data, allowing for easy edits and ensuring data integrity across the normalized tables.
- **Secure & Modular**: Keeps API keys and secrets separate from the codebase using a .env file.
-----
## <a name="_xefqu5x4gpet"></a>**🏛️ System Architecture**
The system operates on a hybrid model to ensure reliability and performance.

- **Airtable (Database & UI)**: Serves as the central database for all applicant data. Its user-friendly interface is used for initial data entry and final review of the processed results.
- **Python Script (Backend Logic)**: A local script acts as the processing engine. It connects to the Airtable API to fetch new records, execute the compression and shortlisting logic, and call the Gemini API.
- **Google Gemini AI (Intelligence Layer)**: Provides advanced analysis by processing the structured JSON data sent by the Python script and returning qualitative insights.
-----
## <a name="_uijvnqp36ojq"></a>**🏁 Getting Started**
Follow these steps to set up and run the project on your local machine.
### <a name="_sgatfczbfe8y"></a>**Prerequisites**
- Python 3.8+
- An Airtable account
- A Google AI Studio API key (for Gemini)
### <a name="_u66e22fysm6"></a>**1. Set Up the Airtable Base**
Before running the script, you must create the database structure in Airtable.

1. Create a new Airtable base.
1. Create the five tables with the exact field names and types as defined below:
   1. **Applicants**: Applicant ID (Autonumber), Compressed JSON (Long Text), Shortlist Status (Single Select), LLM Summary (Long Text), LLM Score (Number), LLM Follow-Ups (Long Text)
   1. **Personal Details**: Full Name (Single Line Text), Email, Location, LinkedIn, Applicant ID (Link to Applicants)
   1. **Work Experience**: Company (Single Line Text), Title, Start (Date), End (Date), Technologies, Applicant ID (Link to Applicants)
   1. **Salary Preferences**: Record Name (Single Line Text), Preferred Rate (Number), Currency, Availability (hrs/wk), Applicant ID (Link to Applicants)
   1. **Shortlisted Leads**: Shortlist ID (Autonumber), Applicant (Link to Applicants), Score Reason (Long Text), Created At (Created Time)
### <a name="_tb0lr8ylcjov"></a>**2. Clone the Repository**
Bash

git clone [https://github.com/your-username/mercor-automation-assignment.git](https://github.com/ammansharrma/mercor-automation-assignment.git)

cd mercor-automation-assignment

### <a name="_8m69qmlmax37"></a>**3. Set Up the Environment**
Create a virtual environment to manage project dependencies.

Bash

\# Create the virtual environment

python -m venv venv

\# Activate it

\# On Windows:

venv\Scripts\activate

\# On macOS/Linux:

source venv/bin/activate

### <a name="_ge3eh5hjcz4f"></a>**4. Install Dependencies**
Install all required libraries from the requirements.txt file.

Bash

pip install -r requirements.txt

### <a name="_q7x7ce8j0m1w"></a>**5. Configure API Keys**
Create a file named .env in the root of the project directory. Add the following variables, replacing the placeholders with your actual credentials.

\# .env

AIRTABLE\_API\_KEY="YOUR\_AIRTABLE\_KEY\_HERE"

AIRTABLE\_BASE\_ID="YOUR\_AIRTABLE\_BASE\_ID\_HERE"

GEMINI\_API\_KEY="YOUR\_GEMINI\_API\_KEY\_HERE"

-----
## <a name="_al6xlyvkrs0"></a>**📖 Usage**
### <a name="_on5i1ediswa9"></a>**Running the Main Automation Pipeline**
To process new applicants, run the main.py script from your terminal. The script will find all applicants marked as "Not Evaluated", compress their data, evaluate them against the shortlisting rules, and send their profile to Gemini for analysis.

Bash

python main.py

### <a name="_mvvpgu1rbb10"></a>**Decompressing JSON for Edits**
If you need to manually edit an applicant's data via the Compressed JSON field, the decompress.py script can synchronize those changes back to the child tables.

Bash

\# Replace '1' with the Applicant ID you want to decompress

python decompress.py 1

-----
## <a name="_1d8nej5boxvf"></a>**📄 License**
This project is licensed under the MIT License.

