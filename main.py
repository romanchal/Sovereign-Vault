import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# SECURITY: Allow your GitHub/Netlify link to talk to the engine
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
    output_path = f"/tmp/sovereign_{os.urandom(4).hex()}.{request.format}"
    
    ydl_opts = {
        'format': 'bestaudio/best' if request.format == 'mp3' else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'noplaylist': True,
        'quiet': True,
        'nocheckcertificate': True,
    }

    if request.format == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([request.url])
        
        # Ensure file exists before sending
        if os.path.exists(output_path):
            return FileResponse(path=output_path, filename=f"extracted.{request.format}")
        else:
            raise HTTPException(status_code=500, detail="File generation failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))