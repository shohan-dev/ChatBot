@echo off
echo Starting ISP AI Chatbot Environment...

:: Check if python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed! Please install Python first.
    pause
    exit /b
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Run the application
echo Starting FastAPI Server...
echo Access the chat at http://127.0.0.1:8000
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause
