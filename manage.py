#!/usr/bin/env python
import os
import sys
import site

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spending.settings")

    prev_sys_path = list(sys.path)
    site.addsitedir('vendor-local/lib/python')

    new_sys_path = []
    for item in list(sys.path):
        if item not in prev_sys_path:
            new_sys_path.append(item)
            sys.path.remove(item)
    sys.path[:0] = new_sys_path

    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
