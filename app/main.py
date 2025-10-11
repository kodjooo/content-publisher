"""Совместимость с прежней точкой входа."""

from publisher.run import main as publisher_main


def main() -> None:
    """Запускает сервис публикации через модуль app."""
    publisher_main()


if __name__ == "__main__":
    main()
