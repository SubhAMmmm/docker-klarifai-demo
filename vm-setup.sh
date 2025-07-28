#!/bin/bash

# VM Setup Script - Run this on your Azure VM
# This script installs Docker, Docker Compose, and sets up the environment

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt install git -y

# Create application directory
sudo mkdir -p /opt/klarifai
sudo chown $USER:$USER /opt/klarifai

# Create logs directory
mkdir -p /opt/klarifai/logs

# Install nginx (optional, for reverse proxy)
sudo apt install nginx -y

# Create a deploy user (for GitHub Actions)
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Generate SSH key for deploy user
sudo -u deploy ssh-keygen -t rsa -b 4096 -f /home/deploy/.ssh/id_rsa -N ""

echo "VM setup complete!"
echo "Don't forget to:"
echo "1. Log out and log back in for Docker group changes to take effect"
echo "2. Configure your firewall to allow ports 80, 443, and your app port"
echo "3. Set up your domain/DNS to point to this VM"