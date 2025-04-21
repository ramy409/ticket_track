import scrapy
import json
import os
import requests

BOT_TOKEN = "ضع_التوكن_هنا"
CHAT_ID = "ضع_اليوزر_ID_هنا"

class WebookTicketsSpider(scrapy.Spider):
    name = "webook"
    start_urls = ["https://resell.webook.com/ar"]

    def parse(self, response):
        matches = response.css('.line-clamp-2::text').getall()
        matches = [match.strip() for match in matches if match.strip()]

        known_matches_path = "known_matches.json"
        if os.path.exists(known_matches_path):
            with open(known_matches_path, "r", encoding="utf-8") as f:
                known_matches = json.load(f)
        else:
            known_matches = []

        new_matches = [m for m in matches if m not in known_matches]

        if new_matches:
            self.send_telegram_alert("🎟️ مباريات جديدة نزلت:
" + "\n".join(new_matches))
            with open(known_matches_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)
        else:
            self.log("لا توجد مباريات جديدة حالياً.")

    def send_telegram_alert(self, message):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        try:
            requests.post(url, data=data)
        except Exception as e:
            self.log(f"فشل إرسال الإشعار: {e}")
