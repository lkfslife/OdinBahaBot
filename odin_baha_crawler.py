import os
import re
from turtle import title
import requests
from bs4 import BeautifulSoup

# 原生支援讀取 local .env
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BOARD_URL = "https://forum.gamer.com.tw/B.php?bsn=38601"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://forum.gamer.com.tw/"
}
RECORD_FILE = "sent_ids.txt"

def load_sent_ids():
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_ids(sent_ids):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        for post_id in list(sent_ids)[-200:]:
            f.write(f"{post_id}\n")

def fetch_post_preview(url):
    """進入文章內頁抓取前 120 字內文摘要"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            # 巴哈文章內容主區塊
            article_body = soup.select_one(".c-article__content")
            if article_body:
                text = article_body.get_text(separator=" ", strip=True)
                # 清除多餘空白並截取前 120 字
                text = re.sub(r"\s+", " ", text)
                if len(text) > 120:
                    return text[:120] + "..."
                return text
    except Exception as e:
        print(f"[-] 抓取文章內文失敗: {e}")
    return "點擊下方傳送門查看完整內容。"

def run():
    if not WEBHOOK_URL:
        print("❌ 錯誤：找不到 DISCORD_WEBHOOK_URL")
        return

    print("🔍 開始檢查巴哈姆特哈啦板情報...")
    try:
        response = requests.get(BOARD_URL, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ 抓取失敗，狀態碼: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.select(".b-list__row")
        sent_ids = load_sent_ids()
        new_sent_ids = set(sent_ids)
        
        for art in reversed(articles):
            title_tag = art.select_one(".b-list__main__title")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            href = "https://forum.gamer.com.tw/" + title_tag.get("href")

            match = re.search(r"snA=(\d+)", href)
            if not match:
                continue
            post_id = match.group(1)

            if ("情報" in title) and (post_id not in sent_ids):
                # 判斷是韓服前瞻還是台服情報
                is_kr = any(k in title for k in ["韓版", "韓服", "KR", "韓測"])
                
                if is_kr:
                    server_tag = "[ ⚡ 奧丁神諭 ‧ 韓服前瞻情報 ]"
                else:
                    server_tag = "[ ⚡ 奧丁神諭 ‧ 台服官方快訊 ]"

                # 組裝 Discord Markdown 排版
                content = (
                    f"```ini\n"
                    f"{server_tag}\n"
                    f"```\n"
                    f"📜 **文章標題**\n"
                    f"```yaml\n"
                    f"{title}\n"
                    f"```\n"
                    f"> 🔗 **傳送門**：[點此前往巴哈姆特觀看完整內容]({href})\n"
                    f"> ━━━━━━━━━━━━━━━━━━━━━━"
                )

                payload = {"content": content}
                res = requests.post(WEBHOOK_URL, json=payload)
                if res.status_code in [200, 204]:
                    print(f"✅ 成功推送 ({'韓服' if is_kr else '台服'}): {title}")
                    new_sent_ids.add(post_id)
                else:
                    print(f"❌ Webhook 推送失敗: {res.status_code}")

        save_sent_ids(new_sent_ids)
        print("✅ 檢查完成。")

    except Exception as e:
        print(f"❌ 執行時發生錯誤: {e}")

if __name__ == "__main__":
    run()