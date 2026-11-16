@echo off
REM IAIP dashboard: double-click to start. Close this window to stop the dashboard.
cd /d "%~dp0"
set PY=C:\Users\Arka\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PY%" set PY=python
"%PY%" -c "import streamlit, plotly, pyarrow" 2>nul || (echo Installing streamlit, plotly, pyarrow - first time only... & "%PY%" -m pip install streamlit plotly pyarrow)
echo Starting the IAIP dashboard at http://localhost:8501
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8501"
"%PY%" -m streamlit run app.py
pause
