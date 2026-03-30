from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import yt_dlp
import os

app = FastAPI(title="Sovereign Media Engine v4.0")

# --- THE BRIDGE (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE CORE ---
def get_db():
    conn = sqlite3.connect("sovereign_vault.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            category TEXT NOT NULL,
            reward_amount TEXT NOT NULL,
            promo_link TEXT NOT NULL,
            logo_url TEXT,
            clicks INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- MODELS & SECURITY ---
ADMIN_USER = "admin"
ADMIN_PASS = "roman777"

class AdminAuth(BaseModel):
    username: str
    password: str

class Offer(BaseModel):
    app_name: str
    category: str
    reward_amount: str
    promo_link: str
    logo_url: str

class MediaRequest(BaseModel):
    url: str
    format: str  # 'mp3' or 'mp4'
    quality: str # '360', '720', '1080'

# --- ENDPOINTS ---

@app.post("/admin/login")
async def login(auth: AdminAuth):
    if auth.username == ADMIN_USER and auth.password == ADMIN_PASS:
        return {"status": "authorized"}
    raise HTTPException(status_code=401)

@app.post("/admin/add-offer")
async def add_offer(offer: Offer):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO offers (app_name, category, reward_amount, promo_link, logo_url) VALUES (?,?,?,?,?)',
                   (offer.app_name, offer.category, offer.reward_amount, offer.promo_link, offer.logo_url))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/get-offers")
async def get_offers():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM offers")
    return [dict(row) for row in cursor.fetchall()]

@app.delete("/admin/delete-offer/{oid}")
async def delete_offer(oid: int):
    conn = get_db()
    conn.execute("DELETE FROM offers WHERE id = ?", (oid,))
    conn.commit()
    return {"status": "deleted"}

@app.get("/redirect/{oid}")
async def track_redirect(oid: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT promo_link FROM offers WHERE id = ?", (oid,))
    res = cursor.fetchone()
    if res:
        conn.execute("UPDATE offers SET clicks = clicks + 1 WHERE id = ?", (oid,))
        conn.commit()
        return RedirectResponse(url=res['promo_link'])
    raise HTTPException(status_code=404)

# --- THE MASTER DOWNLOAD ENGINE ---
def cleanup(path):
    if os.path.exists(path): os.remove(path)

@app.post("/api/process-media")
async def process_media(req: MediaRequest, tasks: BackgroundTasks):
    os.makedirs('vault_downloads', exist_ok=True)
    
    # Logic for Quality Selection
    fmt = 'bestaudio/best' if req.format == 'mp3' else f'bestvideo[height<={req.quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    
    opts = {
        'format': fmt,
        'outtmpl': 'vault_downloads/%(id)s.%(ext)s',
        'merge_output_format': 'mp4' if req.format == 'mp4' else None,
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}] if req.format == 'mp3' else [],
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            ext = 'mp3' if req.format == 'mp3' else 'mp4'
            path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.' + ext
            
        tasks.add_task(cleanup, path)
        return FileResponse(path=path, filename=f"Sovereign_{info['id']}.{ext}")
    except:
        raise HTTPException(status_code=500, detail="Extraction Failed")