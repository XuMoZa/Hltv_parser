import requests
from bs4 import BeautifulSoup
from datetime import timedelta, datetime, timezone
import os
import cloudscraper
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

tracked_teams = {"faze", "falcons", "spirit"}
HLTV_URL = "https://www.hltv.org/matches"
keyboard = [
        [InlineKeyboardButton("Показать матчи", callback_data="matches")],
        [InlineKeyboardButton("Список команд", callback_data="list")]
    ]
reply_markup = InlineKeyboardMarkup(keyboard)

def fetch_matches(teams):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.hltv.org/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Cache-Control": "max-age=0",
        "Priority": "u=0, i"
}
    print("Fetching matches...")
    scraper = cloudscraper.create_scraper()
    response = scraper.get(HLTV_URL)
    if response.status_code == 403:
        return ["Матчи не были загружены, попробуйте позже."]
    soup = BeautifulSoup(response.text, "html.parser")

    now = datetime.now(timezone.utc)
    matches = []

    match_blocks = soup.select("div.matches-chronologically.matches-chronologically-hide div.match-bottom")
    print(match_blocks)
    for block in match_blocks:
        try:
            time_elem = block.select_one("div.match-time")
            if not time_elem or "data-unix" not in time_elem.attrs:
                continue
            timestamp = int(time_elem["data-unix"]) // 1000
            match_time = datetime.fromtimestamp(timestamp, timezone.utc)

            team1_elem = block.select_one("div.match-team.team1 div.match-teamname")
            team2_elem = block.select_one("div.match-team.team2 div.match-teamname")
            if not team1_elem or not team2_elem:
                continue

            team1 = team1_elem.text.strip().lower()
            team2 = team2_elem.text.strip().lower()

            if any(t == team1 or t == team2 for t in teams):
                matches.append(f"{(match_time + timedelta(hours=3)).strftime('%d.%m %H:%M UTC')} — {team1.title()} vs {team2.title()}")
        except Exception as e:
            print(f"Ошибка при парсинге матча: {e}")
            continue
    return matches

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "matches":
        matches_list = fetch_matches(tracked_teams)
        text = "Ближайшие матчи:\n\n" + "\n".join(matches_list) + "\n\n" + "Для просмотра моих возможностей напишите /start" if matches_list else "В ближайшие 24 часа матчей отслеживаемых команд нет."+ "\n\n" + "Для просмотра моих возможностей напишите /start"
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif query.data == "list":
        if tracked_teams:
            await query.edit_message_text("Отслеживаемые команды:\n" + "\n".join(sorted(tracked_teams)) + "\n\n" + "Для просмотра моих возможностей напишите /start", reply_markup=reply_markup)
        else:
            await query.edit_message_text("Пока что ни одна команда не отслеживается."+ "\n\n" + "Для просмотра моих возможностей напишите /start", reply_markup = reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Привет! Я отслеживаю матчи.\nНажми кнопку ниже или используй команды:\n/matches — ближайшие игры\n/add <команда> — добавить команду\n/list — список команд\n/remove <команда> — удалить команду",
        reply_markup=reply_markup
    )

async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matches = fetch_matches(tracked_teams)
    if matches:
        await update.message.reply_text("Ближайшие матчи:\n\n" + "\n".join(matches) + "\n\n" + "Для просмотра моих возможностей напишите /start", reply_markup = reply_markup)
    else:
        await update.message.reply_text("В ближайшие 24 часа матчей отслеживаемых команд нет.\n\n"+ "\n\n" + "Для просмотра моих возможностей напишите /start", reply_markup = reply_markup)

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используй: /add <команда>")
        return
    team = ""
    for arg in context.args:
        if arg == context.args[0]:
            team = context.args[0].lower()
        else:
            team = team + " " + (arg.lower())
    if team in tracked_teams:
        await update.message.reply_text(f"Команда '{team}' уже в списке отслеживаемых.", reply_markup=reply_markup)
    else:
        tracked_teams.add(team)
        await update.message.reply_text(f"Команда '{team}' добавлена!", reply_markup=reply_markup)

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        if tracked_teams:
            await update.message.reply_text("Отслеживаемые команды:\n" + "\n".join(
                sorted(tracked_teams)) + "\n\n" + "Для удаления команды напишите /remove <название команды>")
        else:
            await update.message.reply_text(
                "Пока что ни одна команда не отслеживается." + "\n\n" + "Для просмотра моих возможностей напишите /start", reply_markup = reply_markup)
    else:
        team = ""
        for arg in context.args:
            if arg == context.args[0]:
                team = context.args[0].lower()
            else:
                team = team + " " + (arg.lower())
        if team in tracked_teams:
            tracked_teams.discard(team)
            await update.message.reply_text(f"Команда '{team}' была удалена!", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"Команда '{team}' не была найдена." + "\n\n" + "Для удаления команды напишите /remove <название команды>", reply_markup=reply_markup)

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

    app = ApplicationBuilder().token(os.environ.get("token")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matches", matches))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
