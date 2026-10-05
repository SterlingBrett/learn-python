"""Tests for turning the lesson files into a course catalog."""

from pathlib import Path

import pytest

from course.catalog import load_catalog, load_lesson
from course.runner import run_code

ROOT = Path(__file__).resolve().parents[2]
CATALOG = load_catalog(ROOT)
SECTIONS = [(lesson, section) for category in CATALOG for lesson in category.lessons
            for section in lesson.sections]


def test_catalog_follows_readme_order():
    titles = [category.title for category in CATALOG]
    assert titles[0] == 'Getting Started'
    assert 'Data Types' in titles
    assert CATALOG[0].lessons[0].title == 'What is Python'
    assert CATALOG[0].lessons[0].markdown


def test_every_lesson_file_is_in_the_catalog():
    lesson_paths = {lesson.path.resolve() for category in CATALOG for lesson in category.lessons}
    for path in (ROOT / 'src').rglob('test_*.py'):
        assert path.resolve() in lesson_paths, path


def test_lessons_have_titles_and_sections():
    for category in CATALOG:
        for lesson in category.lessons:
            assert lesson.title
            assert lesson.sections or lesson.markdown, lesson.id
            for section in lesson.sections:
                assert section.title, section.id
                assert section.code.strip(), section.id


def test_section_parsing(tmp_path):
    lesson_file = tmp_path / 'test_demo.py'
    lesson_file.write_text(
        '"""Demo Topic.\n\n@see: https://example.com/demo\n\nAbout the demo.\n"""\n\n'
        'import pytest\n\nHELPER = 2\n\n\n'
        'def test_first_part():\n'
        '    """Test first part.\n\n    More words.\n    """\n\n'
        '    # A comment kept for the learner.\n'
        '    text = """line one\n    still inside the string"""\n'
        '    assert HELPER == 2  # pylint: disable=comparison-with-callable\n'
        '    assert text.endswith("    still inside the string")\n',
        encoding='utf-8')
    lesson = load_lesson(lesson_file, tmp_path)
    assert lesson.title == 'Demo Topic'
    assert lesson.links == ['https://example.com/demo']
    assert lesson.intro == 'About the demo.'
    section, = lesson.sections
    assert section.title == 'First part'
    assert section.explanation == 'More words.'
    assert section.code.startswith('# A comment kept for the learner.\n')
    assert 'pylint' not in section.code
    assert '    still inside the string"""' in section.code
    assert 'HELPER = 2' in section.setup
    assert section.checks == 2
    assert run_code(section.code, section.setup, root=tmp_path).passed


@pytest.mark.parametrize('lesson, section', SECTIONS, ids=[s.id for _, s in SECTIONS])
def test_every_section_passes_unchanged(lesson, section):
    result = run_code(section.code, section.setup, section.wrap, lesson.path.parent,
                      stdin='Ada', root=ROOT)
    assert result.passed, f'{result.message}\n{result.details}\n{result.output}'
