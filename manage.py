#!/usr/bin/env python
"""The commands of Django, such as ``python manage.py migrate``."""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pycal_dashboard.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
