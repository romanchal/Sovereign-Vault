import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# --- SOVEREIGN SECURITY: BRIDGE FACE TO BRAIN ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MediaRequest(BaseModel):
    url: str
    format: str

@app.post("/api/process-media")
async def process_media(request: MediaRequest):
    # Unique filename to prevent overlaps on the server
    unique_id = str(uuid.uuid4())[:8]
    output_path = f"/tmp/sov_{unique_id}.{request.format}"
    
    # Path to the Secret File you uploaded in Render Dashboard
    cookie_path = os.path.join(os.getcwd(), 'cookies.txt')

    ydl_opts = {
        'format': 'bestaudio/best' if request.format == 'mp3' else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'noplaylist': True,
        'quiet': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        # Browser Spoofing
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # Use Cookies if Render detected the Secret File
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
        print(f"Sovereign Protocol: Authenticated Session Active for ID {unique_id}")

    if request.format == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([request.url])
        
        if os.path.exists(output_path):
            return FileResponse(
                path=output_path, 
                filename=f"Sovereign_Extract_{unique_id}.{request.format}",
                media_type='application/octet-stream'
            )
        else:
            raise HTTPException(status_code=500, detail="Extraction failed: File not found.")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="YouTube Blocked this request. Check Server Logs.")

# --- AUTO-PING ENDPOINT ---
@app.get("/api/ping")
async def ping():
    return {"status": "online", "message": "Sovereign Engine Active"}