import pandas as pd
import requests
import json
import os
import sys
import io
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

CURRENT_YEAR = "2026"

def get_column_by_substring(df, substrings):
    """Finds a column index matching any of the given substrings (case-insensitive)."""
    for sub in substrings:
        for i, col in enumerate(df.columns):
            if sub.lower() in str(col).lower():
                return i
    return None

def normalize_race_name(name):
    if not name:
        return ""
    # Remove Grand Prix / GP case-insensitive
    clean = re.sub(r'grand prix', '', name, flags=re.IGNORECASE)
    clean = re.sub(r'\bgp\b', '', clean, flags=re.IGNORECASE)
    clean = clean.strip()
    
    # Replacement mapping (case-insensitive)
    replacements = {
        "bahrain": "Bahrain",
        "saudi arabia": "Saudi Arabia",
        "australian": "Australia",
        "china": "Chinese",
        "japan": "Japanese",
        "emilia romagna": "Emilia Romagna",
        "miami": "Miami",
        "monaco": "Monaco",
        "spain": "Spanish",
        "canada": "Canadian",
        "austria": "Austrian",
        "great britain": "British",
        "hungary": "Hungarian",
        "belgium": "Belgian",
        "netherlands": "Dutch",
        "italy": "Italian",
        "azerbaijan": "Azerbaijan",
        "singapore": "Singapore",
        "united states": "United States",
        "mexico": "Mexican",
        "brazil": "Brazilian",
        "las vegas": "Las Vegas",
        "qatar": "Qatar",
        "abu dhabi": "Abu Dhabi",
        "lasvegas": "Las Vegas",
        "sao paulo": "Brazilian",
        "barcelona": "Barcelona-Catalunya"
    }
    
    lower_clean = clean.lower()
    for pattern, replacement in replacements.items():
        if pattern in lower_clean:
            clean = replacement
            break
            
    return clean + " Grand Prix"

def parse_driver_name(raw_name):
    """Cleans up clumpy or corrupted string spacing layouts from F1.com tables."""
    clean_name = str(raw_name).replace('\u00a0', ' ').strip()
    name_parts = clean_name.split(' ')
    name_parts = [p for p in name_parts if p]
    
    if not name_parts:
        return "", "", "UNK"
        
    if len(name_parts) == 1:
        last_part = name_parts[0]
        if len(last_part) > 3 and last_part[-3:].isupper() and last_part[-3:].isalpha():
            return "", last_part[:-3].strip(), last_part[-3:]
        else:
            return last_part, "", "UNK"
            
    given_name = name_parts[0]
    last_part = name_parts[-1]
    
    if len(last_part) > 3 and last_part[-3:].isupper() and last_part[-3:].isalpha():
        code = last_part[-3:]
        family_last = last_part[:-3]
        middle_parts = name_parts[1:-1]
        family_name = " ".join(middle_parts + [family_last]) if middle_parts else family_last
    else:
        code = last_part
        family_name = " ".join(name_parts[1:])
        
    return given_name.strip(), family_name.strip(), code.strip()

def get_race_name_to_round_mapping():
    """Fetches F1Calendar.com data and returns a mapping from normalized race name to round number."""
    url = f"https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1/{CURRENT_YEAR}.json"
    mapping = {}
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for index, item in enumerate(data.get("races", [])):
                name = item.get("name", "")
                norm_name = normalize_race_name(name)
                round_num = str(item.get("round", index + 1))
                mapping[norm_name] = round_num
    except Exception as e:
        print(f"⚠️ Warning: Could not generate race name to round mapping: {e}")
    return mapping

def scrape_standings():
    print("Scraping Official F1 Standings...")
    url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/drivers.html"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            raise ValueError(f"HTTP Status {response.status_code}")
            
        tables = pd.read_html(io.StringIO(response.text))
        if not tables:
            raise ValueError("No tables found on the F1 standings page.")
        df = tables[0]
        
        pos_idx = get_column_by_substring(df, ['pos', 'position'])
        if pos_idx is None: pos_idx = 0
        
        driver_idx = get_column_by_substring(df, ['driver', 'name'])
        if driver_idx is None: driver_idx = 1
        
        car_idx = get_column_by_substring(df, ['car', 'team', 'constructor'])
        if car_idx is None: car_idx = 3
        
        pts_idx = get_column_by_substring(df, ['pts', 'points'])
        if pts_idx is None: pts_idx = 4
        
        standings_list = []
        for index, row in df.iterrows():
            given_name, family_name, code = parse_driver_name(row.iloc[driver_idx])
            p_val = str(row.iloc[pos_idx]).strip()
            pts_val = str(row.iloc[pts_idx]).strip()
            
            standings_list.append({
                "position": p_val,
                "points": pts_val,
                "Driver": {
                    "givenName": given_name,
                    "familyName": family_name,
                    "code": code
                },
                "Constructors": [{"name": str(row.iloc[car_idx]).strip()}]
            })

        ergast_json = {
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": [{"DriverStandings": standings_list}]
                }
            }
        }

        os.makedirs("api", exist_ok=True)
        with open("api/standings.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Standings updated successfully.")

    except Exception as e:
        print(f"❌ Failed to scrape standings: {e}")
        raise e

