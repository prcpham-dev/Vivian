#!/bin/bash
echo "==========================================="
echo "Setting up Vivian Extension and Server..."
echo "==========================================="

echo ""
echo "[1/2] Setting up Client (VS Code Extension)"
cd "$(dirname "$0")" || exit
npm install
npm run package

echo ""
echo "[2/2] Setting up Server (Python Backend)"
cd "$(dirname "$0")/Server" || exit
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Installing requirements..."
pip install -r ../requirements.txt
cd ..

echo ""
echo "==========================================="
echo "Setup Complete!"
echo "You can now install the generated .vsix file in VS Code."
echo "==========================================="

# Keep the terminal window open so the user can read the output
echo "Press any key to close this window..."
read -r -n 1
