import datetime
import requests
import json
import os
import re
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

print(f"Current Working Directory: {os.getcwd()}")
print(f"Files in this folder: {os.listdir('.')}")

load_dotenv()
print(f"SERPER_API_KEY from .env: {os.getenv('SERPER_API_KEY')}")

# --- CONFIGURATION (Pulls from GitHub Secrets or Local) ---
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

print(f"DEBUG: Key found? {bool(SERPER_API_KEY)}")

def extract_company_name(url):
    """Simple parser to get company name from ATS URLs."""
    try:
        url = url.lower().replace('https://', '').replace('http://', '').replace('www.', '')
        if 'greenhouse.io' in url:
            match = re.search(r'greenhouse\.io/([^/]+)', url)
            return match.group(1).capitalize() if match else "Unknown"
        elif 'lever.co' in url:
            match = re.search(r'lever\.co/([^/]+)', url)
            return match.group(1).capitalize() if match else "Unknown"
        elif 'ashbyhq.com' in url:
            match = re.search(r'ashbyhq\.com/([^/]+)', url)
            return match.group(1).capitalize() if match else "Unknown"
        return url.split('.')[0].capitalize()
    except:
        return "Manual Check"

def get_search_results(query):
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    all_results = []
    
    for start_index in [0, 10, 20]:
        payload = json.dumps({
            "q": query,
            "num": 10,
            "start": start_index,
            "gl": "us"
        })
        try:
            response = requests.post(url, headers=headers, data=payload)
            if response.status_code == 200:
                page_data = response.json().get('organic', [])
                all_results.extend(page_data)
                if len(page_data) < 5: break
            else: break
        except: break
    return all_results

def update_google_sheet(rows, tab_name):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Auth Logic: GitHub vs Local Mac Mini
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        creds_info = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_dict(creds_info, scope)
    else:
        # Fallback to local file for your Mac Mini
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        
    service = build('sheets', 'v4', credentials=creds)

    # Link is now in Column E (index 4) because we added Company
    range_name = f"{tab_name}!E:E"
    try:
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        existing_links = [item[0] for item in result.get('values', []) if item]
    except:
        existing_links = []

    # Check against Link (index 4)
    new_rows = [r for r in rows if r[4] not in existing_links]

    if new_rows:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{tab_name}!A1",
            valueInputOption="USER_ENTERED",
            body={'values': new_rows}
        ).execute()
        print(f"✅ Added {len(new_rows)} jobs to {tab_name}.")

def main():
    sites = ["lever.co", "greenhouse.io", "ashbyhq.com", "app.dover.io", "apply.workable.com", "myworkdayjobs.com"]
    
    jobs_to_search = [
        {"tab": "EM", "query": '("Engineering Manager" OR "Director of Engineering") AND "Salary" (Remote) after:2026-01-01'},
        {"tab": "PM", "query": '("Product Manager" OR "Director of Product") AND "Salary" (Remote) after:2026-01-01'}
    ]

    for job_type in jobs_to_search:
        print(f"\n--- Scanning {job_type['tab']} ---")
        tab_data = []
        for site in sites:
            results = get_search_results(f"site:{site} {job_type['query']}")
            for item in results:
                link = item.get('link')
                # Date | Company | Platform | Title | Link | Snippet
                tab_data.append([
                    datetime.date.today().strftime("%Y-%m-%d"),
                    extract_company_name(link),
                    site.split('.')[0],
                    item.get('title'),
                    link,
                    item.get('snippet')
                ])
        
        if tab_data:
            update_google_sheet(tab_data, job_type['tab'])

if __name__ == "__main__":
    main()