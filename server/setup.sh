#!/usr/bin/env bash
# Mein Deutsch reminder server installer for kingdom-ai.
# Run:  curl -fsSL https://michaelpeccia.github.io/mein-deutsch/server/setup.sh | bash
set -e
DIR="$HOME/push-server"
URL="https://michaelpeccia.github.io/mein-deutsch/server/push_server.py"

echo "== Installing Python venv support (may ask for your password) =="
sudo apt-get install -y python3-venv curl >/dev/null

echo "== Setting up $DIR =="
mkdir -p "$DIR"
cd "$DIR"
curl -fsSL "$URL" -o push_server.py
[ -d venv ] || python3 -m venv venv
venv/bin/pip install --quiet --upgrade pip pywebpush

echo "== Creating the service =="
sudo tee /etc/systemd/system/mein-deutsch-push.service >/dev/null <<UNIT
[Unit]
Description=Mein Deutsch daily reminder push server
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python $DIR/push_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now mein-deutsch-push
sudo systemctl restart mein-deutsch-push
sleep 2
echo "== Checking =="
curl -s http://localhost:8097/health && echo && echo "Reminder server is running on port 8097."
