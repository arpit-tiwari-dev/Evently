#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Evently application setup..."

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

# Test Redis connection first
echo "🔍 Testing Redis connection..."
python -c "
import os
import redis
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Evently.settings')
import django
django.setup()

try:
    r = redis.from_url(settings.CELERY_BROKER_URL)
    r.ping()
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"

# Start Celery worker in background
echo "🔧 Starting Celery worker in background..."
celery -A Evently worker --loglevel=info > /tmp/celery.log 2>&1 &
CELERY_PID=$!

# Wait a moment for Celery to start
sleep 3

# Check if Celery is running
if ps -p $CELERY_PID > /dev/null; then
    echo "✅ Celery worker started successfully! PID: $CELERY_PID"
    echo "📋 Celery logs:"
    tail -n 5 /tmp/celery.log
else
    echo "❌ Celery worker failed to start!"
    echo "📋 Celery error logs:"
    cat /tmp/celery.log
    exit 1
fi

# Start Django application (don't use exec - let it run in foreground)
echo "🌐 Starting Django application..."
PORT=${PORT:-8000}
gunicorn Evently.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-3}
