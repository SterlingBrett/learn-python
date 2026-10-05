"""Turn the lesson files in src/ into a course catalog.

Every lesson in this repository is a Python file whose module docstring
introduces the topic and whose test_* functions each illustrate one
sub-topic with comments and assertions. This module parses those files
(without importing them) into Category -> Lesson -> Section objects that
the GUI can display and run.

The order and titles of lessons come from the table of contents in
README.md, so the course follows the same path as the repository.
"""

import ast
import inspect
import io
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

PYLINT_LINE_RE = re.compile(r'^\s*#\s*pylint:')
PYLINT_INLINE_RE = re.compile(r'\s+#\s*pylint:[^#]*$')
LINK_RE = re.compile(r'^#?\s*@\w*:?\s*(https?://\S+)\s*$')
TOC_CATEGORY_RE = re.compile(r'^\d+\.\s+\*\*(.+?)\*\*')
TOC_LESSON_RE = re.compile(r'^\s+-\s+\[(.+?)\]\((src/[^)]+)\)(.*)$')


@dataclass
class Section:
    """One sub-topic of a lesson: an explanation plus code the learner can run."""

    id: str
    title: str
    explanation: str
    code: str
    setup: str = ''
    wrap: bool = True
    checks: int = 0
    fixtures: tuple = ()


@dataclass
class Lesson:
    """One lesson file: either runnable Python sections or a Markdown page."""

    id: str
    title: str
    summary: str
    path: Path
    intro: str = ''
    links: list = field(default_factory=list)
    sections: list = field(default_factory=list)
    markdown: str = ''


@dataclass
class Category:
    """A group of lessons, such as "Data Types"."""

    title: str
    lessons: list = field(default_factory=list)


def load_catalog(root):
    """Build the course catalog from the repository at ``root``."""
    root = Path(root)
    categories = []
    listed = set()

    readme = root / 'README.md'
    if readme.exists():
        for line in readme.read_text(encoding='utf-8').splitlines():
            if line.startswith('## ') and categories:
                break  # The table of contents is over.
            category_match = TOC_CATEGORY_RE.match(line)
            if category_match:
                categories.append(Category(category_match.group(1).strip()))
                continue
            lesson_match = TOC_LESSON_RE.match(line)
            if lesson_match and categories:
                title, rel_path, rest = lesson_match.groups()
                path = root / rel_path
                if not path.exists():
                    continue
                lesson = load_lesson(path, root, title=clean_title(title),
                                     summary=clean_summary(rest))
                if lesson:
                    categories[-1].lessons.append(lesson)
                    listed.add(path.resolve())

    # Lessons that exist on disk but are missing from the README still show up.
    extra = {}
    for path in sorted((root / 'src').rglob('test_*.py')):
        if path.resolve() in listed:
            continue
        lesson = load_lesson(path, root)
        if lesson:
            title = path.parent.name.replace('_', ' ').title()
            extra.setdefault(title, Category(title)).lessons.append(lesson)
    categories.extend(extra.values())

    return [category for category in categories if category.lessons]


def load_lesson(path, root, title=None, summary=''):
    """Parse one lesson file. Returns None if the file cannot be read."""
    path = Path(path)
    lesson_id = path.relative_to(root).as_posix()
    try:
        source = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None

    if path.suffix == '.md':
        heading = re.search(r'^#\s+(.+)$', source, re.MULTILINE)
        return Lesson(
            id=lesson_id,
            title=title or (heading.group(1).strip() if heading else path.stem),
            summary=summary,
            path=path,
            markdown=source,
        )

    try:
        tree = ast.parse(source.expandtabs(4))
    except SyntaxError:
        return None
    source = source.expandtabs(4)
    lines = source.splitlines()

    doc_title, intro, links = split_module_docstring(source, tree)
    lesson = Lesson(
        id=lesson_id,
        title=title or doc_title or path.stem,
        summary=summary,
        path=path,
        intro=intro,
        links=links,
    )

    tests = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')]

    removed = set()
    docstring = get_docstring_node(tree)
    if docstring:
        removed.update(range(docstring.lineno, docstring.end_lineno + 1))

    if not tests:
        # A lesson with no test functions runs as a plain script.
        code = keep_lines(lines, removed).strip('\n') + '\n'
        lesson.sections.append(Section(
            id=lesson_id + '::main',
            title=lesson.title,
            explanation='',
            code=code,
            wrap=False,
            checks=count_checks(code),
        ))
        return lesson

    spans = []
    for node in tests:
        first = node.decorator_list[0].lineno if node.decorator_list else node.lineno
        last = extend_over_comments(lines, node.end_lineno, node.col_offset)
        spans.append((node, first, last))
        removed.update(range(first, last + 1))

    removed.update(number for number, line in enumerate(lines, start=1)
                   if PYLINT_LINE_RE.match(line))
    setup = tidy_blank_lines(keep_lines(lines, removed))

    for node, _, last in spans:
        func_doc = get_docstring_node(node)
        sec_title, explanation = split_function_docstring(source, func_doc, node.name)
        code = function_body(source, lines, node, func_doc, last)
        lesson.sections.append(Section(
            id=f'{lesson_id}::{node.name}',
            title=sec_title,
            explanation=explanation,
            code=code,
            setup=setup,
            checks=count_checks(code),
            fixtures=tuple(arg.arg for arg in node.args.args),
        ))
    return lesson


