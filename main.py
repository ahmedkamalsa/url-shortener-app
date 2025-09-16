# main.py
import os
import secrets
import time
import psycopg2
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from psycopg2.extras import RealDictCursor

# --- App and Template Configuration ---
app = FastAPI(title="Professional URL Shortener")
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(Path(BASE_DIR, 'templates')))

# --- Database Connection Management ---
def get_db_connection():
    retries = 5
    DATABASE_URL = os.environ.get("DATABASE_URL")
    while retries > 0:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except psycopg2.OperationalError:
            retries -= 1
            time.sleep(1) # Reduced sleep time for faster retries
    raise RuntimeError("Could not connect to database.")

@app.on_event("startup")
async def startup_event():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    id SERIAL PRIMARY KEY,
                    short_code VARCHAR(255) UNIQUE NOT NULL,
                    long_url TEXT NOT NULL,
                    clicks INT NOT NULL DEFAULT 0
                );
            """)
            conn.commit()
    finally:
        conn.close()

# --- Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/shorten", response_class=HTMLResponse)
async def create_short_url(request: Request, url: str = Form(...), custom_code: str = Form(None)):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            short_code = custom_code if (custom_code and custom_code.strip()) else secrets.token_urlsafe(6)
            
            if custom_code and custom_code.strip():
                cursor.execute("SELECT short_code FROM urls WHERE short_code = %s", (short_code,))
                if cursor.fetchone():
                    return templates.TemplateResponse("index.html", {
                        "request": request,
                        "error": "Sorry, that custom code is already taken. Please try another.",
                        "url": url,
                        "custom_code": custom_code
                    })

            cursor.execute("INSERT INTO urls (short_code, long_url) VALUES (%s, %s)", (short_code, url))
            conn.commit()
            
            base_url = str(request.base_url).rstrip('/')
            new_url = f"{base_url}/{short_code}"
            
            return templates.TemplateResponse("index.html", {"request": request, "new_url": new_url})
    finally:
        conn.close()

@app.get("/{short_code}")
async def redirect_to_long_url(short_code: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT long_url FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="URL not found")
            
            cursor.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = %s", (short_code,))
            conn.commit()

            return RedirectResponse(url=result['long_url'])
    finally:
        conn.close()

@app.get("/{short_code}/stats", response_class=HTMLResponse)
async def get_stats(request: Request, short_code: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT long_url, clicks FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="URL not found")
            
            base_url = str(request.base_url).rstrip('/')
            full_short_url = f"{base_url}/{short_code}"

            return templates.TemplateResponse("stats.html", {
                "request": request,
                "short_url": full_short_url,
                "long_url": result['long_url'],
                "clicks": result['clicks']
            })
    finally:
        conn.close()