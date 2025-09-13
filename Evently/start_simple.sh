#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting Evently services (Simple Mode)..."

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

# Start both services using supervisord
echo "🔧 Starting services with supervisord..."

# Create supervisord config
cat > /tmp/supervisord.conf << EOF
[supervisord]
nodaemon=true
user=root

[program:celery]
command=celery -A Evently worker --loglevel=info
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/celery.err.log
stdout_logfile=/var/log/celery.out.log

[program:gunicorn]
command=gunicorn Evently.wsgi:application --bind 0.0.0.0:8000 --workers 3
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/gunicorn.err.log
stdout_logfile=/var/log/gunicorn.out.log
EOF

# Install supervisord if not available
if ! command -v supervisord &> /dev/null; then
    echo "📦 Installing supervisord..."
    pip install supervisor
fi

# Start supervisord
exec supervisord -c /tmp/supervisord.conf
