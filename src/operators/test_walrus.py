"""Assignment Expressions (the walrus operator)

@see: https://docs.python.org/3/reference/expressions.html#assignment-expressions
@see: https://peps.python.org/pep-0572/

The := operator assigns a value to a variable and returns that value at the same time, so the
assignment can be used inside a larger expression. It is nicknamed the "walrus operator" because
:= looks like the eyes and tusks of a walrus.

A regular assignment (=) is a statement and cannot appear inside an if condition, a while
condition or a comprehension. The walrus operator can.
"""

import re


def test_walrus_in_if_statement():
    """Assign a value and test it in one step."""

    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

    # Without the walrus operator, len() would be called twice or need a separate line.
    if (count := len(numbers)) > 10:
        message = f'List is too long ({count} elements, expected <= 10)'
    else:
        message = 'List length is fine'

    assert message == 'List is too long (11 elements, expected <= 10)'

    # The variable stays available after the expression.
    assert count == 11

    # This pattern is common with functions that return None when nothing is found.
    if match := re.search(r'\d+', 'Order number 1234 shipped'):
        order_number = match.group()
    else:
        order_number = None

    assert order_number == '1234'


def test_walrus_in_while_loop():
    """Read values until there are none left."""

    lines = ['first', 'second', '']
    received = []

    # Each time around, the next line is assigned to line and checked. The loop stops when an
    # empty line (which is falsy) is returned.
    while line := lines.pop(0):
        received.append(line)

    assert received == ['first', 'second']


def test_walrus_in_comprehension():
    """Reuse a computed value inside a comprehension."""

    def slow_square(number):
        return number * number

    numbers = [1, 2, 3, 4, 5]

    # slow_square() is called once per number: the result is used in the filter and in the output.
    big_squares = [square for number in numbers if (square := slow_square(number)) > 5]

    assert big_squares == [9, 16, 25]


def test_walrus_needs_parentheses():
    """The walrus operator has very low precedence, so parentheses are often required."""

    value = 15

    # Here the comparison runs first and is_big gets the bool result.
    if is_big := value > 10:
        pass

    assert is_big is True

    # Here the parentheses make size get the number, which is then compared.
    if (size := value) > 10:
        pass

    assert size == 15
