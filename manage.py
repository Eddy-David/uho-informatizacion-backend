#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    # ``python manage.py test`` usa el entorno de pruebas (PostgreSQL + hasher
    # rápido), igual que pytest; y ``test`` debe poder crear su base de datos.
    if len(sys.argv) > 1 and sys.argv[1] in {"test", "pytest"}:
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.testing"
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
