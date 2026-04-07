import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime, timezone
import time
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Load secrets securely
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- CONFIGURATION ---
CHANNEL_ID = 1482998910564827236  # Your #when-is-f1-on channel ID
ROLE_ID = 1483013359254110250     # Your @f1 notifications role ID

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

PRE_SEASON = (
    "## 🇧🇭 Pre-Season Testing\n"
    "> ~~`Week 1 Day 1`: <t:1770822000:F> (<t:1770822000:R>)~~\n"
    "> ~~`Week 1 Day 2`: <t:1770908400:F> (<t:1770908400:R>)~~\n"
    "> ~~`Week 1 Day 3`: <t:1770994800:F> (<t:1770994800:R>)~~\n"
    "> ~~`Week 2 Day 1`: <t:1771398000:F> (<t:1771398000:R>)~~\n"
    "> ~~`Week 2 Day 2`: <t:1771484400:F> (<t:1771484400:R>)~~\n"
    "> ~~`Week 2 Day 3`: <t:1771570800:F> (<t:1771570800:R>)~~\n"
)

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- GLOBAL STATE ---
schedule_cache = []
calendar_messages = []    
next_gp_message = None    
current_next_round = None

def to_unix(date_str, time_str):
    try:
        dt_str = f"{date_str}T{time_str}"
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
        dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except:
            return 0 

def format_session(api_key, date_str, time_str, current_time, is_short_msg=False):
    name_map = {
        "FirstPractice": "Practice 1 ", "SecondPractice": "Practice 2 ",
        "ThirdPractice": "Practice 3 ", "Qualifying": "Qualifying ",
        "SprintQualifying": "Sprint Qual", "Sprint": "    Sprint ",
        "Race": "      Race "
    }
    display_name = name_map.get(api_key, api_key)
    unix_time = to_unix(date_str, time_str)
    
    line = f"`{display_name}`: <t:{unix_time}:F> (<t:{unix_time}:R>)"
    
    if unix_time < current_time:
        if is_short_msg:
            return f"~~{line}~~"   # No blockquote for the short message
        return f"> ~~{line}~~"     # Add blockquote for the calendar
        
    if is_short_msg:
        return f"{line}"           # No blockquote for the short message
    return f"> {line}"             # Add blockquote for the calendar

def generate_short_msg(race, current_time):
    race_name = race['raceName']
    flag = FLAG_EMOJIS.get(race_name, "🏁")
    msg = f"## {flag} {race_name}\n\n"
    
    if 'FirstPractice' in race: msg += format_session("FirstPractice", race['FirstPractice']['date'], race['FirstPractice']['time'], current_time, True) + "\n"
    if 'Sprint' in race:
        if 'SprintQualifying' in race: msg += format_session("SprintQualifying", race['SprintQualifying']['date'], race['SprintQualifying']['time'], current_time, True) + "\n"
        msg += format_session("Sprint", race['Sprint']['date'], race['Sprint']['time'], current_time, True) + "\n"
    else:
        if 'SecondPractice' in race: msg += format_session("SecondPractice", race['SecondPractice']['date'], race['SecondPractice']['time'], current_time, True) + "\n"
        if 'ThirdPractice' in race: msg += format_session("ThirdPractice", race['ThirdPractice']['date'], race['ThirdPractice']['time'], current_time, True) + "\n"
    if 'Qualifying' in race: msg += format_session("Qualifying", race['Qualifying']['date'], race['Qualifying']['time'], current_time, True) + "\n"
         
    msg += format_session("Race", race['date'], race['time'], current_time, True) + "\n\n"
    msg += f"Use **Channels & Roles** and get the <@&{ROLE_ID}> role to receive notifications!"
    return msg

@tasks.loop(hours=24)
async def fetch_api_data():
    global schedule_cache
    try:
        url = "http://api.jolpi.ca/ergast/f1/current.json"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            schedule_cache = response.json()['MRData']['RaceTable']['Races']
            print(f"[{datetime.now().strftime('%H:%M:%S')}] F1 Schedule data refreshed.")
        else:
            print(f"API returned status {response.status_code}. Retrying later.")
    except Exception as e:
        print(f"API Fetch Failed: {e}")

