#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Evently services..."

# Test database connection
echo "📊 Testing database connection..."
python manage.py check --database default

# Make migrations
echo "📝 Making migrations..."
python manage.py makemigrations

# Run migrations
echo "🔄 Running migrations..."
python manage.py migrate

echo "✅ Database setup complete!"

# Start Celery worker in background
echo "🔧 Starting Celery worker in background..."
celery -A Evently worker --loglevel=info --detach --pidfile=/tmp/celery.pid

# Wait a moment for Celery to start
sleep 3

# Check if Celery is running
if pgrep -f "celery.*worker" > /dev/null; then
    echo "✅ Celery worker started successfully!"
else
    echo "❌ Celery worker failed to start!"
    exit 1
fi

# Start Django application
echo "🌐 Starting Django application..."
PORT=${PORT:-8000}
exec gunicorn Evently.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-3}
