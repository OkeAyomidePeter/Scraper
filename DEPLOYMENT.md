# Deployment Guide - Amazon EC2

This guide outlines the steps to deploy the Nigerian Business Outreach System on an Amazon EC2 instance (Ubuntu 22.04 LTS or Amazon Linux 2 recommended).

## 1. System Requirements & Dependencies

### Install Base Utilities

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git unzip build-essential
```

### Install Python (uv)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Install Node.js & pnpm

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pnpm
```

## 2. Project Setup

```bash
git clone <your-repo-url> outreach-system
cd outreach-system
```

### Configure Backend

```bash
cd backend
uv sync
# Manually create .env and add keys
nano .env
```

### Configure WhatsApp Service

```bash
cd ../whatsapp-service
pnpm install
# Note: Baileys is socket-based and does NOT require a browser installation.
```

## 3. Chrome & Playwright (Headless Setup)

The **Scraper** requires headless Chrome. Perform this in the backend directory.

```bash
cd ../backend
uv run playwright install --with-deps chromium
```

## 4. Systemd Services (Automatic Start)

We'll create the service files in your project directory first, then copy them to the system folder.

### A. WhatsApp Service

Create `whatsapp.service` in the root:

```ini
[Unit]
Description=WhatsApp Baileys Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Scraper/whatsapp-service
ExecStart=/usr/bin/pnpm start
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### B. Orchestrator Service (Lead Queueing)

Create `orchestrator.service` in the root:

```ini
[Unit]
Description=Outreach Orchestrator (Scraper & Queue)
After=whatsapp.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Scraper/backend
ExecStart=/home/ubuntu/.local/bin/uv run orchestrator.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### C. Sender Service (Anti-Detection)

Create `sender.service` in the root:

```ini
[Unit]
Description=Outreach Slow-Drip Sender
After=whatsapp.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Scraper/backend
ExecStart=/home/ubuntu/.local/bin/uv run sender.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### D. Telegram Bot Service (Remote Monitor)

Create `telegram.service` in the root:

```ini
[Unit]
Description=Outreach Telegram Monitor Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Scraper/backend
ExecStart=/home/ubuntu/.local/bin/uv run telegram_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### E. Enable & Start Services

```bash
# Copy all to system folder
sudo cp sender.service telegram.service /etc/systemd/system/

# Reload and start all four
sudo systemctl daemon-reload
sudo systemctl enable whatsapp orchestrator sender telegram
sudo systemctl start whatsapp orchestrator sender telegram
```

## 5. Remote Authentication (One-time)

1. Stop the service if running: `sudo systemctl stop outreach-whatsapp`
2. Run manually to scan QR: `cd whatsapp-service && pnpm start`
3. Scan QR code from the terminal locally.
4. Once "Ready", press `Ctrl+C` and restart via systemd: `sudo systemctl start outreach-whatsapp`

## 6. Operation

- Update `backend/search.txt` to change search targets.
- Monitor progress via your **Telegram Bot** using the `/stats` command.
- The system enforces a **5 messages/day** limit automatically.
