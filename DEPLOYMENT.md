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
# Install Chrome for Baileys
pnpm exec puppeteer browsers install chrome
```

## 3. Chrome & Playwright (Headless Setup)

EC2 instances require specific dependencies for headless Chrome.

```bash
cd ../backend
uv run playwright install-deps
uv run playwright install chromium
```

## 4. Systemd Services (Automatic Start)

We will create two services: one for the WhatsApp gateway and one for the Orchestrator.

### A. WhatsApp Service

Create `/etc/systemd/system/outreach-whatsapp.service`:

```ini
[Unit]
Description=WhatsApp Baileys Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/outreach-system/whatsapp-service
ExecStart=/usr/bin/pnpm start
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### B. Orchestrator Bot

Create `/etc/systemd/system/outreach-orchestrator.service`:

```ini
[Unit]
Description=Outreach Orchestrator & Telegram Bot
After=outreach-whatsapp.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/outreach-system/backend
ExecStart=/home/ubuntu/.cargo/bin/uv run orchestrator.py
Restart=always
```

### Enable Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable outreach-whatsapp
sudo systemctl start outreach-whatsapp
```

## 5. Remote Authentication (One-time)

1. Stop the service if running: `sudo systemctl stop outreach-whatsapp`
2. Run manually to scan QR: `cd whatsapp-service && pnpm start`
3. Scan QR code from the terminal locally.
4. Once "Ready", press `Ctrl+C` and restart via systemd: `sudo systemctl start outreach-whatsapp`

## 6. Operation

- Update `backend/search.txt` to change search targets.
- Monitor progress via your **Telegram Bot** using the `/stats` command.
- The system enforces a **100 messages/day** limit automatically.