def get_docstring_node(node):
    """Return the string node used as the docstring of ``node``, if any."""
    body = getattr(node, 'body', None)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[0]
    return None


def raw_docstring(source, node):
    """Return a docstring exactly as written (escapes such as \\n stay visible)."""
    if node is None:
        return ''
    segment = ast.get_source_segment(source, node.value) or ''
    start = min((i for i in (segment.find('"'), segment.find("'")) if i >= 0), default=-1)
    if start < 0:
        return inspect.cleandoc(node.value.value)
    quote = segment[start:start + 3]
    if quote not in ('"""', "'''"):
        quote = segment[start]
    inner = segment[start + len(quote):len(segment) - len(quote)]
    return inspect.cleandoc(inner)


def split_module_docstring(source, tree):
    """Split a module docstring into (title, intro text, list of links)."""
    text = raw_docstring(source, get_docstring_node(tree))
    if not text:
        return '', '', []
    first, _, rest = text.partition('\n')
    links = []
    body = []
    for line in rest.splitlines():
        match = LINK_RE.match(line.strip())
        if match:
            links.append(match.group(1))
        else:
            body.append(line)
    return clean_title(first), tidy_blank_lines('\n'.join(body)), links


def split_function_docstring(source, node, name):
    """Return (section title, explanation) for a test function."""
    text = raw_docstring(source, node)
    first, _, rest = text.partition('\n')
    title = clean_title(first)
    title = re.sub(r'^Test(ing)?\s+', '', title)
    if not title:
        title = name[len('test_'):].replace('_', ' ')
    title = title[:1].upper() + title[1:]
    return title, rest.strip()


def function_body(source, lines, node, docstring, last):
    """Return the body of a test function, dedented to start at column 0."""
    if docstring is not None:
        start = docstring.end_lineno + 1
    else:
        start = node.body[0].lineno
        # Keep comments written just above the first statement.
        while start - 1 > node.lineno and lines[start - 2].strip().startswith('#'):
            start -= 1

    protected = string_continuation_lines(source)
    indent = node.body[0].col_offset
    out = []
    for number in range(start, last + 1):
        line = lines[number - 1]
        if number in protected:
            out.append(line)  # Inside a multi-line string: keep it exactly.
            continue
        if PYLINT_LINE_RE.match(line):
            continue  # Linter settings are noise for learners.
        line = PYLINT_INLINE_RE.sub('', line)
        if line[:indent].strip() == '':
            out.append(line[indent:])
        else:
            out.append(line.lstrip())
    return '\n'.join(out).strip('\n') + '\n'


def string_continuation_lines(source):
    """Line numbers that continue a multi-line string (their text is data, not code)."""
    protected = set()
    string_types = {tokenize.STRING}
    for name in ('FSTRING_MIDDLE', 'FSTRING_END', 'TSTRING_MIDDLE', 'TSTRING_END'):
        if hasattr(tokenize, name):
            string_types.add(getattr(tokenize, name))
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in string_types and token.end[0] > token.start[0]:
                protected.update(range(token.start[0] + 1, token.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        pass
    return protected


def extend_over_comments(lines, last, col_offset):
    """Include indented comment lines that trail the end of a function."""
    number = last
    while number < len(lines):
        line = lines[number]
        if line.strip() == '':
            number += 1
            continue
        indent = len(line) - len(line.lstrip())
        if line.strip().startswith('#') and indent > col_offset:
            last = number + 1
            number += 1
            continue
        break
    return last


def keep_lines(lines, removed):
    """Return the source with the given 1-based line numbers removed."""
    return '\n'.join(line for number, line in enumerate(lines, start=1)
                     if number not in removed)


def tidy_blank_lines(text):
    """Strip outer blank lines and collapse runs of blank lines into one."""
    text = re.sub(r'\n\s*\n(\s*\n)+', '\n\n', text)
    return text.strip('\n')


def count_checks(code):
    """Count the assert statements in a piece of code."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0
    return sum(isinstance(node, ast.Assert) for node in ast.walk(tree))


def clean_title(text):
    """Tidy a title taken from a README link or a docstring's first line."""
    text = text.strip().replace('`', '')
    return text.rstrip('.').strip()


def clean_summary(text):
    """Tidy the text that follows a lesson link in the README."""
    text = text.strip()
    if text.startswith('(') and text.endswith(')'):
        text = text[1:-1]
    return text.strip()


def has_setup_code(setup):
    """True if setup code does more than comment or import pytest (test plumbing)."""
    return any(line.strip() and not line.strip().startswith('#')
               and line.strip() != 'import pytest'
               for line in setup.splitlines())
