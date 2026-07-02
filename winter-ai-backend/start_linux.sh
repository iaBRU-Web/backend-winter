#!/usr/bin/env bash
cd "$(dirname "$0")"

echo "============================================"
echo "  Winter AI Backend - starting up..."
echo "============================================"

if ! command -v python3 &> /dev/null; then
    echo "Python 3 was not found. Please install it (e.g. sudo apt install python3 python3-pip)."
    read -p "Press Enter to close..."
    exit 1
fi

python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo ""
echo "Starting Winter AI on http://localhost:10000"
echo "Swagger docs available at http://localhost:10000/docs"
echo "Press CTRL+C to stop the server."
echo ""

( sleep 2 && xdg-open "http://localhost:10000/docs" >/dev/null 2>&1 ) &
python3 -m uvicorn api.index:app --host 0.0.0.0 --port 10000
