# Evently Docker Deployment Guide

This guide will help you deploy the Evently Django application using Docker containers.

## Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

## Quick Start

1. **Clone the repository and navigate to the project directory:**
   ```bash
   cd Evently
   ```

2. **Create environment file:**
   ```bash
   cp env.example .env
   ```

3. **Edit the `.env` file with your configuration:**
   ```bash
   # Django Settings
   DEBUG=False
   SECRET_KEY=your-very-secure-secret-key-here
   ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

   # Database Configuration
   DB_NAME=evently_db
   DB_USER=postgres
   DB_PASSWORD=your-secure-password
   DB_HOST=localhost
   DB_PORT=5432
   ```

4. **Build and start the containers:**
   ```bash
   docker-compose up --build
   ```

5. **Access the application:**
   - Application: http://localhost:8000
   - Admin panel: http://localhost:8000/admin (admin/admin123)

## Docker Services

The Docker setup includes three services:

### 1. Database (PostgreSQL)
- **Image:** postgres:15
- **Port:** 5432
- **Data persistence:** Uses Docker volume `postgres_data`

### 2. Web Application (Django)
- **Port:** 8000
- **Features:**
  - Automatic dependency installation
  - Database migrations
  - Static file collection
  - Superuser creation
  - Gunicorn WSGI server

### 3. Nginx (Reverse Proxy)
- **Port:** 80
- **Features:**
  - Static file serving
  - Gzip compression
  - Load balancing
  - Health checks

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Django debug mode | `False` |
| `SECRET_KEY` | Django secret key | Required |
| `ALLOWED_HOSTS` | Allowed hosts (comma-separated) | `localhost,127.0.0.1` |
| `DB_NAME` | Database name | `evently_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `password` |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `5432` |

## Commands

### Development
```bash
# Start services in development mode
docker-compose up

# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production
```bash
# Build and start in production mode
docker-compose -f docker-compose.yml up --build -d

# Update application
docker-compose pull
docker-compose up -d
```

### Database Operations
```bash
# Access database shell
docker-compose exec db psql -U postgres -d evently_db

# Create new migration
docker-compose exec web python manage.py makemigrations

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

### Application Management
```bash
# Access Django shell
docker-compose exec web python manage.py shell

# Collect static files
docker-compose exec web python manage.py collectstatic

# Run tests
docker-compose exec web python manage.py test
```

## Data Persistence

- **Database data:** Stored in Docker volume `postgres_data`
- **Static files:** Stored in Docker volume `static_volume`
- **Application logs:** Available via `docker-compose logs`

## Security Considerations

1. **Change default passwords** in production
2. **Use strong SECRET_KEY** for Django
3. **Set DEBUG=False** in production
4. **Configure ALLOWED_HOSTS** properly
5. **Use HTTPS** in production (configure SSL certificates)

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Check what's using the port
   netstat -tulpn | grep :8000
   
   # Change port in docker-compose.yml
   ports:
     - "8001:8000"  # Use port 8001 instead
   ```

2. **Database connection issues:**
   ```bash
   # Check database logs
   docker-compose logs db
   
   # Restart database service
   docker-compose restart db
   ```

3. **Permission issues:**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs web
docker-compose logs db
docker-compose logs nginx

# Follow logs in real-time
docker-compose logs -f web
```

## Production Deployment

For production deployment:

1. **Use environment-specific settings**
2. **Configure proper logging**
3. **Set up SSL certificates**
4. **Use a production database**
5. **Configure backup strategies**
6. **Set up monitoring and alerting**

## Backup and Restore

### Database Backup
```bash
# Create backup
docker-compose exec db pg_dump -U postgres evently_db > backup.sql

# Restore backup
docker-compose exec -T db psql -U postgres evently_db < backup.sql
```

### Volume Backup
```bash
# Backup volumes
docker run --rm -v evently_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Support

For issues and questions:
1. Check the logs: `docker-compose logs`
2. Verify environment variables
3. Ensure all services are healthy: `docker-compose ps`
4. Check Docker and Docker Compose versions
