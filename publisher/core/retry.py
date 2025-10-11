"""Утилиты повторного выполнения операций."""

from typing import Iterable, Type

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


def retry_on_exceptions(exceptions: Iterable[Type[BaseException]]):
    """Создаёт декоратор с тремя попытками и экспоненциальной паузой."""
    exceptions_tuple = tuple(exceptions)

    return retry(
        retry=retry_if_exception_type(exceptions_tuple),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
