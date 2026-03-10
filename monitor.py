#!/usr/bin/env python3
import os
import asyncio
import requests
from datetime import datetime, timedelta, timezone
from twscrape import API as TwscrapeAPI

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
X_USERNAME = os.environ.get("X_SCRAPE_USERNAME", "")
X_PASSWORD = os.environ.get("X_SCRAPE_PASSWORD", "")

TARGET_USERNAMES = ["kangminlee", "ChanceSon1226", "AdamLowisz"]


async def scrape_user_tweets(api, username, since):
    tweets = []
    try:
        query = f"from:{username} since:{since.strftime('%Y-%m-%d')}"
        async for tweet in api.search(query, limit=50):
            tweets.append(tweet)
    except Exception as e:
        print(f"@{username} 수집 오류: {e}")
    return tweets


def format_summary(username, tweets):
    if not tweets:
        return f"📭 @{username}: 최근 24시간 활동 없음\n"

    originals = []
    replies = []
    retweets = []
    quotes = []

    for tweet in tweets:
        raw = tweet.rawContent if hasattr(tweet, "rawContent") else str(tweet)
        if hasattr(tweet, "inReplyToUser") and tweet.inReplyToUser:
            replies.append(raw)
        elif raw.startswith("RT @"):
            retweets.append(raw)
        elif hasattr(tweet, "quotedTweet") and tweet.quotedTweet:
            quotes.append(raw)
        else:
            originals.append(raw)

    lines = [
        f"\n👤 @{username}",
        f"총 활동: {len(tweets)}건",
        f"├ 원본 트윗: {len(originals)}건",
        f"├ 답글: {len(replies)}건",
        f"├ 리포스트: {len(retweets)}건",
        f"└ 인용 트윗: {len(quotes)}건",
    ]

    if originals:
        lines.append("\n📝 주요 트윗:")
        for t in originals[:3]:
            text = t[:150].replace("\n", " ")
            lines.append(f"• {text}")

    if replies:
        lines.append("\n💬 주요 답글:")
        for t in replies[:3]:
            text = t[:150].replace("\n", " ")
            lines.append(f"• {text}")

    if retweets:
        lines.append(f"\n🔄 리포스트 {len(retweets)}건:")
        for t in retweets[:3]:
            text = t[:150].replace("\n", " ")
            lines.append(f"• {text}")

    if quotes:
        lines.append(f"\n💡 인용 트윗 {len(quotes)}건:")
        for t in quotes[:3]:
            text = t[:150].replace("\n", " ")
            lines.append(f"• {text}")

    lines.append("\n" + "─" * 30)
    return "\n".join(lines)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(text) > 4096:
        chunks = [text[i:i + 4096] for i in range(0, len(text), 4096)]
        for chunk in chunks:
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "disable_web_page_preview": True,
            }).raise_for_status()
    else:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        }).raise_for_status()


async def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    date_str = now.strftime("%Y-%m-%d")

    api = TwscrapeAPI()

    if X_USERNAME and X_PASSWORD:
        await api.pool.add_account(X_USERNAME, X_PASSWORD, "", "")
        await api.pool.login_all()

    report_parts = [
        f"📋 Twitter 일일 리포트 ({date_str})",
        "=" * 30,
    ]

    for username in TARGET_USERNAMES:
        print(f"@{username} 수집 중...")
        tweets = await scrape_user_tweets(api, username, since)
        print(f"  → {len(tweets)}건")
        report_parts.append(format_summary(username, tweets))

    report = "\n".join(report_parts)
    print(report)

    send_telegram(report)
    print("텔레그램 전송 완료!")


if __name__ == "__main__":
    asyncio.run(main())
