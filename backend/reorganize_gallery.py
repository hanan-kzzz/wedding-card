import os
import cv2
import json
import uuid
import shutil
import numpy as np
from numpy.linalg import norm
from insightface.app import FaceAnalysis

# Initialize Face Analysis
try:
    face_app = FaceAnalysis(name='buffalo_l')
    face_app.prepare(ctx_id=0, det_size=(640, 640))
except Exception as e:
    print(f"Error initializing face analysis: {e}")
    exit(1)

def compute_similarity(emb1, emb2):
    return np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))

def main():
    gallery_dir = "gallery"
    db_path = "database.json"
    
    if not os.path.exists(gallery_dir):
        print("Gallery directory not found.")
        return

    # New DB structure
    db_data = {
        "persons": {}
    }

    group_photos_dir = os.path.join(gallery_dir, "group_photos")
    os.makedirs(group_photos_dir, exist_ok=True)
    
    # We will process all valid images in the gallery root and its subdirectories
    # But wait, if they are already in person_ or group_photos, we might re-process them.
    # To be safe, let's gather all images first, move them to a temp folder, and then process.
    temp_dir = "gallery_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    
    for root, dirs, files in os.walk(gallery_dir):
        # Skip temp_dir and group_photos to avoid infinite loop
        if "gallery_temp" in root:
            continue
        for file in files:
            if file.lower().endswith(valid_extensions):
                old_path = os.path.join(root, file)
                new_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}_{file}")
                shutil.move(old_path, new_path)
                
    # Now remove all subdirectories in gallery_dir
    for item in os.listdir(gallery_dir):
        item_path = os.path.join(gallery_dir, item)
        if os.path.isdir(item_path) and item != "group_photos":
            shutil.rmtree(item_path)

    threshold = 0.5

    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        img = cv2.imread(filepath)
        if img is None:
            continue
            
        faces = face_app.get(img)
        
        # Determine the final destination for this image
        original_name = filename.split('_', 1)[1] if '_' in filename else filename
        # Ensure unique name if duplicates exist
        final_filename = f"{uuid.uuid4().hex[:8]}_{original_name}"
        
        if len(faces) == 0:
            # Move to a default folder
            dest_dir = os.path.join(gallery_dir, "unrecognized")
            os.makedirs(dest_dir, exist_ok=True)
            relative_path = f"unrecognized/{final_filename}"
            
        elif len(faces) > 1:
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
            for pid, pdata in db_data["persons"].items():
                sim = compute_similarity(emb, np.array(pdata["representative_embedding"]))
                if sim > threshold:
                    matched_id = pid
                    break
            
            if not matched_id:
                # Create a new person
                matched_id = f"person_{uuid.uuid4().hex[:8]}"
                db_data["persons"][matched_id] = {
                    "representative_embedding": emb.tolist(),
                    "photos": []
                }
            
            matched_person_ids.append(matched_id)
            
        if len(faces) == 1:
            person_id = matched_person_ids[0]
            dest_dir = os.path.join(gallery_dir, person_id)
            os.makedirs(dest_dir, exist_ok=True)
            relative_path = f"{person_id}/{final_filename}"
            
        dest_path = os.path.join(gallery_dir, relative_path)
        shutil.move(filepath, dest_path)
        
        for pid in set(matched_person_ids):
            # deduplicate if same face found twice (shouldn't happen but just in case)
            if f"/gallery/{relative_path}" not in db_data["persons"][pid]["photos"]:
                db_data["persons"][pid]["photos"].append(f"/gallery/{relative_path}")
            
    shutil.rmtree(temp_dir)
    
    with open(db_path, "w") as f:
        json.dump(db_data, f, indent=4)
        
    print("Gallery reorganized successfully.")

if __name__ == "__main__":
    main()
