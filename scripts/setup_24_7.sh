#!/bin/bash
# TradingETH Bot - 24/7 Setup Script
# This script configures the bot to run continuously as a systemd service

set -e  # Exit on error

echo "🤖 TradingETH Bot - 24/7 Setup"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root or with sudo"
    exit 1
fi

# Get the actual user who invoked sudo
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER=$SUDO_USER
else
    ACTUAL_USER=$(whoami)
fi

echo "📁 Installing for user: $ACTUAL_USER"
echo ""

# Determine bot directory
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📂 Bot directory: $BOT_DIR"

# Check if .env exists
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "❌ Error: .env file not found in $BOT_DIR"
    echo "   Please create .env file with your configuration first"
    exit 1
fi

# Check if venv exists
if [ ! -d "$BOT_DIR/.venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "   Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Create log directory
echo "📝 Creating log directory..."
mkdir -p /var/log/tradingbot
chown $ACTUAL_USER:$ACTUAL_USER /var/log/tradingbot

# Copy and configure systemd service
echo "⚙️  Configuring systemd service..."
SERVICE_FILE="/etc/systemd/system/tradingbot.service"

# Replace %USER% placeholder with actual user
sed "s/%USER%/$ACTUAL_USER/g" "$BOT_DIR/scripts/tradingbot.service.example" | \
    sed "s|/workspaces/TradingETH-|$BOT_DIR|g" > "$SERVICE_FILE"

echo "✅ Service file created: $SERVICE_FILE"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable service to start on boot
echo "🚀 Enabling service to start on boot..."
systemctl enable tradingbot.service

# Start the service
echo "▶️  Starting the bot..."
systemctl start tradingbot.service

# Wait a moment for startup
sleep 2

# Check status
echo ""
echo "📊 Service Status:"
echo "=================="
systemctl status tradingbot.service --no-pager || true

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Useful commands:"
echo "   View status:  sudo systemctl status tradingbot"
echo "   Stop bot:     sudo systemctl stop tradingbot"
echo "   Start bot:    sudo systemctl start tradingbot"
echo "   Restart bot:  sudo systemctl restart tradingbot"
echo "   View logs:    sudo journalctl -u tradingbot -f"
echo "   View logs:    sudo tail -f /var/log/tradingbot.log"
echo ""
echo "🎉 Your bot is now running 24/7!"
