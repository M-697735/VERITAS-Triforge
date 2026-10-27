@echo off
setlocal
cd /d "%~dp0"

echo [VERITAS] Checking frontend build...
if not exist "frontend\dist\index.html" (
    echo [VERITAS] Building frontend assets...
    cd frontend
    call npm install
    call npm run build
    cd ..
)

echo [VERITAS] Launching backend server and opening browser...
python backend/run.py %*

