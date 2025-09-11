# Docker Deployment Guide for Evently

This guide explains how to deploy the Evently application using Docker and PostgreSQL.

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
   Edit the `.env` file with your desired configuration.

3. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - API: http://localhost:8000
   - Admin panel: http://localhost:8000/admin

## Environment Configuration

The application uses environment variables for configuration. Copy `env.example` to `.env` and modify as needed:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=evently_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
```

## Docker Services

### PostgreSQL Database (`db`)
- **Image:** postgres:15
- **Port:** 5432
- **Database:** evently_db
- **User:** postgres
- **Password:** postgres (change in production)

### Django Application (`web`)
- **Build:** From local Dockerfile
- **Port:** 8000
- **Dependencies:** Depends on healthy database

## Production Deployment

### 1. Security Considerations

**Update the `.env` file for production:**
```env
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=your-secure-database-password
```

### 2. SSL/HTTPS Setup

For production, consider using a reverse proxy like Nginx with SSL certificates:

```yaml
# Add to docker-compose.yml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web
```

### 3. Database Backup

Create a backup script:

```bash
#!/bin/bash
# backup.sh
docker-compose exec db pg_dump -U postgres evently_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 4. Static Files

For production, configure static file serving:

```yaml
# Add to docker-compose.yml
  nginx:
    image: nginx:alpine
    volumes:
      - static_volume:/app/staticfiles
    depends_on:
      - web
```

## Development Commands

### Run in development mode:
```bash
docker-compose up
```

### Run in background:
```bash
docker-compose up -d
```

### View logs:
```bash
docker-compose logs -f
```

### Stop services:
```bash
docker-compose down
```

### Rebuild after code changes:
```bash
docker-compose up --build
```

### Access Django shell:
```bash
docker-compose exec web python manage.py shell
```

### Run Django management commands:
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic
```

## Database Management

### Create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

### Reset database (WARNING: This will delete all data):
```bash
docker-compose down -v
docker-compose up --build
```

## Troubleshooting

### Common Issues:

1. **Port already in use:**
   - Change ports in `docker-compose.yml`
   - Or stop conflicting services

2. **Database connection issues:**
   - Ensure PostgreSQL service is healthy
   - Check environment variables
   - Verify network connectivity

3. **Permission issues:**
   - Check file permissions
   - Ensure Docker has access to the project directory

### View service status:
```bash
docker-compose ps
```

### Check service health:
```bash
docker-compose exec db pg_isready -U postgres
```

## Scaling

To scale the web service:

```bash
docker-compose up --scale web=3
```

Note: You'll need a load balancer for multiple web instances.

## Monitoring

### View resource usage:
```bash
docker stats
```

### View container logs:
```bash
docker-compose logs web
docker-compose logs db
```

## Cleanup

### Remove all containers and volumes:
```bash
docker-compose down -v
```

### Remove images:
```bash
docker-compose down --rmi all
```

### Complete cleanup:
```bash
docker system prune -a
```

## API Endpoints

Once running, the API will be available at:
- Base URL: http://localhost:8000
- Admin: http://localhost:8000/admin
- API Documentation: Check the API_DOCUMENTATION.md file

## Support

For issues or questions:
1. Check the logs: `docker-compose logs`
2. Verify environment configuration
3. Ensure all services are healthy: `docker-compose ps`
