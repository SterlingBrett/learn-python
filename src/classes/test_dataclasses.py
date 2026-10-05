"""Data Classes

@see: https://docs.python.org/3/library/dataclasses.html

Many classes exist mostly to hold data: a point with x and y, a book with a title and an author.
Writing such classes by hand means repeating every attribute in __init__(), and then writing
__repr__() and __eq__() so the objects print nicely and can be compared.

The @dataclass decorator from the dataclasses module writes those methods for you. You only list
the fields together with their type annotations.
"""

from dataclasses import FrozenInstanceError, asdict, dataclass, field, replace

import pytest


@dataclass
class Point:
    """A point on a plane.

    The fields are declared as class-level annotations. The decorator generates
    __init__(self, x, y), __repr__() and __eq__() from them.
    """

    x: int
    y: int


@dataclass
class Book:
    """A book with optional fields.

    Fields with default values must come after fields without them, just like function
    parameters. Mutable defaults such as lists must use field(default_factory=...), so every
    instance gets its own new list instead of sharing one.
    """

    title: str
    author: str
    pages: int = 0
    tags: list[str] = field(default_factory=list)

    def is_long(self) -> bool:
        """Data classes are regular classes, so they can have methods too."""
        return self.pages > 500


@dataclass(frozen=True)
class Color:
    """An immutable data class.

    With frozen=True, assigning to a field after creation raises an error. Frozen instances can
    also be used as dictionary keys or set members because they are hashable.
    """

    red: int
    green: int
    blue: int


@dataclass(order=True)
class Version:
    """A data class that supports <, <=, > and >=.

    With order=True, instances are compared as if they were tuples of their fields, in the order
    the fields are declared.
    """

    major: int
    minor: int
    patch: int


@dataclass
class Rectangle:
    """A data class with a computed field.

    __post_init__() runs right after the generated __init__(), which is the place to validate
    input or compute values from other fields. field(init=False) keeps area out of __init__().
    """

    width: float
    height: float
    area: float = field(init=False)

    def __post_init__(self):
        if self.width < 0 or self.height < 0:
            raise ValueError('Width and height must not be negative')
        self.area = self.width * self.height


def test_dataclass_basics():
    """Generated __init__, __repr__ and __eq__."""

    point = Point(1, 2)

    # __init__() was generated, so the fields are set from the arguments.
    assert point.x == 1
    assert point.y == 2

    # Keyword arguments work as well.
    assert Point(y=2, x=1) == point

    # __repr__() shows the class name and every field.
    assert repr(point) == 'Point(x=1, y=2)'

    # __eq__() compares the fields, not the identity of the objects.
    assert Point(1, 2) == Point(1, 2)
    assert Point(1, 2) != Point(2, 1)
    assert Point(1, 2) is not Point(1, 2)

    # Instances are mutable by default.
    point.x = 10
    assert point == Point(10, 2)


def test_dataclass_defaults():
    """Default values and default factories."""

    book = Book('Dune', 'Frank Herbert')

    assert book.pages == 0
    assert book.tags == []
    assert not book.is_long()

    # Each instance gets its own list thanks to default_factory.
    other_book = Book('Emma', 'Jane Austen', 474)
    book.tags.append('sci-fi')

    assert book.tags == ['sci-fi']
    assert other_book.tags == []

    assert Book('Middlemarch', 'George Eliot', pages=880).is_long()


def test_frozen_dataclass():
    """Immutable data classes."""

    white = Color(255, 255, 255)

    with pytest.raises(FrozenInstanceError):
        white.red = 0  # type: ignore[misc]

    # Use dataclasses.replace() to create a modified copy instead.
    cyan = replace(white, red=0)

    assert cyan == Color(0, 255, 255)
    assert white == Color(255, 255, 255)

    # Frozen instances are hashable.
    names = {white: 'white', cyan: 'cyan'}
    assert names[Color(0, 255, 255)] == 'cyan'


def test_ordered_dataclass():
    """Ordering comparisons."""

    assert Version(1, 2, 0) < Version(1, 10, 0)
    assert Version(2, 0, 0) > Version(1, 99, 99)

    versions = [Version(1, 10, 0), Version(1, 2, 3), Version(0, 9, 9)]

    assert sorted(versions) == [Version(0, 9, 9), Version(1, 2, 3), Version(1, 10, 0)]
    assert max(versions) == Version(1, 10, 0)


def test_post_init():
    """Computed fields and validation."""

    rectangle = Rectangle(3, 4)

    assert rectangle.area == 12

    with pytest.raises(ValueError):
        Rectangle(-1, 4)


def test_asdict():
    """Converting a data class to a dictionary.

    asdict() is useful when you need plain data, for example to save it as JSON.
    """

    book = Book('Dune', 'Frank Herbert', 412, ['sci-fi'])

    assert asdict(book) == {
        'title': 'Dune',
        'author': 'Frank Herbert',
        'pages': 412,
        'tags': ['sci-fi'],
    }
