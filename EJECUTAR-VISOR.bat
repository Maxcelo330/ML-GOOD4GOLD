@echo off
rem Abre el visor de zonas con analisis de bloques (doble clic). Cierra esta ventana para apagarlo.
cd /d "%~dp0"
set PY=%USERPROFILE%\anaconda3\envs\g4g-ml\python.exe
if not exist "%PY%" (
  echo No se encontro el entorno g4g-ml en %PY%
  pause
  exit /b 1
)
"%PY%" -I 05_CODIGO\paso8_visor_html.py
"%PY%" -I 05_CODIGO\servidor_visor.py
pause
