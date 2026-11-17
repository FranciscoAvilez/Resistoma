@echo off
REM Genera CalculadoraSolucionesPediatricas.exe en la carpeta dist\
REM Requiere Python 3.10+ para Windows (https://www.python.org) con la opcion "Add to PATH".
python -m pip install --upgrade pyinstaller
python -m PyInstaller --onefile --windowed --name CalculadoraSolucionesPediatricas app.py
echo.
echo Listo: dist\CalculadoraSolucionesPediatricas.exe
pause
