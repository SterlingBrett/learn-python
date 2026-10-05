"""MATCH statement

@see: https://docs.python.org/3/tutorial/controlflow.html#match-statements
@see: https://peps.python.org/pep-0636/

A match statement takes an expression and compares its value to successive patterns given as one
or more case blocks. Only the first pattern that matches gets executed.

It looks like the switch statement found in other languages, but it can do much more: patterns
can check the shape of sequences, dictionaries and objects and pull values out of them at the same
time. Match statements were added in Python 3.10.
"""

from dataclasses import dataclass


def http_status(status):
    """Literal patterns compare the subject with a value.

    The wildcard pattern _ always matches, so it works like the else part of an if statement.
    Several literals can be combined with | ("or").
    """
    match status:
        case 200:
            return 'OK'
        case 404:
            return 'Not Found'
        case 401 | 403:
            return 'Not Allowed'
        case _:
            return 'Something else'


def describe_command(command):
    """Sequence patterns match lists and tuples of a certain shape.

    Names in a pattern are capture patterns: they match anything and bind the matching value to
    that name. *rest captures the remaining items as a list.
    """
    match command.split():
        case []:
            return 'Nothing to do'
        case ['look']:
            return 'You look around'
        case ['go', direction]:
            return f'You go {direction}'
        case ['drop', *objects]:
            return f'You drop {len(objects)} objects'
        case _:
            return f'Unknown command: {command}'


def describe_number(number):
    """A guard is an if clause after a pattern. The case runs only if the guard is true."""
    match number:
        case 0:
            return 'zero'
        case int() if number < 0:
            return 'negative integer'
        case int():
            return 'positive integer'
        case float():
            return 'float'
        case _:
            return 'not a number'


def describe_event(event):
    """Mapping patterns match dictionaries that contain the given keys.

    Extra keys in the dictionary are ignored. Values can be matched against nested patterns.
    """
    match event:
        case {'type': 'click', 'position': (x, y)}:
            return f'Click at {x}, {y}'
        case {'type': 'key', 'key': str() as key}:
            return f'Key {key} pressed'
        case {'type': event_type}:
            return f'Unhandled {event_type} event'
        case _:
            return 'Not an event'


@dataclass
class Point:
    """A point used to demonstrate class patterns."""

    x: int
    y: int


def where_is(point):
    """Class patterns check the type of the subject and match its attributes."""
    match point:
        case Point(x=0, y=0):
            return 'Origin'
        case Point(x=0, y=y):
            return f'On the Y axis at {y}'
        case Point(x=x, y=0):
            return f'On the X axis at {x}'
        case Point():
            return 'Somewhere else'
        case _:
            return 'Not a point'


def test_literal_patterns():
    """Matching exact values."""

    assert http_status(200) == 'OK'
    assert http_status(404) == 'Not Found'
    assert http_status(403) == 'Not Allowed'
    assert http_status(500) == 'Something else'


def test_sequence_patterns():
    """Matching the shape of lists."""

    assert describe_command('') == 'Nothing to do'
    assert describe_command('look') == 'You look around'
    assert describe_command('go north') == 'You go north'
    assert describe_command('drop sword shield key') == 'You drop 3 objects'
    assert describe_command('dance wildly') == 'Unknown command: dance wildly'


def test_guards_and_type_patterns():
    """Matching types with extra conditions."""

    assert describe_number(0) == 'zero'
    assert describe_number(-5) == 'negative integer'
    assert describe_number(7) == 'positive integer'
    assert describe_number(2.5) == 'float'
    assert describe_number('7') == 'not a number'


def test_mapping_patterns():
    """Matching dictionaries."""

    assert describe_event({'type': 'click', 'position': (10, 20)}) == 'Click at 10, 20'
    assert describe_event({'type': 'key', 'key': 'q', 'shift': False}) == 'Key q pressed'
    assert describe_event({'type': 'scroll'}) == 'Unhandled scroll event'
    assert describe_event('click') == 'Not an event'


def test_class_patterns():
    """Matching objects."""

    assert where_is(Point(0, 0)) == 'Origin'
    assert where_is(Point(0, 5)) == 'On the Y axis at 5'
    assert where_is(Point(3, 0)) == 'On the X axis at 3'
    assert where_is(Point(1, 1)) == 'Somewhere else'
    assert where_is((0, 0)) == 'Not a point'