def scrape_race_results(name_to_round):
    print("Scraping Official F1 Race Winners and Podiums...")
    master_url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/races.html"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(master_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        race_paths = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"/{CURRENT_YEAR}/races/" in href and ("race-result" in href or "result.html" in href):
                full_url = urljoin(master_url, href)
                race_paths.append(full_url)
                
        race_paths = list(dict.fromkeys(race_paths))
        print(f"Found {len(race_paths)} valid {CURRENT_YEAR} race links to scan.")
        
        races_list = []
        for detail_url in race_paths:
            try:
                detail_response = requests.get(detail_url, headers=headers, timeout=10)
                if detail_response.status_code != 200:
                    continue
                    
                detail_tables = pd.read_html(io.StringIO(detail_response.text))
                if not detail_tables:
                    continue
                
                race_df = None
                for table in detail_tables:
                    p_idx = get_column_by_substring(table, ['pos', 'position'])
                    if p_idx is not None and len(table) > 0:
                        first_val = str(table.iloc[0, p_idx]).strip()
                        if first_val == "1":
                            race_df = table
                            break
                
                if race_df is None:
                    race_df = detail_tables[0]
                
                pos_idx = get_column_by_substring(race_df, ['pos', 'position'])
                if pos_idx is None: pos_idx = 0
                
                driver_idx = get_column_by_substring(race_df, ['driver', 'name'])
                if driver_idx is None: driver_idx = 2
                
                if len(race_df) == 0 or "no results available" in str(race_df.iloc[0]).lower():
                    continue

                segments = detail_url.split('/')
                slug_idx = -2 if segments[-1].endswith('.html') and 'race-result' in segments[-1] else -1
                gp_slug = segments[slug_idx].replace('-', ' ').title()
                
                if not gp_slug or gp_slug.isdigit() or gp_slug.lower() in ['race result', 'race-result']:
                    gp_slug = segments[slug_idx - 1].replace('-', ' ').title()
                
                gp_name = gp_slug if "grand prix" in gp_slug.lower() else f"{gp_slug} Grand Prix"
                if "Usa" in gp_name: gp_name = gp_name.replace("Usa", "United States")
                
                norm_gp_name = normalize_race_name(gp_name)
                round_val = name_to_round.get(norm_gp_name)
                
                podium_results = []
                for i in range(min(3, len(race_df))):
                    row = race_df.iloc[i]
                    p_val = str(row.iloc[pos_idx]).strip()
                    
                    if not p_val.isdigit():
                        continue
                        
                    given_name, family_name, code = parse_driver_name(row.iloc[driver_idx])
                    
                    podium_results.append({
                        "position": p_val,
                        "Driver": {
                            "givenName": given_name,
                            "familyName": family_name,
                            "code": code
                        }
                    })
                
                if podium_results:
                    race_obj = {
                        "raceName": gp_name,
                        "Results": podium_results
                    }
                    if round_val:
                        race_obj["round"] = round_val
                    races_list.append(race_obj)
            except Exception as item_err:
                print(f"⚠️ Skipping item table processing mismatch: {item_err}")
                continue

        races_list.sort(key=lambda x: int(x.get("round", 999)))

        ergast_json = {
            "MRData": {
                "RaceTable": {
                    "Races": races_list
                }
            }
        }

        os.makedirs("api", exist_ok=True)
        with open("api/results.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Full Race Results (Podiums) updated successfully.")

    except Exception as e:
        print(f"❌ Failed to scrape race details: {e}")
        raise e

