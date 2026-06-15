@echo off
echo ===========================================
echo Setting up Vivian Extension and Server...
echo ===========================================

echo.
echo [1/2] Setting up Client (VS Code Extension)
cd Client
call npm install
call npm run package
cd ..

echo.
echo [2/2] Setting up Server (Python Backend)
cd Server
echo Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Installing requirements...
pip install -r requirements.txt
cd ..

echo.
echo ===========================================
echo Setup Complete!
echo You can now install the generated .vsix file in VS Code.
echo ===========================================
pause
