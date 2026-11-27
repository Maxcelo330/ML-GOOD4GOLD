@echo off
rem ============================================================================================
rem  Detector de zonas (equipo aurum80): UN doble clic y listo.
rem  - Si ya esta instalado, abre el visor.
rem  - Si falta el entorno de Python, ofrece instalarlo solo (pregunta antes de bajar nada).
rem  - EJECUTAR-VISOR.bat /verificar   solo revisa el equipo y avisa, sin abrir el visor.
rem  Cierra la ventana negra para apagar el visor. Este archivo esta escrito sin tildes a proposito.
rem ============================================================================================
setlocal EnableExtensions
title Detector de zonas - aurum80
cd /d "%~dp0"
set "RAIZ=%~dp0"
set "PY="
set "CONDA="
set "SOLO_VERIFICAR="
if /i "%~1"=="/verificar" set "SOLO_VERIFICAR=1"

:buscar
set "PY="
call :probar "%USERPROFILE%\anaconda3\envs\g4g-ml\python.exe"
call :probar "%USERPROFILE%\miniconda3\envs\g4g-ml\python.exe"
call :probar "%USERPROFILE%\miniforge3\envs\g4g-ml\python.exe"
call :probar "%USERPROFILE%\mambaforge\envs\g4g-ml\python.exe"
call :probar "%LOCALAPPDATA%\anaconda3\envs\g4g-ml\python.exe"
call :probar "%LOCALAPPDATA%\miniconda3\envs\g4g-ml\python.exe"
call :probar "%ProgramData%\anaconda3\envs\g4g-ml\python.exe"
call :probar "%ProgramData%\miniconda3\envs\g4g-ml\python.exe"
call :probar "%ProgramData%\miniforge3\envs\g4g-ml\python.exe"
if defined PY goto :revisar

echo.
echo  No encontre el entorno de Python de este proyecto (g4g-ml).
echo  Es normal la primera vez en una computadora nueva.
if defined SOLO_VERIFICAR goto :sin_entorno
call :buscar_conda
if not defined CONDA goto :bajar_miniforge

echo.
echo  Encontre conda en: %CONDA%
echo  Voy a crear el entorno g4g-ml (tarda de 5 a 15 minutos y usa cerca de 2 GB; hace falta internet).
choice /c SN /n /m "  Lo hago ahora? (S = si, N = no): "
if errorlevel 2 goto :cancelado
call "%CONDA%" env create -f "%RAIZ%02_ENTORNO\environment.yml"
if errorlevel 1 goto :fallo_entorno
goto :buscar

:bajar_miniforge
echo.
echo  Tampoco encontre conda. Puedo instalar Miniforge (un instalador gratuito de Python cientifico)
echo  solo para tu usuario, sin pedir permisos de administrador, y luego crear el entorno.
echo  Descarga unos 90 MB desde github.com y despues unos 2 GB de paquetes. Hace falta internet.
choice /c SN /n /m "  Lo hago ahora? (S = si, N = no): "
if errorlevel 2 goto :cancelado
set "INSTALADOR=%TEMP%\Miniforge3-instalador.exe"
echo  Descargando Miniforge...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe' -OutFile $env:TEMP\Miniforge3-instalador.exe"
if not exist "%INSTALADOR%" goto :fallo_descarga
echo  Instalando Miniforge en %USERPROFILE%\miniforge3 ...
start /wait "" "%INSTALADOR%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%USERPROFILE%\miniforge3
del "%INSTALADOR%" >nul 2>&1
set "CONDA=%USERPROFILE%\miniforge3\Scripts\conda.exe"
if not exist "%CONDA%" goto :fallo_descarga
echo  Creando el entorno g4g-ml (de 5 a 15 minutos)...
call "%CONDA%" env create -f "%RAIZ%02_ENTORNO\environment.yml"
if errorlevel 1 goto :fallo_entorno
goto :buscar

