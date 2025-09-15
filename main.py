# main.py
import os
import secrets
import time  # استيراد مكتبة الوقت
import psycopg2
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Resilient URL Shortener")

def get_db_connection():
    """
    يقوم بالاتصال بقاعدة البيانات مع آلية إعادة محاولة ذكية.
    """
    retries = 5
    DATABASE_URL = os.environ.get("DATABASE_URL")
    while retries > 0:
        try:
            print("Attempting to connect to the database...")
            conn = psycopg2.connect(DATABASE_URL)
            print("Database connection successful!")
            return conn
        except psycopg2.OperationalError as e:
            print(f"Database connection failed: {e}")
            retries -= 1
            print(f"Retrying in 5 seconds... ({retries} attempts left)")
            time.sleep(5)  # انتظر 5 ثوانٍ قبل المحاولة مرة أخرى
    
    # إذا فشلت كل المحاولات، قم بإنهاء التطبيق
    raise RuntimeError("Could not connect to the database after several attempts.")

# قم باستدعاء الدالة الجديدة للحصول على الاتصال
conn = get_db_connection()

@app.on_event("startup")
async def startup_event():
    """ عند بدء التشغيل، تأكد من وجود الجدول في قاعدة البيانات """
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id SERIAL PRIMARY KEY,
                short_code VARCHAR(10) UNIQUE NOT NULL,
                long_url TEXT NOT NULL
            );
        """)
        conn.commit()
    print("Table 'urls' is ready.")

@app.post("/shorten", status_code=201)
async def create_short_url(request: Request):
    """ API Endpoint لإنشاء رابط قصير """
    data = await request.json()
    long_url = data.get("url")
    if not long_url:
        raise HTTPException(status_code=400, detail="URL is required")

    short_code = secrets.token_urlsafe(6)

    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO urls (short_code, long_url) VALUES (%s, %s)",
            (short_code, long_url)
        )
        conn.commit()
    
    return {"short_url": f"/{short_code}"}


@app.get("/{short_code}")
async def redirect_to_long_url(short_code: str):
    """ إعادة التوجيه من الرابط القصير إلى الطويل """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT long_url FROM urls WHERE short_code = %s", (short_code,))
        result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return RedirectResponse(url=result['long_url'])