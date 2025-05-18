import time
import json
import logging
import os
import requests
from threading import Thread
from datetime import datetime
from flask import Flask, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from contextlib import contextmanager

# ====== إعداد نظام التسجيل ======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tickets_checker.log"),
        logging.StreamHandler()
    ]
)

# ====== إعدادات المحددات CSS ======
SELECTORS = {
    'cards': "div.mx-auto.w-full > a",
    'title': "p.line-clamp-2",
    'load_more': "//button[contains(text(),'عرض المزيد')]"
}

class TicketsMonitor:
    def __init__(self, url, bot_token=None, chat_id=None):
        self.url = url
        # استخدام متغيرات بيئية إذا لم يتم تمرير القيم
        self.bot_token = bot_token or os.environ.get("BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("CHAT_ID")
        self.matches = self._load_matches()
        self.last_check_time = None
        self.new_matches = set()  # لتتبع المباريات الجديدة للعرض في الواجهة
    
    def _load_matches(self):
        try:
            with open("matches.json", "r") as f:
                return set(json.load(f))
        except Exception as e:
            logging.warning(f"لم يتم العثور على ملف المباريات المخزنة: {e}")
            return set()
    
    def _save_matches(self):
        try:
            with open("matches.json", "w") as f:
                json.dump(list(self.matches), f)
            logging.info(f"تم حفظ {len(self.matches)} مباراة في الملف")
        except Exception as e:
            logging.error(f"خطأ في حفظ المباريات: {e}")
    
    def send_notification(self, message):
        if not self.bot_token or not self.chat_id:
            logging.error("تعذر إرسال الإشعار: BOT_TOKEN أو CHAT_ID غير محدد")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message}
        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                logging.info(f"تم إرسال الإشعار بنجاح: {message[:50]}...")
                return True
            else:
                logging.error(f"فشل في إرسال الإشعار. الرد: {response.text}")
                return False
        except Exception as e:
            logging.error(f"خطأ في إرسال الإشعار: {e}")
            return False
    
    @contextmanager
    def _get_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(options=options)
        try:
            yield driver
        finally:
            driver.quit()
    
    def fetch_new_matches(self):
        logging.info(f"بدء فحص المباريات على {self.url}")
        self.last_check_time = datetime.now()
        self.new_matches = set()  # إعادة تعيين المباريات الجديدة
    
        with self._get_driver() as driver:
            try:
            # إضافة تأخير أولي للتأكد من تحميل الصفحة بالكامل
                driver.get(self.url)
                time.sleep(5)  # انتظر 5 ثوانٍ للتأكد من تحميل الصفحة
            
                wait = WebDriverWait(driver, 20)
            
            # اختبار الانتظار وظهور العناصر على الصفحة
                logging.info("انتظار ظهور محتوى الصفحة...")
            
            # محاولة النقر على زر "عرض المزيد" باستخدام جميع المحددات المتاحة
                for load_more_selector in SELECTORS['load_more']:
                    load_more_count = 0
                    while (load_more_count < 5):  # حد أقصى لعدد مرات الضغط
                        try:
                            selector_type = By.XPATH if load_more_selector.startswith("//") else By.CSS_SELECTOR
                            wait = WebDriverWait(driver, 10)
                            
                            # Wait for the button to be clickable
                            load_more = wait.until(EC.element_to_be_clickable((selector_type, load_more_selector)))
                            
                            # Try clicking the button
                            driver.execute_script("arguments[0].click();", load_more)
                            load_more_count += 1
                            logging.info(f"Clicked 'Load More' button ({load_more_count}) using selector: {load_more_selector}")
                            
                            # Wait for new content to load
                            time.sleep(5)
                        except Exception as e:
                            logging.info(f"'Load More' button not available or not clickable: {e}")
                            break

                    if load_more_count > 0:
                        # Successfully used this selector
                        break
                
                # حفظ لقطة من الصفحة للتشخيص
                driver.save_screenshot("page_screenshot.png")
                logging.info("تم حفظ لقطة من الصفحة للتشخيص في page_screenshot.png")
                
                # عرض مصدر HTML للصفحة في السجل (جزء صغير)
                page_source = driver.page_source
                logging.info(f"جزء من مصدر الصفحة: {page_source[:500]}...")
                
                with open("page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                # محاولة استخراج البطاقات باستخدام جميع المحددات المتاحة
                current_matches = set()
                
                for card_selector in SELECTORS['cards']:
                    logging.info(f"محاولة استخراج البطاقات باستخدام المحدد: {card_selector}")
                    cards = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.mx-auto.w-full > a")))
                    print(f"عدد الكروت المستخرجة: {len(cards)}")
                    
                    if cards:
                        logging.info(f"تم العثور على {len(cards)} بطاقة باستخدام المحدد: {card_selector}")
                        
                        for i, card in enumerate(cards):
                            try:
                                # محاولة استخراج العنوان باستخدام جميع محددات العناوين
                                title = None
                                
                                for title_selector in SELECTORS['title']:
                                    try:
                                        title_elements = card.find_elements(By.CSS_SELECTOR, title_selector)
                                        if title_elements:
                                            title = title_elements[0].text.strip()
                                            logging.info(f"تم استخراج العنوان باستخدام المحدد: {title_selector}")
                                            break
                                    except Exception as e:
                                        continue
                                
                                # إذا لم نستطع العثور على العنوان، نحاول الحصول على النص الكامل للبطاقة
                                if not title:
                                    title = card.text.strip()
                                    logging.info("تم استخدام نص البطاقة الكامل بدلاً من العنوان المخصص")
                                
                                if title:
                                    current_matches.add(title)
                                    logging.info(f"المباراة {i+1}: {title}")
                            except Exception as e:
                                logging.warning(f"خطأ في استخراج بيانات المباراة رقم {i+1}: {e}")
                        
                        # إذا وجدنا بطاقات، نتوقف عن استخدام المحددات الأخرى
                        if current_matches:
                            break
                
                # طباعة تقرير بالمعلومات المستخرجة
                logging.info(f"إجمالي المباريات المستخرجة: {len(current_matches)}")
                for idx, match in enumerate(current_matches):
                    logging.info(f"مباراة {idx+1}: {match}")
                
                # التحقق من المباريات الجديدة
                new_matches = current_matches - self.matches
                if new_matches:
                    for match in new_matches:
                        message = f"🎟️ مباراة جديدة نزلت: {match}"
                        self.send_notification(message)
                    self.matches.update(new_matches)
                    self.new_matches = new_matches  # لتتبع المباريات الجديدة للعرض في الواجهة
                    self._save_matches()
                    logging.info(f"تم العثور على {len(new_matches)} مباراة جديدة")
                else:
                    logging.info("لا توجد مباريات جديدة")
                
                return len(new_matches)
                
            except Exception as e:
                logging.error(f"حدث خطأ أثناء تحليل الصفحة: {e}")
                # تسجيل stack trace كاملة
                import traceback
                logging.error(traceback.format_exc())
                self.send_notification(f"⚠️ حدث خطأ في نظام المراقبة: {str(e)[:100]}")
                return -1
    
    def fetch_with_retry(self, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                result = self.fetch_new_matches()
                return result
            except Exception as e:
                logging.error(f"فشلت المحاولة رقم {attempt+1}: {e}")
                if attempt == max_attempts - 1:
                    self.send_notification("⚠️ حدث خطأ في نظام المراقبة! يرجى التحقق")
                time.sleep(60)  # انتظر دقيقة قبل إعادة المحاولة
        return -1
    
    def run(self, interval=60):
        while True:
            self.fetch_with_retry()
            time.sleep(interval)

#-----------------------------------------------------------------------------------------------------------------------------



# ====== إعداد Flask ======
app = Flask(__name__)

# إنشاء المراقب
monitor = TicketsMonitor(
    url="https://webook.com/ar/explore?tag=football&category=sports-events",
    bot_token=os.environ.get("BOT_TOKEN", "7979804759:AAHfCswfBOhQ-Y9rwEDbnvEAxNeO_ZQ_H20"),
    chat_id=os.environ.get("CHAT_ID", "7979804759")
)

@app.route('/')
def home():
    logging.info(f"المباريات الحالية: {monitor.matches}")
    logging.info(f"المباريات الجديدة: {monitor.new_matches}")
    return render_template('monitor.html', 
                          matches=sorted(monitor.matches),
                          new_matches=monitor.new_matches,
                          last_check=monitor.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if monitor.last_check_time else None)

@app.route('/status', methods=['GET'])
def api_status():
    return jsonify({
        'status': 'running',
        'matches_count': len(monitor.matches),
        'new_matches_count': len(monitor.new_matches),
        'last_check': monitor.last_check_time.strftime('%Y-%m-%d %H:%M:%S') if monitor.last_check_time else None
    })

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    keep_alive()
    logging.info("بدء تشغيل مراقب التذاكر...")
    monitor_thread = Thread(target=monitor.run, args=(60*5,))  # التحقق كل 5 دقائق
    monitor_thread.start()