:revisar
echo.
echo  Python encontrado: %PY%
rem Lo mismo que hace "activar" un entorno conda: le dice a GDAL y PROJ donde estan sus datos (evita avisos molestos)
for %%D in ("%PY%") do set "ENTORNO=%%~dpD"
if exist "%ENTORNO%Library\share\gdal" set "GDAL_DATA=%ENTORNO%Library\share\gdal"
if exist "%ENTORNO%Library\share\proj" set "PROJ_DATA=%ENTORNO%Library\share\proj"
"%PY%" -I "%RAIZ%05_CODIGO\diagnostico.py" --silencioso
if errorlevel 1 goto :falta_algo
if not defined SOLO_VERIFICAR goto :abrir
echo  Todo listo. Para abrir el visor haz doble clic en EJECUTAR-VISOR.bat
goto :terminar

:abrir
echo.
echo  Preparando el visor... (cierra esta ventana negra para apagarlo)
"%PY%" -I "%RAIZ%05_CODIGO\paso8_visor_html.py"
if errorlevel 1 goto :fallo_visor
"%PY%" -I "%RAIZ%05_CODIGO\servidor_visor.py"
goto :terminar

:falta_algo
echo.
echo  Al entorno le falta algo (mira la lista de arriba).
if defined SOLO_VERIFICAR goto :terminar
choice /c SN /n /m "  Intento instalar lo que falta? (S = si, N = no): "
if errorlevel 2 goto :cancelado
"%PY%" -m pip install -r "%RAIZ%02_ENTORNO\requirements.txt"
"%PY%" -I "%RAIZ%05_CODIGO\diagnostico.py" --silencioso
if errorlevel 1 goto :fallo_entorno
goto :abrir

:sin_entorno
echo  (Modo /verificar: no se instala nada.)
goto :terminar

:cancelado
echo.
echo  Listo, no hice cambios. Cuando quieras, vuelve a abrir este archivo.
goto :terminar

:fallo_descarga
echo.
echo  No pude descargar o instalar Miniforge. Revisa la conexion a internet y vuelve a intentar.
echo  Alternativa manual: instala Miniforge desde https://github.com/conda-forge/miniforge y abre este archivo otra vez.
goto :terminar

:fallo_entorno
echo.
echo  No se pudo dejar listo el entorno. Copia el mensaje de arriba y mandaselo a quien te ayuda con el proyecto.
goto :terminar

:fallo_visor
echo.
echo  No se pudo preparar el visor. Copia el mensaje de arriba y mandaselo a quien te ayuda con el proyecto.
goto :terminar

:terminar
echo.
pause
endlocal
exit /b

rem ---------------------------------------------------------------------------------------------
:probar
if defined PY exit /b
if exist "%~1" set "PY=%~1"
exit /b

:buscar_conda
for /f "delims=" %%C in ('where conda.exe 2^>nul') do if not defined CONDA set "CONDA=%%C"
if defined CONDA exit /b
call :probar_conda "%USERPROFILE%\anaconda3\Scripts\conda.exe"
call :probar_conda "%USERPROFILE%\miniconda3\Scripts\conda.exe"
call :probar_conda "%USERPROFILE%\miniforge3\Scripts\conda.exe"
call :probar_conda "%USERPROFILE%\mambaforge\Scripts\conda.exe"
call :probar_conda "%LOCALAPPDATA%\anaconda3\Scripts\conda.exe"
call :probar_conda "%LOCALAPPDATA%\miniconda3\Scripts\conda.exe"
call :probar_conda "%ProgramData%\anaconda3\Scripts\conda.exe"
call :probar_conda "%ProgramData%\miniconda3\Scripts\conda.exe"
call :probar_conda "%ProgramData%\miniforge3\Scripts\conda.exe"
exit /b

:probar_conda
if defined CONDA exit /b
if exist "%~1" set "CONDA=%~1"
exit /b
