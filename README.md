# F1 Live Dashboard

A Formula 1 season dashboard with live schedule data, countdowns, standings, qualifying, and results. The dashboard serves a static frontend through Flask and merges race calendar data from Jolpica with session timing data from OpenF1.

## Features

- Live race calendar with upcoming and past sessions
- Countdown to the next race
- Current driver standings, results, and qualifying grid
- Optional relative-time view for session timestamps
- Discord bot that can post the schedule to a channel

## Project Layout

- `index.html`, `styles.css`, `app.js`: browser dashboard
- `server.py`: Flask app that serves the site and proxies API requests
- `f1_bot.py`: Discord bot that posts F1 schedule updates
- `requirements.txt`: Python dependencies

## Prerequisites

- Python 3.10 or newer
- A virtual environment is recommended
- Internet access for the OpenF1 and Jolpica API requests

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run the dashboard

```bash
python server.py
```

Then open `http://localhost:5000` in your browser.

## Run the Discord bot

1. Set `DISCORD_TOKEN` in a local `.env` file.
2. Update the channel and role IDs in `f1_bot.py` if needed.
3. Start the bot:

```bash
python f1_bot.py
```

## API endpoints

The Flask server proxies these endpoints:

- `/api/openf1/sessions`
- `/api/jolpica/schedule`
- `/api/jolpica/results`
- `/api/jolpica/standings`
- `/api/jolpica/qualifying`

## Notes

- The repository includes local test scripts for schedule merge behavior and API parsing.
- Secrets should stay in `.env`; the file is ignored by git.
