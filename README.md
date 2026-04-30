a# F1 Bot & Web Dashboard

F1 schedule project shows the Formula 1 calendar and the upcoming races countdown live in real-time. This project combines a dynamic Discord bot with a dedicated web interface to serve up the latest from the grid.

## Project Overview

This repository provides everything needed to run a Formula 1 Discord bot and an accompanying web platform. 
* **Bot Engine:** The core functionality is driven by the `f1_bot.py` script
* **[Web](https://f1.trionine.xyz/) Frontend:** The visual layout is handled by `index.html`  

## Requirements

* **`discord.py`**: For full integration with the Discord API
* **`Flask`**: To serve the web application and handle backend routing
* **`requests`**: For fetching external F1 data endpoints
* **`python-dotenv`**: To securely load environment variables and bot tokens

## Installation & Usage

### 1. Local Setup
Ensure you have Python installed, then install the required libraries:
```
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory to store your sensitive credentials (thanks to `python-dotenv`):
```env
DISCORD_TOKEN=your_bot_token_here
```

### 3. Execution
To start the bot locally, run the main Python file:
```
python f1_bot.py
```
