"""Type Hints

@see: https://docs.python.org/3/library/typing.html
@see: https://typing.python.org/en/latest/

Type hints describe what kinds of values variables, parameters and return values are expected to
hold. Python itself does not check them while the program runs: a function annotated to take an
int will still accept a string. Instead, they help people reading the code, editors offering
autocompletion, and static type checkers such as mypy or pyright that find mistakes before the
code runs.

This lesson builds on the Function Annotations lesson, which shows where the annotations are
stored.
"""

from collections.abc import Callable, Iterable
from typing import Any, TypedDict, TypeVar, get_type_hints


def greet(name: str, excited: bool = False) -> str:
    """Parameters are annotated after a colon, the return value after an arrow."""
    return f'Hello, {name}{"!" if excited else "."}'


def total_length(words: list[str]) -> int:
    """Built-in collections can be used as generic types: list[str] is a list of strings."""
    return sum(len(word) for word in words)


def count_words(text: str) -> dict[str, int]:
    """dict[str, int] maps string keys to integer values."""
    counts: dict[str, int] = {}
    for word in text.split():
        counts[word] = counts.get(word, 0) + 1
    return counts


def min_max(numbers: Iterable[float]) -> tuple[float, float]:
    """Iterable accepts any iterable, such as a list, tuple, set or generator.

    tuple[float, float] is a tuple with exactly two floats.
    """
    values = list(numbers)
    return min(values), max(values)


def find_index(items: list[str], target: str) -> int | None:
    """The | operator combines types: this function returns an int or None."""
    if target in items:
        return items.index(target)
    return None


def apply_twice(function: Callable[[int], int], value: int) -> int:
    """Callable[[int], int] is a function that takes one int and returns an int."""
    return function(function(value))


def describe(value: Any) -> str:
    """Any switches type checking off for a value. Use it sparingly."""
    return type(value).__name__


T = TypeVar('T')


def first(items: list[T]) -> T:
    """A generic function.

    The type variable T links the parameter and the return value: given a list[int] the result
    is an int, given a list[str] the result is a str.

    Python 3.12 added a shorter syntax that needs no TypeVar:

        def first[T](items: list[T]) -> T: ...
    """
    return items[0]


# A type alias gives a long or repeated type a short, descriptive name. Python 3.12 added the
# type statement for this: type Coordinates = tuple[float, float]
Coordinates = tuple[float, float]


def distance_from_origin(point: Coordinates) -> float:
    """Type aliases are used just like the type they stand for."""
    x, y = point
    return (x ** 2 + y ** 2) ** 0.5


class Movie(TypedDict):
    """TypedDict describes dictionaries with a fixed set of keys and value types."""

    title: str
    year: int


def movie_label(movie: Movie) -> str:
    """Type checkers know movie['year'] is an int here."""
    return f'{movie["title"]} ({movie["year"]})'


def test_basic_type_hints():
    """Simple annotations."""

    assert greet('Ada') == 'Hello, Ada.'
    assert greet('Ada', excited=True) == 'Hello, Ada!'

    # Variables can be annotated too.
    language: str = 'Python'
    year: int = 1991

    assert f'{language} {year}' == 'Python 1991'

    # The hints are available at runtime through typing.get_type_hints().
    assert get_type_hints(greet) == {'name': str, 'excited': bool, 'return': str}


def test_type_hints_are_not_enforced():
    """Python does not check types at runtime."""

    # greet() is annotated to take a str, but an int still works because f-strings accept any
    # value. A static type checker would report this call as an error.
    assert greet(42) == 'Hello, 42.'  # type: ignore[arg-type]


def test_collection_types():
    """Generic collection types."""

    assert total_length(['to', 'be']) == 4
    assert count_words('a b a') == {'a': 2, 'b': 1}
    assert min_max([3, 1, 2]) == (1, 3)
    assert min_max(number * 2 for number in range(4)) == (0, 6)


def test_optional_and_union_types():
    """Values that can have more than one type."""

    colors = ['red', 'green']

    assert find_index(colors, 'green') == 1
    assert find_index(colors, 'blue') is None


def test_callable_and_any():
    """Functions as values, and opting out of type checking."""

    assert apply_twice(lambda number: number * 3, 2) == 18
    assert describe(3.5) == 'float'
    assert describe([]) == 'list'


def test_generics_and_aliases():
    """Generic functions and type aliases."""

    assert first([10, 20]) == 10
    assert first(['x', 'y']) == 'x'

    assert distance_from_origin((3.0, 4.0)) == 5.0


def test_typed_dict():
    """Typed dictionaries."""

    movie: Movie = {'title': 'Metropolis', 'year': 1927}

    assert movie_label(movie) == 'Metropolis (1927)'

    # At runtime a TypedDict is an ordinary dict.
    assert isinstance(movie, dict)
