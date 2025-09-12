#!/bin/bash

# Exit on any error

echo "Starting Evently application setup..."

# Test database connection
echo "Testing database connection..."
python manage.py check --database default

# Make migrations
echo "Making migrations..."
python manage.py makemigrations

# Run migrations
echo "Running migrations..."
python manage.py migrate


echo "Setup complete! Starting application..."

# Start the application
PORT=${PORT:-8000}
exec gunicorn Evently.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-3}
echo "Application started!"
