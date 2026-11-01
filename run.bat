@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import sys; print('Using Python', sys.version)" || (echo Python 3.12 not found. Install Python 3.12 and enable the py launcher.& pause & exit /b 1)
py -3.12 -c "import fastapi, uvicorn, dotenv, mysql.connector, pydantic, httpx, multipart, edge_tts, itsdangerous" >nul 2>&1
if errorlevel 1 (
    echo Required packages are missing. Installing requirements...
    py -3.12 -m pip install -r requirements.txt || (echo Dependency installation failed.& pause & exit /b 1)
) else (
    echo Required packages are already installed; skipping reinstall.
)
if not exist .env copy .env.example .env
if not exist logs mkdir logs
py -3.12 scripts\ensure_admin_secret.py || (echo Could not prepare admin session security.& pause & exit /b 1)
findstr /C:"PASTE_YOUR_GROQ_API_KEY_HERE" .env >nul && (echo Add your Groq API key to .env first.& notepad .env & pause & exit /b 0)
findstr /C:"CHANGE_ME" .env >nul && (echo Set your MySQL password in .env before using hotel booking.& notepad .env & pause & exit /b 1)
findstr /C:"CHANGE_THIS_TO_A_UNIQUE_PASSWORD" .env >nul && (echo Set ADMIN_PASSWORD to a unique password of at least 12 characters.& notepad .env & pause & exit /b 1)
findstr /C:"admin@example.com" .env >nul && (echo Set ADMIN_EMAIL to the real admin email address.& notepad .env & pause & exit /b 1)
findstr /C:"PASTE_YOUR_RESEND_API_KEY_HERE" .env >nul && echo WARNING: Forgot-password email delivery is disabled until RESEND_API_KEY is configured.
set "NOVA_PORT="
for /f %%P in ('py -3.12 scripts\find_port.py') do set "NOVA_PORT=%%P"
if not defined NOVA_PORT (echo Could not find a free localhost port.& pause & exit /b 1)
echo.
echo Nova UI build: context-aware-room-followup-20261026
echo If port 8000 is occupied by an older Nova process, this launch uses another free port.
set "APP_BASE_URL=http://127.0.0.1:%NOVA_PORT%"
echo Open: http://127.0.0.1:%NOVA_PORT%
echo Admin: http://127.0.0.1:%NOVA_PORT%/admin
echo The browser will open after the updated UI is detected. Press CTRL+C to stop Nova.
echo.
start "Nova browser opener" /b py -3.12 scripts\open_browser_when_ready.py %NOVA_PORT%
py -3.12 -m uvicorn app:app --host 127.0.0.1 --port %NOVA_PORT%
pause
