"""Tests for running learner code."""

from course.runner import run_code


def test_passing_checks_and_output():
    result = run_code('print("hi")\nassert 1 + 1 == 2\nassert True\n')
    assert result.passed
    assert result.message == 'All 2 checks passed.'
    assert result.output == 'hi\n'


def test_failed_check_reports_the_line():
    result = run_code('x = 1\n\nassert x == 2\n')
    assert result.status == 'failed'
    assert result.line == 3
    assert 'assert x == 2' in result.message


def test_error_reports_type_and_line():
    result = run_code('items = []\nitems[3]\n')
    assert result.status == 'error'
    assert result.line == 2
    assert result.message.startswith('IndexError on line 2')


def test_syntax_error():
    result = run_code('if True\n    pass\n')
    assert result.status == 'error'
    assert result.message.startswith('SyntaxError on line 1')


def test_endless_loop_is_stopped():
    result = run_code('while True:\n    pass\n', timeout=2)
    assert result.status == 'error'
    assert 'longer than 2 seconds' in result.message


def test_input_comes_from_program_input_box():
    code = 'name = input()\nprint("Hi", name)\n'
    assert run_code(code, wrap=False, stdin='Ada').output == 'Hi Ada\n'
    missing = run_code(code, wrap=False)
    assert missing.status == 'error'
    assert 'input' in missing.message


def test_wrapped_code_keeps_function_semantics():
    code = (
        'value = "outer"\n'
        'def change():\n'
        '    nonlocal value\n'
        '    value = "changed"\n'
        'change()\n'
        'assert value == "changed"\n'
        'return\n'
    )
    assert run_code(code).passed


def test_setup_code_is_available():
    result = run_code('assert double(2) == 4\n', setup='def double(x):\n    return x * 2\n')
    assert result.passed


def test_pytest_raises_works():
    code = 'import pytest\nwith pytest.raises(ZeroDivisionError):\n    1 / 0\n'
    assert run_code(code).passed


def test_monkeypatch_and_capsys_fixtures():
    code = (
        "monkeypatch.setattr('builtins.input', lambda prompt: 'Ada')\n"
        "print('Hi', input('name? '))\n"
        "assert capsys.readouterr().out == 'Hi Ada\\n'\n"
    )
    result = run_code(code, fixtures=('monkeypatch', 'capsys'))
    assert result.passed, result.message
    assert result.output == 'Hi Ada\n'


def test_unknown_fixture_is_explained():
    result = run_code('assert tmp_path\n', fixtures=('tmp_path',))
    assert result.status == 'error'
    assert 'tmp_path' in result.message
