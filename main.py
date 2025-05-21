import requests
from bs4 import BeautifulSoup
from datetime import timedelta, datetime, timezone
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

tracked_teams = {"faze", "falcons", "spirit"}
HLTV_URL = "https://www.hltv.org/matches"


def fetch_matches(teams):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    }
    response = requests.get(HLTV_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    now = datetime.now(timezone.utc)
    matches = []

    # Находим все блоки с матчами по классу "match-bottom"
    match_blocks = soup.select("div.match-bottom")

    for block in match_blocks:
        try:
            time_elem = block.select_one("div.match-time")
            if not time_elem or "data-unix" not in time_elem.attrs:
                continue
            timestamp = int(time_elem["data-unix"]) // 1000
            match_time = datetime.fromtimestamp(timestamp, timezone.utc)

            # Фильтр по времени: только ближайшие 24 часа
            if not (now <= match_time <= now + timedelta(hours=24)):
                continue

            team1_elem = block.select_one("div.match-team.team1 div.match-teamname")
            team2_elem = block.select_one("div.match-team.team2 div.match-teamname")
            if not team1_elem or not team2_elem:
                continue

            team1 = team1_elem.text.strip().lower()
            team2 = team2_elem.text.strip().lower()

            if any(t in team1 or t in team2 for t in teams):
                matches.append(f"{match_time.strftime('%d.%m %H:%M UTC')} — {team1.title()} vs {team2.title()}")
        except Exception as e:
            print(f"Ошибка при парсинге матча: {e}")
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
