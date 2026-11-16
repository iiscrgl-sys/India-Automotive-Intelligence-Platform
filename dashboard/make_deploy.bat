@echo off
REM Builds IAIP\deploy\ for Streamlit Community Cloud. Run again after every data refresh.
cd /d "%~dp0"
set PY=C:\Users\Arka\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PY%" set PY=python
"%PY%" -c "import pandas, pyarrow" 2>nul || "%PY%" -m pip install pandas pyarrow
"%PY%" make_deploy.py
pause
