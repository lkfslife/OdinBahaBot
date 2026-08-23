import os
import re
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
    """讀取歷史推送紀錄"""
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_ids(sent_ids):
    """寫入歷史推送紀錄（最多保留 200 筆）"""
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        for post_id in list(sent_ids)[-200:]:
            f.write(f"{post_id}\n")

def get_server_banner(title):
    """精準判定伺服器與公告類型"""
    is_kr = any(k in title for k in ["韓版", "韓服", "KR", "韓"])
    is_maint = "例行維護公告" in title

    # 1. 標題同時有維護公告與韓版更新內容 (例如截圖中的：08月13日 例行維護公告、韓版 08月12日 更新內容)
    if is_maint and is_kr:
        return "[ ⚡ 奧丁神諭 ‧ 台韓更新情報 ]"

    # 2. 單純台服例行維護
    if is_maint:
        return "[ 🛠️ 奧丁神諭 ‧ 例行維護公告 ]"

    # 3. 韓服前瞻情報
    if is_kr:
        return "[ 🔮 奧丁神諭 ‧ 韓服前瞻情報 ]"

    # 4. 台服官方快訊
    return "[ 📢 奧丁神諭 ‧ 台服官方快訊 ]"

def run():
    if not WEBHOOK_URL:
        print("❌ 錯誤：找不到 DISCORD_WEBHOOK_URL")
        return

    print("🔍 開始檢查巴哈姆特哈啦板最新文章...")
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

            # 嚴格過濾：僅抓取「【情報】」或「例行維護公告」
            is_target = ("【情報】" in title) or ("例行維護公告" in title)

            if is_target and (post_id not in sent_ids):
                server_banner = get_server_banner(title)

                content = (
                    f"```ini\n"
                    f"{server_banner}\n"
                    f"```\n"
                    f"```yaml\n"
                    f"{title}\n"
                    f"```\n"
                    f"> 🔗 **傳送門**：[點此前往巴哈姆特觀看完整內容]({href})\n"
                    f"> ━━━━━━━━━━━━━━━━━━━━━━"
                )

                payload = {"content": content}
                res = requests.post(WEBHOOK_URL, json=payload)
                if res.status_code in [200, 204]:
                    print(f"✅ 成功推送 {server_banner}: {title}")
                    new_sent_ids.add(post_id)
                else:
                    print(f"❌ Webhook 推送失敗: {res.status_code}")

        save_sent_ids(new_sent_ids)
        print("✅ 檢查完成。")

    except Exception as e:
        print(f"❌ 執行時發生錯誤: {e}")

if __name__ == "__main__":
    run()