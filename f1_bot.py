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

def normalize_race_name(name):
    if not name:
        return ""
    if "grand prix" in name.lower():
        return name
        
    mapping = {
        "Australian": "Australian Grand Prix",
        "Chinese": "Chinese Grand Prix",
        "Japanese": "Japanese Grand Prix",
        "Miami": "Miami Grand Prix",
        "Canadian": "Canadian Grand Prix",
        "Monaco": "Monaco Grand Prix",
        "Barcelona-Catalunya": "Spanish Grand Prix",
        "Austrian": "Austrian Grand Prix",
        "British": "British Grand Prix",
        "Belgian": "Belgian Grand Prix",
        "Hungarian": "Hungarian Grand Prix",
        "Dutch": "Dutch Grand Prix",
        "Italian": "Italian Grand Prix",
        "Spanish": "Spanish Grand Prix",
        "Azerbaijan": "Azerbaijan Grand Prix",
        "Singapore": "Singapore Grand Prix",
        "United States": "United States Grand Prix",
        "Mexican": "Mexico City Grand Prix",
        "Brazilian": "Brazilian Grand Prix",
        "Las Vegas": "Las Vegas Grand Prix",
        "Qatar": "Qatar Grand Prix",
        "Abu Dhabi": "Abu Dhabi Grand Prix",
        "Australia": "Australian Grand Prix",
        "China": "Chinese Grand Prix",
        "Japan": "Japanese Grand Prix",
        "Canada": "Canadian Grand Prix",
        "São Paulo": "São Paulo Grand Prix",
        "Emilia Romagna": "Emilia Romagna Grand Prix",
        "Bahrain": "Bahrain Grand Prix",
        "Saudi Arabia": "Saudi Arabian Grand Prix",
        "Barcelona": "Spanish Grand Prix"
    }
    return mapping.get(name, name + " Grand Prix")

def format_session(api_key, date_str, time_str, current_time):
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
        return f"> ~~{line}~~"
    return f"> {line}"

def format_race_header(race_name, is_past=False):
    flag = FLAG_EMOJIS.get(race_name, "🏁")
    return f"## {flag} {race_name}"

