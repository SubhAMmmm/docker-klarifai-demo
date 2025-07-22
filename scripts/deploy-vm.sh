#!/bin/bash
set -e

echo "🚀 Starting VM database deployment..."

# Configuration
APP_DIR="$HOME/klarifai-db"
BACKUP_DIR="$APP_DIR/backups"
REPO_URL="https://github.com/yourusername/your-repo.git"  # Update this
BRANCH="main"

# Create directories
mkdir -p $APP_DIR
mkdir -p $BACKUP_DIR
cd $APP_DIR

# Clone or update repository
if [ -d ".git" ]; then
    echo "📥 Updating repository..."
    git fetch origin
    git reset --hard origin/$BRANCH
else
    echo "📥 Cloning repository..."
    git clone -b $BRANCH $REPO_URL .
fi

# Copy deployment files
echo "📋 Setting up configuration files..."
cp deployment/vm-docker-compose.yml docker-compose.yml
cp deployment/init.sql init.sql

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "🔧 Creating environment file..."
    cat > .env << 'EOF'
# Database Configuration
DB_NAME=data_analysis_prod
DB_USER=postgres
DB_PASSWORD=SecureDBPassword123!

# Redis Configuration  
REDIS_PASSWORD=SecureRedisPassword123!

# Backup Configuration
BACKUP_RETENTION_DAYS=7
EOF
    echo "⚠️  Please update .env with secure passwords!"
fi

# Create backup script
cat > backup-script.sh << 'EOF'
#!/bin/bash
BACKUP_FILE="/backups/backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h postgres -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE
echo "Backup created: $BACKUP_FILE"

# Clean old backups
find /backups -name "backup_*.sql" -mtime +${BACKUP_RETENTION_DAYS:-7} -delete
EOF
chmod +x backup-script.sh

# Backup existing database if running
if docker-compose ps | grep -q postgres_prod; then
    echo "💾 Creating database backup..."
    docker-compose exec -T postgres_prod pg_dump -U postgres data_analysis_prod > $BACKUP_DIR/pre_deploy_$(date +%Y%m%d_%H%M%S).sql || echo "No existing database to backup"
fi

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose down || true

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker-compose pull

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Health check
echo "🏥 Performing health checks..."
if docker-compose exec -T postgres_prod pg_isready -U postgres -d data_analysis_prod; then
    echo "✅ PostgreSQL is healthy"
else
    echo "❌ PostgreSQL health check failed"
    exit 1
fi

if docker-compose exec -T redis_prod redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis health check failed"
    exit 1
fi

# Show status
echo "📊 Service status:"
docker-compose ps

# Show logs
echo "📝 Recent logs:"
docker-compose logs --tail=20

echo "🎉 VM database deployment completed successfully!"

# Setup auto-start service
if [ ! -f /etc/systemd/system/klarifai-db.service ]; then
    echo "⚙️  Setting up auto-start service..."
    sudo tee /etc/systemd/system/klarifai-db.service > /dev/null << EOF
[Unit]
Description=Klarifai Database Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=$(whoami)
Group=docker

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable klarifai-db
    echo "✅ Auto-start service configured"
fi