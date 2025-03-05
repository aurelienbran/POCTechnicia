@echo off
echo Starting Qdrant server...

:: On utilise cmd /k pour garder la fenêtre ouverte et on lance qdrant sans arguments
start "Qdrant Server" cmd /k ""D:\Projets\POC TECHNICIA\qdrant\qdrant.exe""

echo Qdrant started in a new window.