def generate_short_msg(race, current_time, rules_mention="#rules", role_mention=None):
    race_name = race['raceName']
    flag = FLAG_EMOJIS.get(race_name, "🏁")
    msg = f"## {flag} {race_name}\n\n"

    if 'FirstPractice' in race:
        msg += format_session("FirstPractice", race['FirstPractice']['date'], race['FirstPractice']['time'], current_time) + "\n"
    if 'Sprint' in race:
        if 'SprintQualifying' in race:
            msg += format_session("SprintQualifying", race['SprintQualifying']['date'], race['SprintQualifying']['time'], current_time) + "\n"
        msg += format_session("Sprint", race['Sprint']['date'], race['Sprint']['time'], current_time) + "\n"
    else:
        if 'SecondPractice' in race:
            msg += format_session("SecondPractice", race['SecondPractice']['date'], race['SecondPractice']['time'], current_time) + "\n"
        if 'ThirdPractice' in race:
            msg += format_session("ThirdPractice", race['ThirdPractice']['date'], race['ThirdPractice']['time'], current_time) + "\n"
    if 'Qualifying' in race:
        msg += format_session("Qualifying", race['Qualifying']['date'], race['Qualifying']['time'], current_time) + "\n"

    msg += format_session("Race", race['date'], race['time'], current_time) + "\n\n"
    
    if not role_mention:
        role_mention = f"<@&{ROLE_ID}>"
    msg += f"React on F1 emoji in {rules_mention} to get {role_mention} role to receive notifications!\nVisit <https://f1.trionine.com/> for the web dashboard."
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

        # Normalize all race names in schedule cache
        for race in schedule_cache:
            race['raceName'] = normalize_race_name(race['raceName'])

        current_time = time.time()
        upcoming_races = [r for r in schedule_cache if to_unix(r['date'], r['time']) > current_time]
        next_race = min(upcoming_races, key=lambda r: to_unix(r['date'], r['time'])) if upcoming_races else None

        # Sort schedule by round number
        display_schedule = sorted(schedule_cache, key=lambda r: int(r.get('round', 0)))

        # --- BUILD CALENDAR CHUNKS ---
        calendar_chunks = []
        current_chunk = f"# F1 2026 Calendar\n\n{PRE_SEASON}"

        for race in display_schedule:
            race_name = race['raceName']
            is_past_race = to_unix(race['date'], race['time']) < current_time
            race_block = format_race_header(race_name, is_past_race) + "\n"

            if 'FirstPractice' in race:
                race_block += format_session("FirstPractice", race['FirstPractice']['date'], race['FirstPractice']['time'], current_time) + "\n"
            
            if 'Sprint' in race:
                if 'SprintQualifying' in race:
                    race_block += format_session("SprintQualifying", race['SprintQualifying']['date'], race['SprintQualifying']['time'], current_time) + "\n"
                race_block += format_session("Sprint", race['Sprint']['date'], race['Sprint']['time'], current_time) + "\n"
            else:
                if 'SecondPractice' in race:
                    race_block += format_session("SecondPractice", race['SecondPractice']['date'], race['SecondPractice']['time'], current_time) + "\n"
                if 'ThirdPractice' in race:
                    race_block += format_session("ThirdPractice", race['ThirdPractice']['date'], race['ThirdPractice']['time'], current_time) + "\n"
            
            if 'Qualifying' in race:
                race_block += format_session("Qualifying", race['Qualifying']['date'], race['Qualifying']['time'], current_time) + "\n"
            
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

        if current_chunk:
            calendar_chunks.append(current_chunk)

        # --- FETCH HISTORY AND HOOK MESSAGES ---
        print("Scanning channel history for existing bot messages...")
        calendar_messages = []
        next_gp_message = None
        
        async for msg in channel.history(limit=50, oldest_first=True):
            if msg.author == client.user:
                if "Use **Channels & Roles**" in msg.content or "React on F1 emoji" in msg.content:
                    next_gp_message = msg
                    print("-> Hooked into existing Next GP message.")
                else:
                    calendar_messages.append(msg)
                    print(f"-> Hooked into Calendar Chunk {len(calendar_messages)}.")

        # --- UPDATE CALENDAR MESSAGES ---
        for i, chunk_text in enumerate(calendar_chunks):
            if i < len(calendar_messages):
                if calendar_messages[i].content.strip() != chunk_text.strip():
                    await calendar_messages[i].edit(content=chunk_text)
                    print(f"✅ Calendar Chunk {i+1} updated.")
                else:
                    print(f"ℹ️ Calendar Chunk {i+1} unchanged.")
            else:
                new_msg = await channel.send(chunk_text)
                calendar_messages.append(new_msg)
                print(f"✅ Sent new Calendar Chunk {i+1}.")

        while len(calendar_messages) > len(calendar_chunks):
            extra_msg = calendar_messages.pop()
            try:
                await extra_msg.delete()
                print("🗑️ Deleted extra calendar message.")
            except discord.NotFound:
                pass

        # --- UPDATE NEXT GP MESSAGE ---
        if next_race:
            rules_channel = discord.utils.get(channel.guild.channels, name="rules")
            rules_mention = rules_channel.mention if rules_channel else "#rules"
            
            # Find the role f1-feed dynamically in the server's roles
            f1_role = discord.utils.get(channel.guild.roles, name="f1-feed")
            role_mention = f1_role.mention if f1_role else f"<@&{ROLE_ID}>"
            
            short_text = generate_short_msg(next_race, current_time, rules_mention, role_mention)

            # Discord edits do not change a message's position. If a new calendar
            # chunk was appended after the Next GP card, repost the card so the
            # channel remains calendar-first and Next-GP-last.
            next_gp_is_out_of_order = (
                next_gp_message
                and calendar_messages
                and next_gp_message.id < calendar_messages[-1].id
            )

            if next_gp_is_out_of_order:
                replacement = await channel.send(short_text)
                try:
                    await next_gp_message.delete()
                except discord.NotFound:
                    pass
                next_gp_message = replacement
                print("✅ Repositioned Next GP message after the calendar.")
            elif next_gp_message:
                if next_gp_message.content.strip() != short_text.strip():
                    await next_gp_message.edit(content=short_text)
                    print("✅ Next GP message updated successfully.")
                else:
                    print("ℹ️ Next GP message unchanged.")
            else:
                await channel.send(short_text)
                print("✅ Sent new next GP message block.")
        else:
            print("No upcoming races found.")

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