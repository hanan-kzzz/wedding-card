import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Change to the directory containing run.py (the backend directory)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
