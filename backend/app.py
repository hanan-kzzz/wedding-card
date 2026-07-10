from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

import json
from numpy.linalg import norm
import os

from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Allow CORS for local testing from static files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Serve the gallery folder statically so the frontend can display the images
if os.path.exists("gallery"):
    app.mount("/gallery", StaticFiles(directory="gallery"), name="gallery")

# Initialize InsightFace model
try:
    face_app = FaceAnalysis(name='buffalo_l')
    face_app.prepare(ctx_id=0, det_size=(640, 640))
except Exception as e:
    print(f"Error initializing face analysis: {e}")
    face_app = None

# Load the database
DB_PATH = "database.json"
WEDDING_PHOTOS = []
LAST_DB_MTIME = 0

def sync_gallery():
    global WEDDING_PHOTOS, LAST_DB_MTIME
    if not face_app:
        return

    # Reload from disk only if modified (saves I/O time on every request)
    if os.path.exists(DB_PATH):
        current_mtime = os.path.getmtime(DB_PATH)
        if current_mtime > LAST_DB_MTIME:
            with open(DB_PATH, 'r') as f:
                WEDDING_PHOTOS = json.load(f)
            LAST_DB_MTIME = current_mtime
    else:
        WEDDING_PHOTOS = []

    existing_files = {photo.get('file', '') for photo in WEDDING_PHOTOS}
    new_files_processed = False
    gallery_dir = "gallery"

    if os.path.exists(gallery_dir):
        valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
        for filename in os.listdir(gallery_dir):
            if not filename.lower().endswith(valid_extensions):
                continue
            if filename not in existing_files:
                print(f"New image found: {filename}, processing...")
                filepath = os.path.join(gallery_dir, filename)
                img = cv2.imread(filepath)
                if img is None:
                    continue
                
                faces = face_app.get(img)
                embeddings = [face.embedding.tolist() for face in faces]
                
                if embeddings:
                    WEDDING_PHOTOS.append({
                        "url": f"/gallery/{filename}",
                        "file": filename,
                        "embeddings": embeddings
                    })
                else:
                    # Append an empty entry so we don't process it again
                    WEDDING_PHOTOS.append({
                        "url": f"/gallery/{filename}",
                        "file": filename,
                        "embeddings": []
                    })
                new_files_processed = True

    if new_files_processed:
        with open(DB_PATH, 'w') as f:
            json.dump(WEDDING_PHOTOS, f)
        print(f"Database updated with new images. Total photos: {len(WEDDING_PHOTOS)}")

# Initial load
sync_gallery()


def compute_similarity(emb1, emb2):
    # Cosine similarity
    return np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))

@app.post("/api/recognize")
async def recognize_face(file: UploadFile = File(...)):
    if not face_app:
        raise HTTPException(status_code=500, detail="Face recognition model not initialized.")
        
    # Sync gallery images before processing
    sync_gallery()
        
    if not WEDDING_PHOTOS:
        raise HTTPException(status_code=500, detail="Gallery database is empty or not loaded.")

    try:
        # Read the uploaded image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Optimize: Resize image if it's too large to speed up face detection
        max_size = 800
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        # Detect faces
        faces = face_app.get(img)
        
        if not faces:
            return {"message": "No faces detected in the uploaded selfie.", "matches": []}
        
        # Take the embedding of the largest face in the selfie (usually index 0)
        user_embedding = faces[0].embedding
        
        matches = []
        THRESHOLD = 0.5  # Adjust this similarity threshold as needed (0 to 1, higher is stricter)
        
        for photo in WEDDING_PHOTOS:
            for gallery_emb in photo['embeddings']:
                sim = compute_similarity(user_embedding, np.array(gallery_emb))
                if sim > THRESHOLD:
                    matches.append(photo['url'])
                    break # Skip other faces in the same photo if we already found a match
        
        # Deduplicate matches
        matches = list(set(matches))
        
        if matches:
            return {
                "message": f"Successfully matched you in {len(matches)} photo(s)!",
                "matches": matches,
                "status": "success"
            }
        else:
            return {
                "message": "We couldn't find any matches in the gallery.",
                "matches": [],
                "status": "success" # the request succeeded, just no matches
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
