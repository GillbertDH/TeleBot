import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

URL = "https://aicollege.knu.ac.kr/bbs/board.php?bo_table=sub6_1_a&lang=kor"
SEEN_FILE = "seen.json"
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def fetch_posts():
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(URL, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    posts = []
    for a in soup.select("td.td_subject a"):
        link = a["href"]
        query = parse_qs(urlparse(link).query)
        if "wr_id" not in query:
            continue
        posts.append({
            "id": query["wr_id"][0],
            "title": a.get_text(strip=True),
            "link": link,
        })
    return posts


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return None
    with open(SEEN_FILE, encoding="utf-8") as f:
        return set(json.load(f))


def save_seen(ids):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, indent=2)


def send_telegram(text):
    """보내기에 성공하면 True, 실패하면 False를 돌려준다"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
        return res.ok
    except requests.RequestException:
        return False


def main():
    posts = fetch_posts()
    seen = load_seen()

    if seen is None:
        save_seen({p["id"] for p in posts})
        print(f"첫 실행: 공지 {len(posts)}개를 본 글로 저장했어요.")
        return

    new_posts = [p for p in posts if p["id"] not in seen]
    new_posts.reverse()  # 오래된 글부터 보내기

    for p in new_posts:
        message = f"📢 새 공지\n\n{p['title']}\n\n{p['link']}"
        if send_telegram(message):
            seen.add(p["id"])  # 성공한 글만 본 글로 기록
            print("보냄:", p["title"])
        else:
            print("전송 실패 (다음에 다시 시도):", p["title"])

    save_seen(seen)
    if not new_posts:
        print("새 공지 없음")


if __name__ == "__main__":
    main()