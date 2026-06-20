import requests
import json
import os
import sys

CURRENT_YEAR = "2026"

def generate_clean_calendar():
    print("Fetching Complete Session Calendar from F1Calendar.com...")
    url = f"https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/{CURRENT_YEAR}.json"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            raise ValueError(f"Failed to pull community database: {response.status_code}")
            
        data = response.json()
        races_list = []
        
        def parse_session_time(timestamp):
            if not timestamp:
                return None
            if 'T' in timestamp:
                parts = timestamp.split('T')
                return {"date": parts[0], "time": parts[1]}
            return {"date": timestamp, "time": "00:00:00Z"}

        for index, item in enumerate(data.get("races", [])):
            sessions = item.get("sessions", {})
            
            gp_time_raw = sessions.get("gp")
            if gp_time_raw and 'T' in gp_time_raw:
                gp_date = gp_time_raw.split('T')[0]
                gp_time = gp_time_raw.split('T')[1]
            else:
                gp_date = item.get("date", "2026-01-01")
                gp_time = "13:00:00Z"
                
            race_obj = {
                "round": str(item.get("round", index + 1)),
                "raceName": item.get("name", "Grand Prix"),
                "date": gp_date,
                "time": gp_time,
                "Circuit": { "circuitName": item.get("location", "Official Circuit") }
            }
            
            if "fp1" in sessions:
                race_obj["FirstPractice"] = parse_session_time(sessions["fp1"])
            if "fp2" in sessions:
                race_obj["SecondPractice"] = parse_session_time(sessions["fp2"])
            if "fp3" in sessions:
                race_obj["ThirdPractice"] = parse_session_time(sessions["fp3"])
            if "sprintQualifying" in sessions:
                race_obj["SprintQualifying"] = parse_session_time(sessions["sprintQualifying"])
            elif "sprintShootout" in sessions: 
                race_obj["SprintQualifying"] = parse_session_time(sessions["sprintShootout"])
            if "sprint" in sessions:
                race_obj["Sprint"] = parse_session_time(sessions["sprint"])
            if "qualifying" in sessions:
                race_obj["Qualifying"] = parse_session_time(sessions["qualifying"])
                
            races_list.append(race_obj)

        ergast_json = {
            "MRData": {
                "RaceTable": {
                    "season": CURRENT_YEAR,
                    "Races": races_list
                }
            }
        }

        os.makedirs("api", exist_ok=True)
        with open("api/current.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Comprehensive multi-session calendar cached successfully.")

    except Exception as e:
        print(f"❌ Failed to parse all community sessions: {e}")
        raise e

if __name__ == "__main__":
    try:
        generate_clean_calendar()
        print("🚀 API generation completed successfully!")
    except Exception as main_error:
        print(f"💥 Critical API build failure: {main_error}")
        sys.exit(1)