@echo off
echo Starting all POC TECHNICIA components...
echo.

echo Step 1: Starting Qdrant
call "%~dp0\1-start-qdrant.bat"
timeout /t 5 > nul
echo.

echo Step 2: Starting Backend
call "%~dp0\2-start-backend.bat"
timeout /t 5 > nul
echo.

echo Step 3: Starting Frontend
call "%~dp0\3-start-frontend.bat"
echo.

echo All components started successfully!
echo - Qdrant: http://localhost:6333
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3001
echo.
echo You can check if Qdrant is running with: Invoke-WebRequest -Uri http://localhost:6333 -UseBasicParsing
echo.

pause
