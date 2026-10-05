"""User input

@see https://docs.python.org/3/library/functions.html#input

User input prompts are very helpful when it comes to interactive programming. Not only in games
but also in standard file operations, you may want your user to interact with the program.
Therefore, the user needs the opportunity to be able to put in information.

The built-in input() function prints an optional prompt, waits for the user to type a line of
text and press Enter, and returns that line as a string (without the trailing newline).
"""


def greet_user():
    """Ask the user for their name and greet them."""

    # Show a prompt that tells the user we are waiting for their input.
    name = input("Please type in your name\n")

    # Build a message based on the input.
    return f"Welcome, {name}!"


def test_input(monkeypatch):
    """User input"""

    # Tests can't type on a keyboard, so we replace input() with a function that returns a
    # prepared answer. The prompt argument is accepted and ignored.
    monkeypatch.setattr('builtins.input', lambda prompt: 'Ada')

    assert greet_user() == 'Welcome, Ada!'

    # input() always returns a string, even when the user types digits. Convert it yourself
    # when you need a number.
    monkeypatch.setattr('builtins.input', lambda prompt: '42')

    age = input('How old are you?\n')

    assert age == '42'
    assert int(age) == 42
