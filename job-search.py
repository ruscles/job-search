import datetime
import requests
import json
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---

JSON_KEYFILE = "service_account_credentials.json"

QUERY = 'site:lever.co | site:greenhouse.io | site:app.dover.io | site:jobs.ashbyhq.com "Engineering Manager" (Senior or Director) AND "Salary" (Remote) after:2024-10-02'

def get_search_results(query):
    url = "https://google.serper.dev/search"
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    all_results = []
    
    # Using the stable 'start' pagination to bypass the 31-result wall
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
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEYFILE, scope)
    service = build('sheets', 'v4', credentials=creds)

    # Check existing links in Column D (previously C, shifted for new Platform col)
    range_name = f"{tab_name}!D:D"
    try:
        sheet_data = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        existing_links = [item[0] for item in sheet_data.get('values', []) if item]
    except:
        existing_links = []

    new_rows = [r for r in rows if r[3] not in existing_links]

    if new_rows:
        append_range = f"{tab_name}!A1"
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=append_range,
            valueInputOption="USER_ENTERED",
            body={'values': new_rows}
        ).execute()
        print(f"✅ Added {len(new_rows)} jobs to {tab_name}.")

def main():
    # Organized by 'Apply Difficulty'
    startup_ats = ["lever.co", "greenhouse.io", "ashbyhq.com", "app.dover.io", "apply.workable.com", "rippling.com"]
    enterprise_ats = ["myworkdayjobs.com", "smartrecruiters.com", "jobvite.com", "bamboohr.com"]
    niche_boards = ["wellfound.com", "weworkremotely.com", "builtin.com"]
    
    all_sites = startup_ats + enterprise_ats + niche_boards

    jobs_to_search = [
        {
            "tab": "EM",
            "query": '("Engineering Manager" OR "Sr. Engineering Manager" OR "Director of Engineering") AND "Salary" (Remote) after:2026-01-01'
        },
        {
            "tab": "PM",
            "query": '("Product Manager" OR "Sr. Product Manager" OR "Staff PM" OR "Group PM" OR "Director of Product") AND "Salary" (Remote) after:2026-01-01'
        }
    ]

    for job_type in jobs_to_search:
        print(f"\n--- Scanning for {job_type['tab']} Roles ---")
        tab_data = []
        
        for site in all_sites:
            full_query = f"site:{site} {job_type['query']}"
            print(f"Checking {site}...")
            results = get_search_results(full_query)
            
            for item in results:
                # Column Logic: Date | Platform | Title | Link | Snippet
                tab_data.append([
                    datetime.date.today().strftime("%Y-%m-%d"),
                    site.split('.')[0], # Simplified Platform Name
                    item.get('title'),
                    item.get('link'),
                    item.get('snippet')
                ])
        
        if tab_data:
            update_google_sheet(tab_data, job_type['tab'])

if __name__ == "__main__":
    main()