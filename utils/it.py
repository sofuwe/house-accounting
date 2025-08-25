from typing import Iterator, TypeVar

T = TypeVar("T")


def iter_chunked(it: Iterator[T], size: int) -> Iterator[tuple[T, ...]]:
    chunk = []
    for item in it:
        chunk.append(item)
        if len(chunk) == size:
            yield tuple(chunk)
            chunk = []
    if chunk:
        yield tuple(chunk)
