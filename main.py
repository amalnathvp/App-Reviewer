import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from app.collector import ReviewCollector
from app.pm_agent import PMAgent

app = FastAPI(
    title="AI Product Management Intelligence Agent",
    description="Automated Customer Feedback Analysis & Actionable Product Insights Platform",
    version="1.0.0"
)

# Request models
class CollectRequest(BaseModel):
    app_name: Optional[str] = None
    google_play_url: Optional[str] = None
    apple_store_url: Optional[str] = None
    review_limit: Optional[int] = 60
    country: Optional[str] = "us"

class AnalyzePayload(BaseModel):
    app: Dict[str, Any]
    reviews: List[Dict[str, Any]]

class DirectTextRequest(BaseModel):
    app_name: str
    reviews_text: str
    category: Optional[str] = "Mobile App"
    platform: Optional[str] = "google_play"

class QuickAnalyzeRequest(BaseModel):
    query: str
    review_limit: Optional[int] = 80
    country: Optional[str] = "us"

# Curated popular demo presets
SAMPLE_APPS = [
    {
        "id": "quizlet",
        "name": "Quizlet: AI Study Flashcards",
        "category": "Education",
        "google_play_url": "https://play.google.com/store/apps/details?id=com.quizlet.quizletandroid",
        "apple_store_url": "https://apps.apple.com/us/app/id546473125",
        "icon": "📚"
    },
    {
        "id": "spotify",
        "name": "Spotify: Music and Podcasts",
        "category": "Music & Audio",
        "google_play_url": "https://play.google.com/store/apps/details?id=com.spotify.music",
        "apple_store_url": "https://apps.apple.com/us/app/id324684580",
        "icon": "🎵"
    },
    {
        "id": "duolingo",
        "name": "Duolingo: Language Lessons",
        "category": "Education",
        "google_play_url": "https://play.google.com/store/apps/details?id=com.duolingo",
        "apple_store_url": "https://apps.apple.com/us/app/id570060128",
        "icon": "🦉"
    },
    {
        "id": "notion",
        "name": "Notion: Notes, Docs & Tasks",
        "category": "Productivity",
        "google_play_url": "https://play.google.com/store/apps/details?id=notion.id",
        "apple_store_url": "https://apps.apple.com/us/app/id1232780281",
        "icon": "📝"
    },
    {
        "id": "minireview",
        "name": "MiniReview - Game Reviews",
        "category": "Entertainment",
        "google_play_url": "https://play.google.com/store/apps/details?id=minireview.best.android.games.reviews",
        "apple_store_url": "https://apps.apple.com/us/app/id6477473021",
        "icon": "🎮"
    }
]

@app.get("/api/sample-apps")
async def get_sample_apps():
    return SAMPLE_APPS

@app.post("/api/collect")
async def collect_reviews(req: CollectRequest):
    """
    Step A: Retrieve reviews and metadata from Google Play and Apple App Store.
    Returns standard structured JSON input.
    """
    if not req.app_name and not req.google_play_url and not req.apple_store_url:
        raise HTTPException(
            status_code=400,
            detail="Must provide an app_name, google_play_url, or apple_store_url."
        )

    data = ReviewCollector.collect(
        app_name=req.app_name,
        google_play_url=req.google_play_url,
        apple_store_url=req.apple_store_url,
        review_limit=req.review_limit or 60,
        country=req.country or "us"
    )

    if not data["reviews"]:
        # If scraper found 0 reviews, return informative message
        return {
            "app": data["app"],
            "reviews": [],
            "message": "No reviews could be retrieved for the specified target. Check the identifier or try a sample app."
        }

    return data

@app.post("/api/analyze")
async def analyze_structured_reviews(payload: AnalyzePayload):
    """
    Step B: AI PM Agent processes structured review input.
    Executes all 14 steps and returns the exact required JSON schema.
    """
    result = PMAgent.analyze(payload.model_dump())
    return result

@app.post("/api/quick-analyze")
async def quick_analyze(req: QuickAnalyzeRequest):
    """
    Single-input analysis: Takes an app name OR store link,
    auto-resolves and performs visual PM intelligence analysis.
    """
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Please enter an app name or link.")
    
    collected = ReviewCollector.auto_collect(
        query_or_url=query,
        review_limit=req.review_limit or 80,
        country=req.country or "us"
    )
    if not collected.get("reviews"):
        raise HTTPException(
            status_code=404,
            detail=f"No customer reviews found for '{query}'. Please check the spelling or paste a store link."
        )
    
    analysis = PMAgent.analyze(collected)
    return {
        "collected_data": collected,
        "analysis": analysis
    }

@app.post("/api/analyze-app")
async def analyze_app_end_to_end(req: CollectRequest):
    """
    End-to-end endpoint: Collects reviews from store(s) and runs PM Intelligence analysis.
    """
    if not req.app_name and not req.google_play_url and not req.apple_store_url:
        raise HTTPException(
            status_code=400,
            detail="Must provide an app_name, google_play_url, or apple_store_url."
        )

    collected = ReviewCollector.collect(
        app_name=req.app_name,
        google_play_url=req.google_play_url,
        apple_store_url=req.apple_store_url,
        review_limit=req.review_limit or 60,
        country=req.country or "us"
    )

    if not collected["reviews"]:
        raise HTTPException(
            status_code=404,
            detail="Could not find or retrieve reviews for the specified app. Please verify the URL or try searching by exact app name."
        )

    analysis = PMAgent.analyze(collected)
    return {
        "collected_data": collected,
        "analysis": analysis
    }

@app.post("/api/analyze-text")
async def analyze_pasted_text(req: DirectTextRequest):
    """
    Allows pasting raw review text (one review per line or separated by double newlines).
    """
    lines = [l.strip() for l in req.reviews_text.split("\n") if l.strip()]
    reviews_list = []
    for l in lines:
        if len(l) > 10:
            reviews_list.append({
                "platform": req.platform or "google_play",
                "rating": 1 if any(w in l.lower() for w in ["bad", "crash", "hate", "slow", "bug"]) else 5,
                "review": l,
                "date": "2026-10-06",
                "version": "Current",
                "language": "en",
                "helpful_count": 0
            })

    payload = {
        "app": {
            "name": req.app_name,
            "package_id": "custom.app",
            "app_store_id": "",
            "category": req.category or "Mobile App",
            "description": "User submitted review bundle",
            "rating": None,
            "review_count": len(reviews_list)
        },
        "reviews": reviews_list
    }

    analysis = PMAgent.analyze(payload)
    return {
        "collected_data": payload,
        "analysis": analysis
    }

# Mount static files and frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>AI Product Management Intelligence Agent</h1><p>Frontend loading...</p>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
