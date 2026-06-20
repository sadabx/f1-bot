# Serverless F1 Discord Bot and API Scraper

A serverless Discord bot and schedule generator for Formula 1. The script fetches F1 calendar data, structures it, and updates Discord message blocks. It runs on a scheduled pipeline using GitHub Actions.

Web Dashboard: https://f1.trionine.xyz/

## Repository Structure

- f1_bot.py: Discord bot script that reads the schedule cache and updates the Discord channel.
- update_api.py: Script that downloads the latest F1 calendar and caches it locally.
- requirements.txt: List of python package dependencies.
- .github/workflows/update_api.yml: Scrapes and commits F1 schedule data every 30 minutes.
- .github/workflows/run_bot.yml: Runs the Discord bot after update_api finishes.

## Local Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a .env file in the root directory:
   ```env
   DISCORD_TOKEN=your_discord_bot_token
   ```

## Running Locally

1. Update the local API cache:
   ```bash
   python update_api.py
   ```

2. Start the Discord bot runner:
   ```bash
   python f1_bot.py
   ```

## GitHub Actions Workflows

- Update F1 API: Runs update_api.py on a schedule (every 30 minutes) or on push to the main branch. Any changes to the calendar are committed back to the repository.
- Run Serverless F1 Discord Bot: Chained to trigger automatically on completion of the Update F1 API workflow. It runs f1_bot.py using the latest cached calendar file.
