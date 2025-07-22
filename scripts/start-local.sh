#!/bin/bash
set -e

echo "Starting local Docker services (PostgreSQL + Redis)..."

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "Deployment directory: $DEPLOYMENT_DIR"

# Check if deployment directory exists
if [ ! -d "$DEPLOYMENT_DIR" ]; then
    echo "Error: deployment directory not found at $DEPLOYMENT_DIR"
    exit 1
fi

# Check if docker-compose.yml exists
if [ ! -f "$DEPLOYMENT_DIR/docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found in $DEPLOYMENT_DIR"
    exit 1
fi

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "Error: backend directory not found at $BACKEND_DIR"
    exit 1
fi

# Check if .env.local exists in project root
if [ ! -f "$PROJECT_ROOT/.env.local" ]; then
    echo "Warning: .env.local file not found in project root!"
    echo "Using default environment variables from docker-compose.yml"
fi

# Navigate to deployment directory
cd "$DEPLOYMENT_DIR"

# Stop any existing containers
echo "Stopping existing containers..."
docker-compose down --remove-orphans

# Remove old volumes to ensure fresh start
echo "Removing old database volume..."
docker volume rm deployment_postgres_data_local 2>/dev/null || true

# Start services
echo "Starting PostgreSQL and Redis services..."
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    docker-compose --env-file "$PROJECT_ROOT/.env.local" up -d
else
    docker-compose up -d
fi

echo "Waiting for services to start..."
sleep 15

# Check service health
echo "Checking service status:"
docker-compose ps

# Test database connection
echo ""
echo "Testing database connection..."
DB_NAME=${DB_NAME:-data_analysis_local}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-localpassword123}

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec postgres_local pg_isready -U $DB_USER -d $DB_NAME > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    else
        echo "Waiting for PostgreSQL... (attempt $i/30)"
        sleep 2
    fi
done

# Test Redis connection
echo "Testing Redis connection..."
if docker exec redis_local redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready yet"
fi

# Now run Django migrations
echo ""
echo "Running Django migrations..."
cd "$BACKEND_DIR"

# Check if virtual environment should be activated
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Create migrations if they don't exist
echo "Creating migrations..."
python manage.py makemigrations

# Apply migrations
echo "Applying migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser (skip if exists)..."
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Services running:"
echo "  - PostgreSQL: localhost:5433"
echo "  - Redis: localhost:6380"
echo ""
echo "Connection details:"
echo "  - Database: postgresql://postgres:localpassword123@localhost:5433/data_analysis_local"
echo "  - Redis: redis://localhost:6380/0"
echo ""
echo "Django setup:"
echo "  - All migrations applied"
echo "  - Superuser created: admin/admin123"
echo ""
echo "To view logs: cd deployment && docker-compose logs -f"
echo "To stop services: cd deployment && docker-compose down"
echo ""
echo "You can now start your Django backend with:"
echo "  cd backend && python manage.py runserver"