import os
import cv2
import json
import numpy as np
import insightface
from insightface.app import FaceAnalysis

# Configuration
GALLERY_DIR = "gallery" # The folder containing the wedding photos
DB_PATH = "database.json" # Where to save the processed embeddings

def main():
    if not os.path.exists(GALLERY_DIR):
        print(f"Creating '{GALLERY_DIR}' directory. Please place your wedding photos here and run again.")
        os.makedirs(GALLERY_DIR)
        return

    print("Initializing InsightFace model...")
    try:
        app = FaceAnalysis(name='buffalo_l')
        app.prepare(ctx_id=0, det_size=(640, 640))
    except Exception as e:
        print(f"Failed to initialize model. Did you install insightface and onnxruntime? Error: {e}")
        return

    database = []

    print(f"Scanning '{GALLERY_DIR}' for images...")
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    
    for filename in os.listdir(GALLERY_DIR):
        if not filename.lower().endswith(valid_extensions):
            continue
            
        filepath = os.path.join(GALLERY_DIR, filename)
        print(f"Processing {filename}...")
        
        img = cv2.imread(filepath)
        if img is None:
            print(f"  Warning: Could not read {filename}")
            continue
            
        faces = app.get(img)
        print(f"  Found {len(faces)} face(s)")
        
        # We store the image path, and a list of embeddings for all faces found in it.
        # Numpy arrays must be converted to python lists to be JSON serializable.
        embeddings = [face.embedding.tolist() for face in faces]
        
        if embeddings:
            database.append({
                "url": f"/gallery/{filename}",  # URL path for frontend
                "file": filename,
                "embeddings": embeddings
            })

    # Save to JSON
    with open(DB_PATH, 'w') as f:
        json.dump(database, f)
        
    print(f"\nProcessing complete! Saved {len(database)} photos with faces to {DB_PATH}")

if __name__ == "__main__":
    main()
