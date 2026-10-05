"""Documentation Strings.

@see: https://docs.python.org/3/tutorial/controlflow.html#documentation-strings

Here are some conventions about the content and formatting of documentation strings.

The first line should always be a short, concise summary of the object’s purpose. For brevity,
it should not explicitly state the object’s name or type, since these are available by other means
(except if the name happens to be a verb describing a function’s operation). This line should begin
with a capital letter and end with a period.

If there are more lines in the documentation string, the second line should be blank, visually
separating the summary from the rest of the description. The following lines should be one or more
paragraphs describing the object’s calling conventions, its side effects, etc.
"""

import inspect


def do_nothing():
    """Do nothing, but document it.

    No, really, it doesn't do anything.
    """
    pass


def test_function_documentation_string():
    """Test documentation string."""

    # Tools that display documentation strip the indentation that comes from the source code. This
    # is done using the following convention. The first non-blank line after the first line of the
    # string determines the amount of indentation for the entire documentation string. (We can’t
    # use the first line since it is generally adjacent to the string’s opening quotes so its
    # indentation is not apparent in the string literal.) Whitespace “equivalent” to this
    # indentation is then stripped from the start of all lines of the string.
    #
    # Since Python 3.13 the compiler already strips this indentation from __doc__. In older
    # versions __doc__ keeps it. inspect.getdoc() returns the cleaned-up text in every version, so
    # it is the reliable way to read a docstring.

    assert inspect.getdoc(do_nothing) == (
        'Do nothing, but document it.\n'
        '\n'
        "No, really, it doesn't do anything."
    )
