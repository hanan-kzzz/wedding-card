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
import uuid
import shutil

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
DB_DATA = {"persons": {}}
LAST_DB_MTIME = 0

def load_db():
    global DB_DATA, LAST_DB_MTIME
    if os.path.exists(DB_PATH):
        current_mtime = os.path.getmtime(DB_PATH)
        if current_mtime > LAST_DB_MTIME:
            with open(DB_PATH, 'r') as f:
                try:
                    DB_DATA = json.load(f)
                except json.JSONDecodeError:
                    DB_DATA = {"persons": {}}
            LAST_DB_MTIME = current_mtime
    else:
        DB_DATA = {"persons": {}}

def save_db():
    with open(DB_PATH, 'w') as f:
        json.dump(DB_DATA, f, indent=4)
    global LAST_DB_MTIME
    if os.path.exists(DB_PATH):
        LAST_DB_MTIME = os.path.getmtime(DB_PATH)

load_db()

def compute_similarity(emb1, emb2):
    return np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))

@app.post("/api/admin/upload")
async def admin_upload_image(file: UploadFile = File(...)):
    try:
        gallery_dir = "gallery"
        group_photos_dir = os.path.join(gallery_dir, "group_photos")
        unrecognized_dir = os.path.join(gallery_dir, "unrecognized")
        os.makedirs(gallery_dir, exist_ok=True)
        os.makedirs(group_photos_dir, exist_ok=True)
        os.makedirs(unrecognized_dir, exist_ok=True)
            
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Detect faces
        faces = face_app.get(img)
        
        original_name = file.filename
        final_filename = f"{uuid.uuid4().hex[:8]}_{original_name}"
        
        load_db()
        threshold = 0.5
        
        if len(faces) == 0:
            dest_dir = unrecognized_dir
            relative_path = f"unrecognized/{final_filename}"
            file_path = os.path.join(gallery_dir, relative_path)
            cv2.imwrite(file_path, img)
            return {"status": "success", "message": f"Uploaded {file.filename} (No faces detected)"}
            
        if len(faces) > 1:
            dest_dir = group_photos_dir
            relative_path = f"group_photos/{final_filename}"
        else:
            dest_dir = None
            relative_path = None
            
        matched_person_ids = []
        
        for face in faces:
            emb = face.embedding
            matched_id = None
            
            # Check against existing persons
            for pid, pdata in DB_DATA.get("persons", {}).items():
                sim = compute_similarity(emb, np.array(pdata["representative_embedding"]))
                if sim > threshold:
                    matched_id = pid
                    break
            
            if not matched_id:
                matched_id = f"person_{uuid.uuid4().hex[:8]}"
                if "persons" not in DB_DATA:
                    DB_DATA["persons"] = {}
                DB_DATA["persons"][matched_id] = {
                    "representative_embedding": emb.tolist(),
                    "photos": []
                }
            
            matched_person_ids.append(matched_id)
            
        if len(faces) == 1:
            person_id = matched_person_ids[0]
            dest_dir = os.path.join(gallery_dir, person_id)
            os.makedirs(dest_dir, exist_ok=True)
            relative_path = f"{person_id}/{final_filename}"
            
        file_path = os.path.join(gallery_dir, relative_path)
        cv2.imwrite(file_path, img)
        
        for pid in set(matched_person_ids):
            photo_url = f"/gallery/{relative_path}"
            if photo_url not in DB_DATA["persons"][pid]["photos"]:
                DB_DATA["persons"][pid]["photos"].append(photo_url)
                
        save_db()
        
        return {"status": "success", "message": f"Successfully uploaded {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
class DeletePhotoRequest(BaseModel):
    path: str

@app.get("/api/admin/photos")
async def get_all_photos():
    gallery_dir = "gallery"
    photos = []
    if os.path.exists(gallery_dir):
        for root, _, files in os.walk(gallery_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    rel_dir = os.path.relpath(root, gallery_dir)
                    if rel_dir == ".":
                        rel_path = file
                    else:
                        rel_path = f"{rel_dir}/{file}".replace("\\", "/")
                    photos.append({
                        "url": f"/gallery/{rel_path}",
                        "filename": file,
                        "path": rel_path
                    })
    # Sort by modification time (newest first)
    photos.sort(key=lambda p: os.path.getmtime(os.path.join(gallery_dir, p["path"])) if os.path.exists(os.path.join(gallery_dir, p["path"])) else 0, reverse=True)
    return {"status": "success", "photos": photos}

@app.post("/api/admin/photos/delete")
async def delete_photo(req: DeletePhotoRequest):
    try:
        gallery_dir = "gallery"
        file_path = os.path.normpath(os.path.join(gallery_dir, req.path))
        # Basic security check to prevent path traversal
        if not file_path.startswith(os.path.abspath(gallery_dir)) and not file_path.startswith(gallery_dir):
             raise HTTPException(status_code=400, detail="Invalid path")
             
        # Remove file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Remove from DB
        load_db()
        photo_url = f"/gallery/{req.path.replace(os.sep, '/')}"
        for pid, pdata in list(DB_DATA.get("persons", {}).items()):
            if photo_url in pdata["photos"]:
                pdata["photos"].remove(photo_url)
        save_db()
        
        return {"status": "success", "message": "Photo deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recognize")
async def recognize_face(file: UploadFile = File(...)):
    if not face_app:
        raise HTTPException(status_code=500, detail="Face recognition model not initialized.")
        
    load_db()
        
    if not DB_DATA.get("persons"):
        raise HTTPException(status_code=500, detail="Gallery database is empty.")

    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        max_size = 800
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        faces = face_app.get(img)
        
        if not faces:
            return {"message": "No faces detected in the uploaded selfie.", "matches": []}
        
        user_embedding = faces[0].embedding
        
        matches = []
        THRESHOLD = 0.5
        
        # Only compare against representative embedding of each person!
        for pid, pdata in DB_DATA.get("persons", {}).items():
            sim = compute_similarity(user_embedding, np.array(pdata["representative_embedding"]))
            if sim > THRESHOLD:
                matches.extend(pdata["photos"])
                break # Matched the person, no need to keep checking other persons
        
        matches = list(set(matches))
        
        if matches:
            return {
                "message": f"Successfully matched you! Found {len(matches)} photo(s).",
                "matches": matches,
                "status": "success"
            }
        else:
            return {
                "message": "We couldn't find any matches in the gallery.",
                "matches": [],
                "status": "success"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
