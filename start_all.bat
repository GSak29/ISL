@echo off
echo Starting ISL and V2A Applications...

:: Start ISL App (Port 5000)
start "ISL Detection App (Port 5000)" cmd /k "cd isl && python app.py"

:: Start V2A App (Port 3000)
start "Voice to Animation App (Port 3000)" cmd /k "cd v2a && python app.py"

echo ===================================================
echo Applications are starting in separate windows.
echo ISL App: http://127.0.0.1:5000/
echo V2A App: http://127.0.0.1:3000/
echo ===================================================
echo You can close this window now, or keep it open.
pause
