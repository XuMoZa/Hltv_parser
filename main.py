import requests
from bs4 import BeautifulSoup
from datetime import timedelta
import datetime
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

tracked_teams = {"faze", "falcons", "spirit"}
HLTV_URL = "https://www.hltv.org/matches"

def fetch_matches(teams):
    response = requests.get(HLTV_URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, "html.parser")
    now = datetime.datetime.now(datetime.UTC)
    matches = []

    for match in soup.select("a.match"):
        try:
            timestamp = int(match.select_one(".matchTime")["data-unix"]) // 1000
            match_time = datetime.datetime.fromtimestamp(timestamp=timestamp, tz=datetime.UTC)
            if not now <= match_time <= now + timedelta(hours=24):
                continue

            team1 = match.select_one(".team1 .team").text.strip().lower()
            team2 = match.select_one(".team2 .team").text.strip().lower()

            for t in teams:
                if t in team1 or t in team2:
                    matches.append(f"{match_time.strftime('%d.%m %H:%M UTC')} — {team1.title()} vs {team2.title()}")
                    break
        except:
            continue
    return matches

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я отслеживаю матчи. Напиши /matches чтобы узнать ближайшие игры.")

async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = fetch_matches(tracked_teams)
    if matches:
        await update.message.reply_text("Ближайшие матчи:\n\n" + "\n".join(matches))
    else:
        await update.message.reply_text("В ближайшие 24 часа матчей отслеживаемых команд нет.")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используй: /add <команда>")
        return
    team = context.args[0].lower()
    tracked_teams.add(team)
    await update.message.reply_text(f"Команда '{team}' добавлена!")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

def main():
    threading.Thread(target=run_server, daemon=True).start()

    app = ApplicationBuilder().token(os.getenv("YOUR_TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matches", matches))
    app.add_handler(CommandHandler("add", add))
    app.run_polling()

if __name__ == "__main__":
    main()
