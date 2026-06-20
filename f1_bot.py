import os
import sys
import json
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
import discord

# Load environment variables from .env file if available (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BOT_DIR = Path(__file__).resolve().parent

# --- CONFIGURATION ---
CHANNEL_ID = 1482998910564827236  # Your channel ID
ROLE_ID = 1483013359254110250     # Your notification role ID
TOKEN = os.getenv('DISCORD_TOKEN')

FLAG_EMOJIS = {
    "Bahrain Grand Prix": "🇧🇭", "Saudi Arabian Grand Prix": "🇸🇦",
    "Australian Grand Prix": "🇦🇺", "Japanese Grand Prix": "🇯🇵",
    "Chinese Grand Prix": "🇨🇳", "Miami Grand Prix": "🇺🇸",
    "Emilia Romagna Grand Prix": "🇮🇹", "Monaco Grand Prix": "🇲🇨",
    "Canadian Grand Prix": "🇨🇦", "Spanish Grand Prix": "🇪🇸",
    "Austrian Grand Prix": "🇦🇹", "British Grand Prix": "🇬🇧",
    "Hungarian Grand Prix": "🇭🇺", "Belgian Grand Prix": "🇧🇪",
    "Dutch Grand Prix": "🇳🇱", "Italian Grand Prix": "🇮🇹",
    "Azerbaijan Grand Prix": "🇦🇿", "Singapore Grand Prix": "🇸🇬",
    "United States Grand Prix": "🇺🇸", "Mexico City Grand Prix": "🇲🇽",
    "São Paulo Grand Prix": "🇧🇷", "Las Vegas Grand Prix": "🇺🇸",
    "Qatar Grand Prix": "🇶🇦", "Abu Dhabi Grand Prix": "🇦🇪"
}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def to_unix(date_str, time_str):
    try:
        dt_str = f"{date_str}T{time_str}"
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except:
        try:
            return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        except:
            return 0 

def generate_short_msg(race, current_time):
    race_name = race['raceName']
    flag = FLAG_EMOJIS.get(race_name, "🏁")
    msg = f"## {flag} {race_name}\n\n"
    
    # Simple formatting logic for the sessions
    for sess_key, display in [("FirstPractice", "Practice 1"), ("SecondPractice", "Practice 2"), 
                              ("ThirdPractice", "Practice 3"), ("SprintQualifying", "Sprint Qual"), 
                              ("Sprint", "Sprint"), ("Qualifying", "Qualifying"), ("Race", "Race")]:
        if sess_key in race:
            unix = to_unix(race[sess_key]['date'], race[sess_key]['time'])
            line = f"`{display.ljust(11)}`: <t:{unix}:F> (<t:{unix}:R>)"
            msg += f"~~{line}~~\n" if unix < current_time else f"{line}\n"
            
    msg += f"\nUse **Channels & Roles** and get the <@&{ROLE_ID}> role to receive notifications!"
    return msg

@client.event
async def on_ready():
    print(f"Logged in as {client.user}. Running scheduled updates...")
    try:
        channel = client.get_channel(CHANNEL_ID)
        if not channel:
            print("❌ Channel not found.")
            await client.close()
            return

        # 1. READ FROM YOUR OWN LOCAL API PATH OR FETCH DYNAMICALLY
        api_dir = BOT_DIR / "api"
        api_path = api_dir / "current.json"
        schedule_cache = None

        if api_path.exists():
            try:
                with open(api_path, "r", encoding="utf-8") as f:
                    schedule_cache = json.load(f)['MRData']['RaceTable']['Races']
                print("✅ Loaded schedule from local cache.")
            except Exception as e:
                print(f"⚠️ Failed to parse local cache: {e}")

        if not schedule_cache:
            print("🌐 Fetching current schedule from Jolpica F1 API...")
            try:
                import urllib.request
                api_url = "https://api.jolpi.ca/ergast/f1/current.json"
                req = urllib.request.Request(
                    api_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    schedule_cache = data['MRData']['RaceTable']['Races']
                
                # Cache the response locally
                api_dir.mkdir(parents=True, exist_ok=True)
                with open(api_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                print("✅ Successfully fetched and cached schedule.")
            except Exception as e:
                print(f"❌ Failed to fetch schedule from API: {e}")
                await client.close()
                return

        current_time = time.time()
        upcoming_races = [r for r in schedule_cache if to_unix(r['date'], r['time']) > current_time]
        next_race = min(upcoming_races, key=lambda r: to_unix(r['date'], r['time'])) if upcoming_races else None

        if not next_race:
            print("No upcoming races found.")
            await client.close()
            return

        short_text = generate_short_msg(next_race, current_time)

        # 2. FIND EXISTING BOT MESSAGE TO UPDATE OR POST A NEW ONE
        existing_msg = None
        async for msg in channel.history(limit=20):
            if msg.author == client.user and "Use **Channels & Roles**" in msg.content:
                existing_msg = msg
                break

        if existing_msg:
            if existing_msg.content.strip() != short_text.strip():
                await existing_msg.edit(content=short_text)
                print("✅ Next GP message updated successfully.")
            else:
                print("ℹ️ No changes detected. Skipping edit.")
        else:
            await channel.send(short_text)
            print("✅ Sent new next GP message block.")

    except Exception as e:
        print(f"💥 Error running bot task: {e}")
        
    # 3. CLOSE CONNECTION IMMEDIATELY TO SHUT DOWN THE WORKFLOW RUNNER
    print("Shutting down runner connection cleanly.")
    await client.close()

if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN secret environment variable missing.")
        sys.exit(1)
    client.run(TOKEN)