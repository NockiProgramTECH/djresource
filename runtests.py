import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()

from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    TestRunner = get_runner(settings)
    failures = TestRunner(verbosity=1, interactive=False).run_tests(["tests"])
    sys.exit(bool(failures))