def scrape_qualifying_results(name_to_round):
    print("Scraping Official F1 Qualifying Results...")
    master_url = f"https://www.formula1.com/en/results.html/{CURRENT_YEAR}/races.html"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(master_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        race_paths = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"/{CURRENT_YEAR}/races/" in href and ("race-result" in href or "result.html" in href):
                full_url = urljoin(master_url, href)
                race_paths.append(full_url)
                
        race_paths = list(dict.fromkeys(race_paths))
        print(f"Found {len(race_paths)} valid {CURRENT_YEAR} race links to check for qualifying.")
        
        qualis_list = []
        for detail_url in race_paths:
            if detail_url.endswith("/race-result"):
                quali_url = detail_url[:-12] + "/qualifying"
            elif detail_url.endswith("/race-result.html"):
                quali_url = detail_url[:-17] + "/qualifying.html"
            else:
                quali_url = detail_url.replace("race-result", "qualifying")
                
            try:
                detail_response = requests.get(quali_url, headers=headers, timeout=10)
                if detail_response.status_code != 200:
                    continue
                    
                detail_tables = pd.read_html(io.StringIO(detail_response.text))
                if not detail_tables:
                    continue
                
                quali_df = None
                for table in detail_tables:
                    p_idx = get_column_by_substring(table, ['pos', 'position'])
                    if p_idx is not None and len(table) > 0:
                        first_val = str(table.iloc[0, p_idx]).strip()
                        if first_val == "1":
                            quali_df = table
                            break
                            
                if quali_df is None:
                    quali_df = detail_tables[0]
                    
                pos_idx = get_column_by_substring(quali_df, ['pos', 'position'])
                if pos_idx is None: pos_idx = 0
                    
                driver_idx = get_column_by_substring(quali_df, ['driver', 'name'])
                if driver_idx is None: driver_idx = 2
                    
                car_idx = get_column_by_substring(quali_df, ['car', 'team', 'constructor'])
                if car_idx is None: car_idx = 3
                    
                q1_idx = get_column_by_substring(quali_df, ['q1'])
                q2_idx = get_column_by_substring(quali_df, ['q2'])
                q3_idx = get_column_by_substring(quali_df, ['q3'])
                
                if len(quali_df) == 0 or "no results available" in str(quali_df.iloc[0]).lower():
                    continue

                segments = detail_url.split('/')
                slug_idx = -2 if segments[-1].endswith('.html') and 'race-result' in segments[-1] else -1
                gp_slug = segments[slug_idx].replace('-', ' ').title()
                
                if not gp_slug or gp_slug.isdigit() or gp_slug.lower() in ['race result', 'race-result']:
                    gp_slug = segments[slug_idx - 1].replace('-', ' ').title()
                
                gp_name = gp_slug if "grand prix" in gp_slug.lower() else f"{gp_slug} Grand Prix"
                if "Usa" in gp_name: gp_name = gp_name.replace("Usa", "United States")
                
                norm_gp_name = normalize_race_name(gp_name)
                round_val = name_to_round.get(norm_gp_name)
                
                qualifying_results = []
                for i in range(len(quali_df)):
                    row = quali_df.iloc[i]
                    p_val = str(row.iloc[pos_idx]).strip()
                    
                    if not p_val.isdigit():
                        continue
                        
                    given_name, family_name, code = parse_driver_name(row.iloc[driver_idx])
                    
                    team_name = str(row.iloc[car_idx]).strip() if car_idx is not None else ""
                    constructor_id = team_name.lower().replace(" racing", "").replace(" f1 team", "").replace(" team", "").replace(" ", "_").strip()
                    
                    q1_val = str(row.iloc[q1_idx]).strip() if q1_idx is not None else ""
                    q2_val = str(row.iloc[q2_idx]).strip() if q2_idx is not None else ""
                    q3_val = str(row.iloc[q3_idx]).strip() if q3_idx is not None else ""
                    
                    if q1_val.lower() in ["nan", "null", "none"]: q1_val = ""
                    if q2_val.lower() in ["nan", "null", "none"]: q2_val = ""
                    if q3_val.lower() in ["nan", "null", "none"]: q3_val = ""
                    
                    qualifying_results.append({
                        "position": p_val,
                        "Driver": {
                            "givenName": given_name,
                            "familyName": family_name,
                            "code": code
                        },
                        "Constructor": {
                            "constructorId": constructor_id,
                            "name": team_name
                        },
                        "Q1": q1_val,
                        "Q2": q2_val,
                        "Q3": q3_val
                    })
                
                if qualifying_results:
                    race_obj = {
                        "raceName": gp_name,
                        "QualifyingResults": qualifying_results
                    }
                    if round_val:
                        race_obj["round"] = round_val
                    qualis_list.append(race_obj)
            except Exception as item_err:
                print(f"⚠️ Skipping item table processing mismatch: {item_err}")
                continue
                
        qualis_list.sort(key=lambda x: int(x.get("round", 999)))

        ergast_json = {
            "MRData": {
                "RaceTable": {
                    "Races": qualis_list
                }
            }
        }
        
        os.makedirs("api", exist_ok=True)
        with open("api/qualifying.json", "w", encoding="utf-8") as f:
            json.dump(ergast_json, f, indent=2)
        print("✅ Qualifying Results updated successfully.")
        
    except Exception as e:
        print(f"❌ Failed to scrape qualifying details: {e}")
        raise e

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
        name_to_round = get_race_name_to_round_mapping()
        scrape_standings()
        scrape_race_results(name_to_round)
        scrape_qualifying_results(name_to_round)
        generate_clean_calendar()
        print("🚀 API generation completed successfully!")
    except Exception as main_error:
        print(f"💥 Critical API build failure: {main_error}")
        sys.exit(1)