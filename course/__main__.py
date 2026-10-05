"""Start the course with: python -m course"""

import sys

if sys.version_info < (3, 10):
    sys.exit('The Learn Python course needs Python 3.10 or newer.')

try:
    import tkinter  # noqa: F401  pylint: disable=unused-import
except ImportError:
    sys.exit(
        'The Learn Python course needs Tkinter, which is part of most Python installs.\n'
        'On Ubuntu or Debian, install it with: sudo apt install python3-tk\n'
        'On macOS, use the installer from python.org or: brew install python-tk'
    )

from course.app import main  # pylint: disable=wrong-import-position

sys.exit(main())
