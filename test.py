from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import os
import requests

# إعداد خيارات المتصفح
options = Options()
options.add_argument("--headless")  # تشغيل المتصفح في وضع عدم العرض
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# إعدادات البوت
BOT_TOKEN = "8002339915:AAEwhTyAdVBqzRshhaWlKVTbdH-C3iQR1oE"  # استبدل بـ Token الخاص بالبوت
CHAT_ID = "1221982749"      # استبدل بـ Chat ID الخاص بك

def send_telegram_message(message):
    """إرسال رسالة إلى تليجرام"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram notification sent successfully.")
        else:
            print(f"Failed to send Telegram notification: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

# وظيفة للتحقق من الكروت الجديدة
def check_for_new_cards():
    driver = webdriver.Chrome(options=options)
    driver.get("https://webook.com/ar/explore?tag=football&category=sports-events")
    wait = WebDriverWait(driver, 20)

    # التعامل مع زر "عرض المزيد"
    max_clicks = 10  # الحد الأقصى لعدد النقرات
    clicks = 0

    while clicks < max_clicks:
        try:
            # العثور على زر "عرض المزيد" باستخدام محدد CSS
            load_more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.py-12.text-center button.w-full.max-w-\\[200px\\]")))
            previous_count = len(driver.find_elements(By.CSS_SELECTOR, "div.mx-auto.w-full > a"))
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
            time.sleep(1)  # انتظار بسيط بعد التمرير
            driver.execute_script("arguments[0].click();", load_more_button)
            print(f"Clicked 'Load More' button {clicks + 1} times")
            time.sleep(5)  # انتظار لتحميل المزيد من العناصر
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "div.mx-auto.w-full > a"))

            if current_count == previous_count:
                print("No new items loaded")
                break

            clicks += 1
        except Exception as e:
            print("No more 'Load More' button or an error occurred:", e)
            break

    # استخراج البطاقات بعد تحميل جميع العناصر
    cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.mx-auto.w-full > a")))
    print(f"Number of cards extracted {len(cards)}")

    # تحميل العناوين المخزنة مسبقًا من ملف JSON
    if os.path.exists("matches.json"):
        with open("matches.json", "r", encoding="utf-8") as f:
            stored_matches = json.load(f)
    else:
        stored_matches = []

    # استخراج العناوين
    matches = stored_matches  # قائمة تحتوي على العناوين المخزنة مسبقًا
    new_matches = []  # قائمة للمباريات الجديدة
    for card in cards:
        try:
            title_el = card.find_element(By.CSS_SELECTOR, "p.line-clamp-2")
            title = title_el.text.strip()
            if title:
                match = {"title": title}
                if match not in matches:  # تحقق إذا كانت المباراة جديدة
                    new_matches.append(match)
                    matches.append(match)  # أضف المباراة إلى القائمة المخزنة
        except:
            continue

    # حفظ النتائج في ملف JSON
    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    driver.quit()

    return new_matches

# التحقق بشكل دوري كل 10 دقائق
while True:
    print("Checking for new cards...")
    new_matches = check_for_new_cards()
    if new_matches:
        print(f"New matches found: {len(new_matches)}")
        for match in new_matches:
            print(f"- {match['title']}")
            send_telegram_message(f"New match found: {match['title']}")
    else:
        print("No new matches found.")
    
    # الانتظار لمدة 1 دقائق
    time.sleep(60)  # 60 ثانية = 1 دقائق


