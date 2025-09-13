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

echo "✅ Setup complete! Starting services..."

# Check if we should start Celery worker
if [ "$START_CELERY" = "true" ] || [ "$1" = "celery" ]; then
    echo "🔧 Starting Celery worker..."
    exec celery -A Evently worker --loglevel=info
else
    echo "🌐 Starting Django application..."
    PORT=${PORT:-8000}
    exec gunicorn Evently.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-3}
fi
