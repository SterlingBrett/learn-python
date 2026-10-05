"""Formatted String Literals (f-strings)

@see: https://docs.python.org/3/tutorial/inputoutput.html#formatted-string-literals
@see: https://docs.python.org/3/reference/lexical_analysis.html#f-strings

Formatted string literals, or f-strings, let you include the value of Python expressions inside a
string by prefixing the string with f or F and writing expressions as {expression}.

They are the most readable and usually the fastest way to build strings from values, and they are
the recommended way to format strings in modern Python code.
"""

from datetime import date


def test_f_string_basics():
    """Embedding variables and expressions."""

    name = 'Ada'
    age = 36

    # Any variable in scope can be placed inside curly braces.
    assert f'{name} is {age} years old.' == 'Ada is 36 years old.'

    # Any expression works, not only variable names: arithmetic, method calls, indexing...
    assert f'Next year {name} will be {age + 1}.' == 'Next year Ada will be 37.'
    assert f'{name.upper()}' == 'ADA'
    assert f'First letter: {name[0]}' == 'First letter: A'

    # Function calls and conditional expressions work too.
    items = ['apple', 'banana', 'cherry']
    assert f'{len(items)} items' == '3 items'
    assert f'{"many" if len(items) > 2 else "few"} items' == 'many items'

    # To include a literal curly brace, double it.
    assert f'{{name}} is replaced by {name}' == '{name} is replaced by Ada'


def test_f_string_format_specifiers():
    """Format specifiers control how values are displayed.

    A format specifier follows the expression after a colon: {value:spec}. It uses the same
    mini-language as the str.format() method and the format() built-in function.
    """

    pi_value = 3.14159265

    # Fixed number of digits after the decimal point.
    assert f'{pi_value:.2f}' == '3.14'

    # Thousands separator.
    assert f'{1234567:,}' == '1,234,567'
    assert f'{1234567.891:,.2f}' == '1,234,567.89'

    # Percentages: the value is multiplied by 100 and followed by a percent sign.
    assert f'{0.256:.1%}' == '25.6%'

    # Width and alignment: < left, > right, ^ center. An optional fill character comes first.
    assert f'[{"left":<8}]' == '[left    ]'
    assert f'[{"right":>8}]' == '[   right]'
    assert f'[{"mid":^9}]' == '[   mid   ]'
    assert f'[{"mid":*^9}]' == '[***mid***]'

    # Zero padding for numbers.
    assert f'{7:03}' == '007'

    # Other number bases: binary, octal and hexadecimal.
    assert f'{255:b}' == '11111111'
    assert f'{255:o}' == '377'
    assert f'{255:x}' == 'ff'
    assert f'{255:#x}' == '0xff'

    # Specifiers can themselves contain expressions, which is handy for dynamic widths.
    width = 6
    assert f'[{42:>{width}}]' == '[    42]'

    # Objects like dates define their own specifiers.
    launch_day = date(2024, 3, 9)
    assert f'{launch_day:%Y-%m-%d}' == '2024-03-09'
    assert f'{launch_day:%d %B %Y}' == '09 March 2024'


def test_f_string_conversions():
    """Conversions choose between str() and repr() of a value.

    !s calls str() (the default), !r calls repr() and !a calls ascii().
    """

    word = 'café'

    assert f'{word}' == 'café'
    assert f'{word!r}' == "'café'"
    assert f'{word!a}' == "'caf\\xe9'"


def test_f_string_self_documenting_expressions():
    """The = specifier prints both the expression and its value.

    Writing {expression=} is a quick way to debug: the text of the expression, an equals sign
    and the repr() of the value all appear in the result.
    """

    total = 10
    count = 4

    assert f'{total=}' == 'total=10'
    assert f'{total / count=}' == 'total / count=2.5'

    # It can be combined with a format specifier.
    assert f'{total / count=:.3f}' == 'total / count=2.500'


def test_multiline_f_strings():
    """Building longer text from several f-strings."""

    name = 'Grace'
    language = 'COBOL'

    # Adjacent string literals are joined, and each one can be an f-string.
    message = (
        f'Hello, {name}! '
        f'You helped create {language}.'
    )

    assert message == 'Hello, Grace! You helped create COBOL.'

    # Triple-quoted f-strings work as well.
    report = f"""Name: {name}
Language: {language}"""

    assert report == 'Name: Grace\nLanguage: COBOL'
