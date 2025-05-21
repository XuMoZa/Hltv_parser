import requests
from bs4 import BeautifulSoup
from datetime import timedelta, datetime, timezone
import os
import cloudscraper
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

tracked_teams = {"faze", "falcons", "spirit"}
HLTV_URL = "https://www.hltv.org/matches"


def fetch_matches(teams):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://www.hltv.org/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Cache-Control": "max-age=0",
        "Cookie": "__cflb=0H28vvhCcx7neqKqegLg3bDFqvDd36FWtMXV4585HVW; MatchFilter={%22active%22:false%2C%22live%22:false%2C%22stars%22:1%2C%22lan%22:false%2C%22teams%22:[]}; cf_clearance=tB6MRjsDAv6.B7IsrAUqVON_zt6ZiKESwxE0ajPgaww-1747830360-1.2.1.1-kM0706qWJHowoaRpgpvgYdhwZ1VqjMDF2vfQ5PsvFK.tE1TINndz0wOa0kVmGBOHk4bVG8OIVNPs0bXxQmbpnH7Bc9COybszEPyGczpa8A7RZ5_T2o2zfBDQLFZNhQtqTnT4BKQpJYJpYHQBhDVm7CTPvBRqcEXaN3HTkpTOyN_O__SVUmfiwdUCSW5r8DUD08_Jd5JzFNhu2Vw8o4MbJWc.ztC2E.TVlehLCZRU6XDxO4dO8FMs_kY51nWG1aMJ5rpR4OuvyMljuLON_C2IezKne5dGID7Bif4Zvh9VEabpkeK7I_utz0TrbE9GuiLJ2i0P4KIPfsA3QJZMNwbOUdcoam3Ey4puwwrzgE36jf4; CookieConsent={stamp:%278F3Qk+9gom759VEQKiFKB+DftznsdMGhPXi01vgm66AMiBdB4Kv+/A==%27%2Cnecessary:true%2Cpreferences:true%2Cstatistics:true%2Cmarketing:true%2Cmethod:%27explicit%27%2Cver:1%2Cutc:1747830363198%2Cregion:%27by%27}; _fbp=fb.1.1747830395231.38489471453328275; _sharedid=4908594a-3963-4eee-a54f-c6334fe2066e; _sharedid_cst=zix7LPQsHA%3D%3D; _lr_env_src_ats=false; _ga_525WEYQTV9=GS2.1.s1747830398$o1$g0$t1747830398$j60$l0$h0$dXSv_Xwwl_b_bLcM-HmFoeqr0vDnadiguLw; _ga=GA1.1.438590886.1747830399; __gads=ID=dd941af737606c91:T=1747830372:RT=1747830372:S=ALNI_MbURAdAIptqg2RUcfJCTKnZ6sGcFw; __gpi=UID=000010c9b8d2b501:T=1747830372:RT=1747830372:S=ALNI_MZhq62yo6vbnUOibgJLk15vN4R7EQ; __eoi=ID=c9f75795bd1f4eb7:T=1747830372:RT=1747830372:S=AA-AfjaS3-P5rVYAHLHmkyIHdTLf; cto_bundle=EpyRTl9DWUdrJTJGQyUyQlhzcWhialZubk9UR1NnMGdnMXlUQXRJVU1WMnVRc0dyNXJUWkVIRm1HUlozNFE3VDlDclRJQk5TOUtyMWlmZHhxNXhiZHdvWHcxS0Y0TlFRNE54YmYlMkZUUGVQSDRtOU5WVmdhQyUyQlBjUjB2Z0hnY3ZySnc5WTJXSEFFMjBQa2ZRTEZJWkVIeDBCZEVHWXM2dyUzRCUzRA; __cf_bm=J6lFNqlp1jAc6QVAvNAQoCnn8KlQdYxlAgHIv1VeHCA-1747834644-1.0.1.1-yP6Tg9_.RNHJhhYWoq79Rg3okL61NKQxPegcEkwgj81Rzuf2RLNs0TqzTxSgFJbBDFiXNgJ.BwYbFx_.eEiAd1zJyWxa07hAVZPSyDkzX4U",
        "Priority": "u=0, i"
}
    print("Fetching matches...")
    scraper = cloudscraper.create_scraper()
    response = scraper.get(HLTV_URL)
    print(response)
    soup = BeautifulSoup(response.text, "html.parser")

    now = datetime.now(timezone.utc)
    matches = []

    # Находим все блоки с матчами по классу "match-bottom"
    match_blocks = soup.select("div.match")
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

            if any(t in team1 or t in team2 for t in teams):
                matches.append(f"{(match_time + timedelta(hours=3)).strftime('%d.%m %H:%M UTC')} — {team1.title()} vs {team2.title()}")
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
