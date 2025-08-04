import os
import datetime
from flask import Flask, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests
import gspread

# --- CONFIGURATION ---

# TODO: PASTE YOUR ANDROID CLIENT ID HERE
# You can find this in your Google Cloud Console -> APIs & Services -> Credentials
# It's the one with the type "Android".
ANDROID_CLIENT_ID = "431652515727-bt80bpas52jp1b6qg6jsmse103q472im.apps.googleusercontent.com"

# The email of the service account you created and shared your sheet with
SERVICE_ACCOUNT_EMAIL = "sheets-editor-for-jobwala99@sublime-vial-467111-q4.iam.gserviceaccount.com"

# The ID of your Google Sheet
EMPLOYER_SHEET_ID = "1vJS8PHB45cZvzTljrNeSykIPgrtFjqrINkPNjWlcYUs"
EMPLOYER_TAB_NAME = "Employers"

# --- FLASK APPLICATION ---

app = Flask(__name__)

# This is the main function that will be called by your Android app
@app.route("/", methods=["POST"])
def save_employer_data():
    try:
        # 1. Get the data sent from the Android app
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request: No data received"}), 400

        id_token_str = data.get("idToken")
        employer_data = data.get("employerData")

        if not id_token_str or not employer_data:
            return jsonify({"error": "Invalid request: Missing idToken or employerData"}), 400

        # 2. SECURITY CHECK: Verify the user's ID token
        try:
            id_info = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), ANDROID_CLIENT_ID)
            print(f"Authenticated user: {id_info['email']}")
        except ValueError as e:
            print(f"Token verification failed: {e}")
            return jsonify({"error": "Invalid user token"}), 403

        # 3. Connect to Google Sheets using the service account
        gc = gspread.service_account()
        spreadsheet = gc.open_by_key(EMPLOYER_SHEET_ID)
        worksheet = spreadsheet.worksheet(EMPLOYER_TAB_NAME)

        # 4. Generate the next Employer ID
        next_id = _generate_next_employer_id(worksheet)

        # 5. Prepare the row data to be inserted
        headers = worksheet.row_values(1) # Get headers from the first row
        
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_to_insert = []
        for header in headers:
            if header == "Date":
                row_to_insert.append(current_date)
            elif header == "Employer ID":
                row_to_insert.append(next_id)
            else:
                row_to_insert.append(employer_data.get(header, ""))

        # 6. Append the new row to the sheet
        worksheet.append_row(row_to_insert, value_input_option="USER_ENTERED")

        print(f"Successfully added new employer: {next_id}")
        return jsonify({"message": f"Successfully saved employer with ID: {next_id}"}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500


def _generate_next_employer_id(worksheet):
    """Fetches all employer IDs and calculates the next one."""
    try:
        all_ids = worksheet.col_values(2) # Assuming 'Employer ID' is in the 2nd column (B)
        numeric_ids = [int(id_str[3:]) for id_str in all_ids if id_str.startswith("EMP") and id_str[3:].isdigit()]
        if not numeric_ids:
            return "EMP0001"
        next_num = max(numeric_ids) + 1
        return f"EMP{next_num:04d}"
    except Exception as e:
        print(f"Could not generate new employer ID: {e}")
        return "EMP-ERROR"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
