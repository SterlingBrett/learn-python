"""A smoke test that opens the window and clicks through the course."""

import os

import pytest

tk = pytest.importorskip('tkinter')

# pylint: disable=wrong-import-position
from course.app import REPO_ROOT, CourseApp  # noqa: E402
from course.catalog import load_catalog  # noqa: E402
from course.progress import Progress  # noqa: E402


@pytest.fixture(name='app')
def fixture_app(tmp_path):
    if os.name != 'nt' and not os.environ.get('DISPLAY') and os.uname().sysname != 'Darwin':
        pytest.skip('No display available')
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip('No display available')
    root.withdraw()
    app = CourseApp(root, load_catalog(REPO_ROOT), Progress(tmp_path / 'progress.json'))
    yield app
    root.destroy()


def test_visits_every_section(app):
    for index in range(len(app.stops)):
        app.go_to(index)
        assert app.editor.get_code() == app.stops[index].original_code


def test_run_marks_section_done(app):
    stop_index = next(index for index, stop in enumerate(app.stops) if stop.section)
    app.go_to(stop_index)
    app.run()
    while app.running:
        app.root.update()
        app.root.after(20)
    assert app.stops[stop_index].id in app.progress.completed
    assert app.banner.cget('text').startswith('✓')


def test_drafts_survive_navigation(app):
    app.go_to(5)
    app.editor.set_code('x = 1\n')
    app.next()
    app.previous()
    assert app.editor.get_code() == 'x = 1\n'
