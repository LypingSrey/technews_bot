"""
Tech News Telegram Bot
----------------------
Checks tech news RSS feeds and sends new articles to your Telegram.
Runs automatically on GitHub Actions (see .github/workflows/news.yml).

Test locally without sending anything:
    python bot.py --dry-run
"""

import calendar
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

# ============================================================
#  ✏️  SETTINGS — change these any time
# ============================================================

# News sources: "Name": "RSS feed URL"
# Add a line to add a source, delete a line to remove one.
FEEDS = {
    "Tom's Hardware": "https://www.tomshardware.com/feeds/all",
    "VideoCardz": "https://videocardz.com/feed",
    "Wccftech": "https://wccftech.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "TechCrunch": "https://techcrunch.com/feed/",
    "GSMArena": "https://www.gsmarena.com/rss-news-reviews.php3",
    "9to5Mac": "https://9to5mac.com/feed/",
    "Android Authority": "https://www.androidauthority.com/feed/",
}

# Only send articles that mention at least one of these words.
# Set KEYWORDS = [] to receive EVERY article from every source.
KEYWORDS = [
    # PC hardware
    "nvidia", "geforce", "rtx", "amd", "radeon", "ryzen", "intel", "core ultra",
    "gpu", "cpu", "processor", "chip", "laptop", "pc", "motherboard", "ssd", "ram",
    # Phones
    "iphone", "ipad", "apple", "samsung", "galaxy", "pixel", "android", "ios",
    "snapdragon", "qualcomm", "mediatek", "smartphone", "phone", "xiaomi", "oneplus",
    # AI
    "ai", "openai", "chatgpt", "gemini", "claude", "llm",
]

MAX_ARTICLES_PER_RUN = 15   # most articles sent each time the bot runs
MAX_AGE_HOURS = 24          # ignore articles older than this
SUMMARY_LENGTH = 160        # characters of summary shown per article

# Category headings (first match wins, anything else goes under "💡 Tech")
CATEGORIES = [
    ("🖥️ PC & Hardware", ["nvidia", "geforce", "rtx", "amd", "radeon", "ryzen", "intel",
                          "gpu", "cpu", "processor", "motherboard", "ssd", "ram", "pc", "laptop"]),
    ("📱 Phones & Mobile", ["iphone", "ipad", "samsung", "galaxy", "pixel", "android", "ios",
                           "snapdragon", "qualcomm", "mediatek", "smartphone", "phone",
                           "xiaomi", "oneplus"]),
    ("🤖 AI", ["ai", "openai", "chatgpt", "gemini", "claude", "llm"]),
]

# ============================================================
#  Nothing below needs changing
# ============================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
SENT_FILE = Path(__file__).parent / "sent.json"
MAX_REMEMBERED = 3000
TELEGRAM_LIMIT = 4000       # Telegram allows 4096 characters per message
LOCAL_TZ = timezone(timedelta(hours=7), "Phnom Penh")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TechNewsBot/1.0)"}


def word_pattern(words):
    """Match whole words (plus plural 's'), so 'ai' doesn't match 'said'."""
    if not words:
        return None
    alternatives = "|".join(re.escape(w) for w in words)
    return re.compile(rf"\b(?:{alternatives})s?\b", re.IGNORECASE)


KEYWORD_RE = word_pattern(KEYWORDS)
CATEGORY_RES = [(name, word_pattern(words)) for name, words in CATEGORIES]


def clean_text(raw):
    """Strip HTML tags and extra spaces from a summary."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def shorten(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(".,;:") + "…"


def entry_time(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(calendar.timegm(parsed), timezone.utc)
    return datetime.now(timezone.utc)


def load_sent():
    if SENT_FILE.exists():
        try:
            return json.loads(SENT_FILE.read_text()).get("ids", [])
        except (json.JSONDecodeError, OSError):
            print("⚠️  sent.json was unreadable, starting fresh.")
    return []


def save_sent(ids):
    SENT_FILE.write_text(json.dumps({"ids": ids[-MAX_REMEMBERED:]}, indent=1))


def fetch_feed(name, url):
    """Download one feed. A broken feed is skipped, not fatal."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        print(f"✅ {name}: {len(feed.entries)} articles")
        return feed.entries
    except Exception as err:  # noqa: BLE001
        print(f"⚠️  {name}: skipped ({err})")
        return []


def collect_articles(sent_ids):
    """Return (new matching articles, ids of every new article seen)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    sent = set(sent_ids)
    articles, seen_now = [], []

    for name, url in FEEDS.items():
        for entry in fetch_feed(name, url):
            link = entry.get("link", "")
            uid = entry.get("id") or link
            if not uid or uid in sent or uid in seen_now:
                continue
            seen_now.append(uid)

            published = entry_time(entry)
            if published < cutoff:
                continue

            title = clean_text(entry.get("title", "Untitled"))
            summary = clean_text(entry.get("summary", ""))
            if KEYWORD_RE and not KEYWORD_RE.search(f"{title} {summary}"):
                continue

            articles.append({
                "title": title,
                "summary": shorten(summary, SUMMARY_LENGTH),
                "link": link,
                "source": name,
                "published": published,
            })

    articles.sort(key=lambda a: a["published"], reverse=True)
    return articles[:MAX_ARTICLES_PER_RUN], seen_now


def category_of(article):
    text = article["title"] + " " + article["summary"]
    for name, pattern in CATEGORY_RES:
        if pattern and pattern.search(text):
            return name
    return "💡 Tech"


def format_article(a):
    local = a["published"].astimezone(LOCAL_TZ).strftime("%H:%M")
    lines = [f'<b>{html.escape(a["title"], quote=False)}</b>']
    if a["summary"]:
        lines.append(html.escape(a["summary"], quote=False))
    lines.append(f'<i>{html.escape(a["source"], quote=False)} · {local}</i> — '
                 f'<a href="{html.escape(a["link"], quote=True)}">Read</a>')
    return "\n".join(lines)


def build_messages(articles):
    """Group by category and split into Telegram-sized messages."""
    groups = {}
    for a in articles:
        groups.setdefault(category_of(a), []).append(a)

    now = datetime.now(LOCAL_TZ).strftime("%a %d %b, %H:%M")
    blocks = [f"📰 <b>Tech News</b> — {now}\n{len(articles)} new article(s)"]
    order = [name for name, _ in CATEGORIES] + ["💡 Tech"]
    for cat in order:
        if cat in groups:
            blocks.append(f"<b>{html.escape(cat, quote=False)}</b>")
            blocks.extend(format_article(a) for a in groups[cat])

    messages, current = [], ""
    for block in blocks:
        if current and len(current) + len(block) + 2 > TELEGRAM_LIMIT:
            messages.append(current)
            current = block
        else:
            current = f"{current}\n\n{block}" if current else block
    if current:
        messages.append(current)
    return messages


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True},
    }, timeout=20)
    if not resp.ok:
        raise RuntimeError(f"Telegram error {resp.status_code}: {resp.text}")


def main():
    dry_run = "--dry-run" in sys.argv
    if not dry_run and (not BOT_TOKEN or not CHAT_ID):
        sys.exit("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID. "
                 "Add them as GitHub Secrets (see README).")

    sent_ids = load_sent()
    articles, seen_now = collect_articles(sent_ids)
    print(f"\n{len(articles)} article(s) to send.")

    if articles:
        for message in build_messages(articles):
            if dry_run:
                print("\n" + "-" * 50 + "\n" + message)
            else:
                send_telegram(message)
                time.sleep(1)

    if not dry_run:
        save_sent(sent_ids + seen_now)
    print("Done.")


if __name__ == "__main__":
    main()
