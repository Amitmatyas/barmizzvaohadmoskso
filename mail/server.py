import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
import pytz

# קובץ ה-serviceAccount.json תעלה ליד server.py או תשתמש ב-secret של Railway
cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

MAILERSEND_TOKEN = "YOUR_MAILERSEND_TOKEN"  # הכנס כאן את הטוקן שלך
MAILERSEND_TEMPLATE_ID = "jpzkmgq8emmg059v"
FROM_EMAIL = "amitmatyas@gmail.com"
TIMEZONE = "Asia/Jerusalem"  # שנה לפי הצורך

def send_mail(to_email, hours_text):
    url = "https://api.mailersend.com/v1/email"
    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Authorization": f"Bearer {MAILERSEND_TOKEN}"
    }
    data = {
        "from": { "email": FROM_EMAIL },
        "to": [{ "email": to_email }],
        "personalization": [{
            "email": to_email,
            "data": { "hours": hours_text }
        }],
        "template_id": MAILERSEND_TEMPLATE_ID
    }
    resp = requests.post(url, headers=headers, json=data)
    print(f"שליחה ל-{to_email} ({hours_text}): {resp.status_code}", resp.text)
    return resp.status_code == 202

def check_and_send():
    now = datetime.now(pytz.timezone(TIMEZONE))
    reminders = db.collection("event_reminders").stream()
    for doc in reminders:
        data = doc.to_dict()
        email = data["email"]
        # שליחה 24 שעות לפני
        if not data.get("sent24"):
            dt24 = datetime.fromisoformat(data["reminder24"])
            if abs((dt24 - now).total_seconds()) < 60:
                if send_mail(email, "24"):
                    doc.reference.update({"sent24": True})
        # שליחה שעתיים לפני
        if not data.get("sent2"):
            dt2 = datetime.fromisoformat(data["reminder2"])
            if abs((dt2 - now).total_seconds()) < 60:
                if send_mail(email, "2"):
                    doc.reference.update({"sent2": True})
        # ניקוי אחרי שהאירוע עבר
        if data.get("eventDateTime"):
            event_dt = datetime.fromisoformat(data["eventDateTime"])
            if event_dt < now:
                doc.reference.delete()

scheduler = BlockingScheduler()
scheduler.add_job(check_and_send, 'interval', minutes=1)

if __name__ == "__main__":
    print("Reminder sender started")
    scheduler.start()
