#!/bin/bash

# Exit on any error
set -e

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

# Execute the main command
exec "$@"
