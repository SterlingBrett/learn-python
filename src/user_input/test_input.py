"""User input

@see https://docs.python.org/3/library/functions.html#input

User input prompts are very helpful when it comes to interactive programming. Not only in games
but also in standard file operations, you may want your user to interact with the program.
Therefore, the user needs the opportunity to be able to put in information.
"""


def user_input():
    """Input prompt"""

    # Printing statement to signal the user that we are waiting for input.
    name = input("Please type in your name\n")

    # Printing a message based on the input.
    print(f"Welcome, {name}!")


def test_user_input(monkeypatch, capsys):
    """Test the input prompt without a real keyboard

    pytest's monkeypatch fixture replaces the built-in input() with a function that returns a
    prepared answer, and the capsys fixture captures everything printed to the screen.
    """

    monkeypatch.setattr('builtins.input', lambda prompt: 'Ada')

    user_input()

    assert capsys.readouterr().out == 'Welcome, Ada!\n'
