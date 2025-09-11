#!/usr/bin/env python
import os
import sys
import subprocess


def run(cmd: list[str]) -> int:
    return subprocess.call(cmd, env=os.environ.copy())


def ensure_superuser() -> None:
    username = os.getenv("DJANGO_SUPERUSER_USERNAME")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
    if not (username and email and password):
        return

    # Create superuser idempotently
    code = (
        "import os;"
        "from django.contrib.auth import get_user_model;"
        "User=get_user_model();"
        "u=os.getenv('DJANGO_SUPERUSER_USERNAME');"
        "e=os.getenv('DJANGO_SUPERUSER_EMAIL');"
        "p=os.getenv('DJANGO_SUPERUSER_PASSWORD');"
        "(User.objects.filter(username=u).exists() or (User.objects.create_superuser(u,e,p) is None)) and None"
    )
    run([sys.executable, "manage.py", "shell", "-c", code])


def main() -> int:
    # Run migrations
    rc = run([sys.executable, "manage.py", "migrate", "--noinput"]) 
    if rc != 0:
        return rc

    # Ensure superuser if env vars provided
    ensure_superuser()

    # Start gunicorn
    port = os.getenv("PORT", "8000")
    return run(["gunicorn", "Evently.wsgi:application", "--bind", f"0.0.0.0:{port}"])


if __name__ == "__main__":
    sys.exit(main())


