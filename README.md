# 📰 Tech News Telegram Bot

Sends you the latest news on NVIDIA, AMD, Intel, phones, and AI on Telegram every 3 hours. It runs for free on GitHub, so your computer can stay off.

**What's in this folder**

| File | What it does |
|---|---|
| `bot.py` | The bot. Reads news sites and sends new articles to you |
| `requirements.txt` | Lists the Python packages the bot needs |
| `.github/workflows/news.yml` | Tells GitHub to run the bot every 3 hours |

Setup takes about 15 minutes. Do the steps in order.

---

## Step 1: Create your bot (2 min)

1. Open Telegram and search for **@BotFather** (it has a blue check mark).
2. Send `/newbot`.
3. Give the bot a name, for example `My Tech News`.
4. Give it a username that ends in `bot`, for example `lyping_technews_bot`.
5. BotFather replies with a **token** that looks like this:
   `7123456789:AAHk3xYz-abcdEFGHijklMNOP`
   Copy it and keep it private. Anyone who has it can control your bot.

## Step 2: Get your chat ID (2 min)

1. Search for your new bot in Telegram, open it, and press **Start** (or send "hi").
2. In your browser, open this link after replacing `YOUR_TOKEN` with your token:
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. Look for `"chat":{"id":123456789`. That number is your **chat ID**.

> If the page shows `"result":[]`, send your bot another message and refresh the page.

## Step 3: Create a GitHub repository (3 min)

1. Sign up for free at [github.com](https://github.com).
2. Click **+** (top right) → **New repository**.
3. Name it `tech-news-bot`, choose **Private**, and click **Create repository**.

## Step 4: Upload the files (3 min)

1. In your new repository, click **uploading an existing file**, or go to **Add file** → **Upload files**.
2. Drag in `bot.py`, `requirements.txt`, and `README.md`, then click **Commit changes**.
3. Create the schedule file. Folders that start with a dot are often hidden on computers, so create this one by hand:
   - Click **Add file** → **Create new file**.
   - In the name box, type exactly `.github/workflows/news.yml`. The slashes create the folders.
   - Open `news.yml` from this folder, copy everything in it, and paste it into the big box.
   - Click **Commit changes**.

## Step 5: Add your secrets (2 min)

Your token and chat ID go here instead of in the code, so nobody can see them.

1. In your repository, go to **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret** and add:
   - Name: `TELEGRAM_BOT_TOKEN`, Secret: your token from Step 1
3. Click **New repository secret** again and add:
   - Name: `TELEGRAM_CHAT_ID`, Secret: your number from Step 2

Type the names exactly as shown, in capital letters.

## Step 6: Test it now (1 min)

1. Click the **Actions** tab at the top of your repository.
2. Click **Tech News Bot** on the left.
3. Click **Run workflow** → **Run workflow**.
4. Wait about 30 seconds. A green ✅ means it worked, so check Telegram.

From now on, the bot runs by itself every 3 hours: 7:00, 10:00, 13:00, 16:00, 19:00, 22:00, 01:00, and 04:00 Phnom Penh time.

> GitHub sometimes starts scheduled runs 5–30 minutes late. That's normal.

---

## Changing things later

All the settings are at the top of `bot.py`. To edit on GitHub, open `bot.py`, click the ✏️ pencil icon, make your change, and click **Commit changes**.

**Add a news source.** Add a line inside `FEEDS`:
```python
    "Engadget": "https://www.engadget.com/rss.xml",
```
Most news sites have an RSS feed. Search for "site name RSS feed" to find it.

**Remove a news source.** Delete its line.

**Change topics.** Add or remove words in `KEYWORDS`. Use lowercase, and put each word in quotes with a comma after it:
```python
    "tesla", "spacex", "nintendo",
```
To get every article with no filtering, change it to `KEYWORDS = []`.

**Get more or fewer articles.** Change `MAX_ARTICLES_PER_RUN = 15`.

**Change how often it runs.** In `.github/workflows/news.yml`, change the `cron` line:

| You want | Use |
|---|---|
| Every 3 hours (default) | `"0 */3 * * *"` |
| Every 6 hours | `"0 */6 * * *"` |
| Once a day at 8:00 AM Phnom Penh | `"0 1 * * *"` |
| 8:00 AM and 8:00 PM Phnom Penh | `"0 1,13 * * *"` |

These times are in UTC, which is Phnom Penh time minus 7 hours.

---

## If something goes wrong

On the **Actions** tab, click the red ❌ run and open the failed step to read the error.

| Error message | Fix |
|---|---|
| `Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID` | The secrets are missing or misspelled. Redo Step 5. |
| `Telegram error 401: Unauthorized` | The token is wrong. Copy it again from @BotFather. |
| `Telegram error 400: chat not found` | The chat ID is wrong, or you haven't pressed **Start** in your bot. |
| `Telegram error 403: bot was blocked by the user` | You blocked the bot. Open it in Telegram and press **Restart**. |
| `Permission denied` or `403` on the "Remember sent articles" step | Go to **Settings** → **Actions** → **General** → **Workflow permissions**, choose **Read and write permissions**, and click **Save**. |
| `⚠️ SomeSite: skipped` in the log | That site's feed was down or changed. The bot still sends news from the others. Remove or replace that feed if it keeps happening. |
| The run succeeds but no message arrives | No new articles matched your keywords since the last run. Add more keywords, or wait for the next run. |

**The first run sends up to 15 articles.** After that, you only get articles published since the last run.

**The file `sent.json` appears in your repository.** That's the bot's memory of what it already sent. Leave it there.

---

## Test on your own computer (optional)

If you have Python installed, you can preview messages without sending anything:
```
pip install -r requirements.txt
python bot.py --dry-run
```
