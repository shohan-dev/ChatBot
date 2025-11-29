from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.endpoints import chat
from app.api.endpoints import history
from app.db.models import init_db

# Initialize database on startup
init_db()
print("✅ Database initialized successfully")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# Setup Templates
templates = Jinja2Templates(directory="templates")

# Include Routers
app.include_router(chat.router, prefix="/api")
app.include_router(history.router)  # History endpoints with /api/history prefix

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the chat interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/history", response_class=HTMLResponse)
async def history_dashboard(request: Request):
    """Serves the chat history dashboard."""
    return templates.TemplateResponse("history.html", {"request": request})

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("🚀 ISP PayBD AI Chat Backend started")
    print("📊 Database: SQLite with full analytics")
    print("🔗 API endpoints:")
    print("   - POST /api/chat - Main chat endpoint")
    print("   - GET /api/history/conversations - List all conversations")
    print("   - GET /api/history/conversations/{id} - Get conversation messages")
    print("   - GET /api/history/users/{user_id}/conversations - User conversations")
    print("   - GET /api/history/statistics/daily - Daily statistics")
    print("   - GET /api/history/search - Search messages")
    print("   - DELETE /api/history/conversations/{id} - Delete conversation")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