@tasks.loop(minutes=5)
async def dashboard_manager():
    try:
        global calendar_messages, next_gp_message, current_next_round
        
        channel = bot.get_channel(CHANNEL_ID)
        if not channel or not schedule_cache: return

        current_time = time.time()
        
        # --- 1. FIND THE NEXT GP ---
        upcoming_races = [r for r in schedule_cache if to_unix(r['date'], r['time']) > current_time]
        next_race = min(upcoming_races, key=lambda r: to_unix(r['date'], r['time'])) if upcoming_races else None

        # --- 2. BRUTE-FORCE CUSTOM SORT ---
        def custom_sort(race):
            name = race['raceName'].lower()
            if "australia" in name: return 1
            if "china" in name or "chinese" in name: return 2
            if "japan" in name: return 3
            if "bahrain" in name: return 4
            if "saudi" in name: return 5
            return to_unix(race['date'], race['time'])
            
        display_schedule = sorted(schedule_cache, key=custom_sort)

        # --- 3. BUILD SEAMLESS CHUNKS ---
        calendar_chunks = []
        current_chunk = f"# F1 2026 Calendar\n\n{PRE_SEASON}"
        
        for race in display_schedule:
            race_name = race['raceName']
            flag = FLAG_EMOJIS.get(race_name, "🏁")
            race_block = f"## {flag} {race_name}\n"
            
            if 'FirstPractice' in race: race_block += format_session("FirstPractice", race['FirstPractice']['date'], race['FirstPractice']['time'], current_time) + "\n"
            if 'Sprint' in race:
                if 'SprintQualifying' in race: race_block += format_session("SprintQualifying", race['SprintQualifying']['date'], race['SprintQualifying']['time'], current_time) + "\n"
                race_block += format_session("Sprint", race['Sprint']['date'], race['Sprint']['time'], current_time) + "\n"
            else:
                if 'SecondPractice' in race: race_block += format_session("SecondPractice", race['SecondPractice']['date'], race['SecondPractice']['time'], current_time) + "\n"
                if 'ThirdPractice' in race: race_block += format_session("ThirdPractice", race['ThirdPractice']['date'], race['ThirdPractice']['time'], current_time) + "\n"
            if 'Qualifying' in race: race_block += format_session("Qualifying", race['Qualifying']['date'], race['Qualifying']['time'], current_time) + "\n"
            race_block += format_session("Race", race['date'], race['time'], current_time) + "\n"
            
            if len(current_chunk) + len(race_block) > 1900:
                calendar_chunks.append(current_chunk)
                current_chunk = race_block
            else:
                current_chunk += race_block
                
        footer_text = "\n*Reserved for Calendar*"
        if len(current_chunk) + len(footer_text) > 1900:
            calendar_chunks.append(current_chunk)
            current_chunk = footer_text
        else:
            current_chunk += footer_text
            
        if current_chunk: calendar_chunks.append(current_chunk)

        # --- 4. UPDATE CALENDAR MESSAGES ---
        for i, chunk_text in enumerate(calendar_chunks):
            if i < len(calendar_messages):
                if calendar_messages[i].content.strip() != chunk_text.strip():
                    await calendar_messages[i].edit(content=chunk_text)
            else:
                msg = await channel.send(chunk_text)
                calendar_messages.append(msg)

        while len(calendar_messages) > len(calendar_chunks):
            extra_msg = calendar_messages.pop() 
            try:
                await extra_msg.delete()        
            except discord.NotFound:
                pass

        # --- 5. MANAGE NEXT GP MESSAGE ---
        if next_race:
            round_number = next_race['round']
            short_text = generate_short_msg(next_race, current_time)
            
            if current_next_round is None:
                current_next_round = round_number
                
            if current_next_round != round_number:
                if next_gp_message:
                    try: await next_gp_message.delete()
                    except discord.NotFound: pass 
                next_gp_message = await channel.send(short_text)
                current_next_round = round_number
            elif next_gp_message:
                if next_gp_message.content.strip() != short_text.strip():
                    await next_gp_message.edit(content=short_text)
            else:
                next_gp_message = await channel.send(short_text)
                
    except Exception as e:
        print(f"Error in dashboard_manager loop: {e}")

@bot.event
async def on_ready():
    global calendar_messages, next_gp_message
    print(f"Logged in as {bot.user}")
    
    fetch_api_data.start()
    
    # Wait for API data, but don't hang forever
    timeout = 0
    while not schedule_cache and timeout < 15:
        await asyncio.sleep(1) 
        timeout += 1
        
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        print("Scanning channel history for existing bot messages...")
        bot_msgs = []
        async for msg in channel.history(limit=50, oldest_first=True):
            if msg.author == bot.user:
                bot_msgs.append(msg)
                
        calendar_messages = []
        next_gp_message = None
        for msg in bot_msgs:
            if "Use **Channels & Roles**" in msg.content:
                next_gp_message = msg
                print("-> Hooked into existing Next GP message.")
            else:
                calendar_messages.append(msg)
                print(f"-> Hooked into Calendar Chunk {len(calendar_messages)}.")
        
        dashboard_manager.start()
        print("Live Dashboard is running smoothly!")

# --- DUMMY WEB SERVER (RENDER KEEP-ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "F1 Dashboard Bot is awake and running!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- START UP EVERYTHING ---
keep_alive()
bot.run(TOKEN)
