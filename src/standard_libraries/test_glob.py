"""File Wildcards.

@see: https://docs.python.org/3/tutorial/stdlib.html#file-wildcards

The glob module provides a function for making file lists from directory wildcard searches:
"""

import glob
import os

# Build paths relative to this lesson file so the test works from any working directory.
GLOB_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glob_files')


def test_glob():
    """File Wildcards."""

    # == operator for lists relies on the order of elements in the list.
    # In some cases (like on Linux Mint, python3.6) the glob() function returns list
    # in reverse order then  it might be expected. Thus lets sort both lists before comparison
    # using sorted() built-in function.
    assert sorted(glob.glob(os.path.join(GLOB_FILES_DIR, '*.txt'))) == sorted([
        os.path.join(GLOB_FILES_DIR, 'first_file.txt'),
        os.path.join(GLOB_FILES_DIR, 'second_file.txt'),
    ])
