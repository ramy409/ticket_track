import requests

bot_token = '8002339915:AAEwhTyAdVBqzRshhaWlKVTbdH-C3iQR1oE'
chat_id = '1221982749'
message = '✅ تم إرسال الرسالة بنجاح من البايثون للبوت!'

url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
payload = {
    'chat_id': chat_id,
    'text': message
}

response = requests.post(url, data=payload)

if response.status_code == 200:
    print("✅ تم إرسال الرسالة بنجاح!")
else:
    print("❌ فشل في الإرسال:", response.text)
