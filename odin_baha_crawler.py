import os
import re
import requests
from bs4 import BeautifulSoup

# 原生支援讀取 local .env（方便本地手動測試，GitHub Actions 會自動讀取 Secret）
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
    """讀取歷史推送紀錄"""
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_ids(sent_ids):
    """寫入歷史推送紀錄（最多保留 200 筆，避免檔案過大）"""
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        for post_id in list(sent_ids)[-200:]:
            f.write(f"{post_id}\n")

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
        
        # 反向迭代：由較舊的文章開始推送到最新文章，符合聊天室時序
        for art in reversed(articles):
            title_tag = art.select_one(".b-list__main__title")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            href = "https://forum.gamer.com.tw/" + title_tag.get("href")

            # 從網址解析出唯一的文章編號 snA (例如 snA=6188)
            match = re.search(r"snA=(\d+)", href)
            if not match:
                continue
            post_id = match.group(1)

            # 篩選情報標籤且尚未推送過
            if ("情報" in title) and (post_id not in sent_ids):
                payload = {
                    "content": f"📢 **【奧丁情報通知】**\n**標題**：{title}\n**傳送門**：{href}"
                }
                res = requests.post(WEBHOOK_URL, json=payload)
                if res.status_code in [200, 204]:
                    print(f"✅ 成功推送: {title}")
                    new_sent_ids.add(post_id)
                else:
                    print(f"❌ Webhook 推送失敗: {res.status_code}")

        # 儲存更新後的 ID 紀錄
        save_sent_ids(new_sent_ids)
        print("✅ 檢查完成。")

    except Exception as e:
        print(f"❌ 執行時發生錯誤: {e}")

if __name__ == "__main__":
    run()