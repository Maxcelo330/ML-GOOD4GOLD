@echo off
rem Abre la presentacion animada con un servidor local (necesario: abrir el .html con doble clic NO funciona).
rem Deja esta ventana abierta mientras ves la presentacion. Para cerrar el servidor, cierra la ventana.
rem Si el puerto esta ocupado por otro programa, usa el siguiente libre (asi no sale el error 404 de un servidor viejo).
setlocal
cd /d "%~dp0"
set "PY=%USERPROFILE%\anaconda3\envs\g4g-ml\python.exe"
if not exist "%PY%" set "PY=python"
set /a PUERTO=8811
:buscar_puerto
netstat -ano | findstr /R /C:":%PUERTO% .*LISTENING" >nul
if errorlevel 1 goto :listo
set /a PUERTO+=1
goto :buscar_puerto
:listo
echo Presentacion en http://127.0.0.1:%PUERTO%/presentacion.html
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 2; Start-Process 'http://127.0.0.1:%PUERTO%/presentacion.html?auto=1&fs=0'"
"%PY%" -I -m http.server %PUERTO% --bind 127.0.0.1
pause
