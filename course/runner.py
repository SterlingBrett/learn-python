"""Run a learner's code safely and report whether the lesson's checks pass.

The GUI calls run_code(), which starts a separate Python process running
this module. That keeps the window responsive, lets an endless loop be
stopped by a timeout, and means nothing the learner does can break the app.

A lesson section is the body of a test_* function. To keep the meaning of
``return``, ``global`` and ``nonlocal`` exactly as in the lesson file, the
learner's code is wrapped back into a function before it runs, without
changing any line numbers.
"""

import ast
import json
import linecache
import os
import subprocess
import sys
import tempfile
import types
from dataclasses import dataclass
from pathlib import Path

USER_FILE = '<your code>'
SETUP_FILE = '<lesson setup>'
DEFAULT_TIMEOUT = 10
MAX_OUTPUT = 50_000
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RunResult:
    """What happened when the learner pressed Run."""

    status: str  # 'passed', 'failed' or 'error'
    message: str
    output: str = ''
    line: int = 0
    details: str = ''

    @property
    def passed(self):
        """True when the code ran and every check held."""
        return self.status == 'passed'


def run_code(code, setup='', wrap=True, lesson_dir=None, stdin='',
             timeout=DEFAULT_TIMEOUT, root=REPO_ROOT):
    """Run learner code in a child Python process and return a RunResult."""
    with tempfile.TemporaryDirectory(prefix='learn-python-') as tmp:
        payload_path = Path(tmp) / 'payload.json'
        result_path = Path(tmp) / 'result.json'
        payload_path.write_text(json.dumps({
            'code': code,
            'setup': setup,
            'wrap': wrap,
            'lesson_dir': str(lesson_dir) if lesson_dir else '',
        }), encoding='utf-8')

        env = dict(os.environ)
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONPATH'] = os.pathsep.join(
            filter(None, [str(REPO_ROOT), env.get('PYTHONPATH', '')]))
        try:
            completed = subprocess.run(
                [sys.executable, '-m', 'course.runner', str(payload_path), str(result_path)],
                input=stdin if stdin.endswith('\n') or not stdin else stdin + '\n',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(root),
                env=env,
                timeout=timeout,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            output = error.output or ''
            if isinstance(output, bytes):
                output = output.decode('utf-8', 'replace')
            return RunResult(
                status='error',
                message=f'Your code took longer than {timeout} seconds and was stopped.',
                output=truncate(output),
                details='Look for a loop that never ends, such as "while True" without a break.',
            )

        output = truncate(completed.stdout)
        try:
            data = json.loads(result_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return RunResult(
                status='error',
                message='Python stopped unexpectedly before your code finished.',
                output=output,
                details=f'Exit code {completed.returncode}.',
            )
        return RunResult(
            status=data.get('status', 'error'),
            message=data.get('message', ''),
            output=output,
            line=data.get('line', 0),
            details=data.get('details', ''),
        )


def truncate(text):
    """Keep very chatty programs from flooding the output pane."""
    if len(text) > MAX_OUTPUT:
        return text[:MAX_OUTPUT] + '\n... (output cut off) ...\n'
    return text


# ---------------------------------------------------------------------------
# Everything below runs inside the child process.
# ---------------------------------------------------------------------------

def _install_pytest_fallback():
    """Lessons use pytest.raises; provide a small stand-in if pytest is missing."""
    try:
        import pytest  # noqa: F401  pylint: disable=import-outside-toplevel,unused-import
        return
    except ImportError:
        pass

    class _Raises:
        def __init__(self, expected, match=None):
            self.expected = expected
            self.match = match
            self.value = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                raise AssertionError(f'DID NOT RAISE {self.expected}')
            if not issubclass(exc_type, self.expected):
                return False
            self.value = exc
            return True

    module = types.ModuleType('pytest')
    module.raises = _Raises
    sys.modules['pytest'] = module


def _remember_source(filename, text):
    """Let tracebacks show the learner's lines even though they are not in a file."""
    lines = text.splitlines(keepends=True)
    linecache.cache[filename] = (len(text), None, lines, filename)


def _wrap_in_function(tree):
    """Put the module's statements inside ``def __lesson__():`` keeping line numbers."""
    wrapper = ast.parse('def __lesson__():\n    pass\n')
    function = wrapper.body[0]
    if tree.body:
        function.body = tree.body
        function.lineno = tree.body[0].lineno
        function.end_lineno = max(node.end_lineno for node in tree.body)
    ast.fix_missing_locations(wrapper)
    return wrapper


def _describe_error(error, code_lines):
    """Turn an exception into (status, message, line, details) for the learner."""
    frames = [(filename, number) for filename, number in _walk_tb(error.__traceback__)
              if filename in (USER_FILE, SETUP_FILE)]
    user_lines = [line for filename, line in frames if filename == USER_FILE]
    line = user_lines[-1] if user_lines else 0
    source = code_lines[line - 1].strip() if 0 < line <= len(code_lines) else ''

    details = []
    if frames:
        details.append('Traceback (most recent call last):')
        for filename, number in frames:
            where = 'your code' if filename == USER_FILE else 'lesson setup'
            details.append(f'  Line {number} of {where}')
            text = linecache.getline(filename, number).strip()
            if text:
                details.append(f'    {text}')
    details.append(f'{type(error).__name__}: {error}'.rstrip(': '))

    is_check = isinstance(error, AssertionError) or type(error).__name__ == 'Failed'
    if is_check:
        where = f' on line {line}' if line else ''
        message = f'A check failed{where}'
        if source:
            message += f': {source}'
        if str(error):
            message += f'\n{error}'
        return 'failed', message, line, '\n'.join(details)

    where = f' on line {line}' if line else ''
    message = f'{type(error).__name__}{where}: {error}'
    return 'error', message, line, '\n'.join(details)


def _walk_tb(tb):
    while tb is not None:
        yield tb.tb_frame.f_code.co_filename, tb.tb_lineno
        tb = tb.tb_next


def _child_main(payload_path, result_path):
    payload = json.loads(Path(payload_path).read_text(encoding='utf-8'))
    code = payload['code']
    setup = payload['setup']
    code_lines = code.splitlines()

    def finish(status, message, line=0, details=''):
        sys.stdout.flush()
        Path(result_path).write_text(json.dumps({
            'status': status, 'message': message, 'line': line, 'details': details,
        }), encoding='utf-8')

    if payload['lesson_dir']:
        sys.path.insert(0, payload['lesson_dir'])
    _install_pytest_fallback()
    _remember_source(USER_FILE, code)
    _remember_source(SETUP_FILE, setup)

    try:
        tree = ast.parse(code, USER_FILE)
        if payload['wrap']:
            tree = _wrap_in_function(tree)
        program = compile(tree, USER_FILE, 'exec')
    except (SyntaxError, ValueError) as error:
        line = getattr(error, 'lineno', 0) or 0
        if not isinstance(error, SyntaxError):
            finish('error', f'Python could not compile this code: {error}')
            return
        finish('error', f'SyntaxError on line {line}: {error.msg}', line,
               'Python could not read this line. Check for a missing colon, bracket or quote, '
               'and that the indentation lines up.')
        return

    namespace = {'__name__': '__main__', '__builtins__': __builtins__}
    try:
        if setup.strip():
            exec(compile(setup, SETUP_FILE, 'exec'), namespace)  # pylint: disable=exec-used
        exec(program, namespace)  # pylint: disable=exec-used
        if payload['wrap']:
            namespace['__lesson__']()
    except SystemExit:
        pass
    except BaseException as error:  # pylint: disable=broad-except
        if isinstance(error, EOFError):
            finish('error', 'Your code asked for input but none was given.', 0,
                   'Type what your program should read into the "Program input" box, '
                   'one line for each input() call, then press Run again.')
            return
        finish(*_describe_error(error, code_lines))
        return

    checks = sum(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(code)))
    if checks == 1:
        finish('passed', 'The check passed.')
    elif checks:
        finish('passed', f'All {checks} checks passed.')
    else:
        finish('passed', 'Your code ran without errors.')


if __name__ == '__main__':
    _child_main(sys.argv[1], sys.argv[2])
