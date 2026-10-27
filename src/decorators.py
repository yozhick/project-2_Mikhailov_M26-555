import time

import prompt

from primitive_db.constants import WRAPPER_ATTRIBUTES


def _preserve_metadata(wrapper, func):
    """Сохранение метаданных и ссылки на исходную функцию."""
    for attribute in WRAPPER_ATTRIBUTES:
        if hasattr(func, attribute):
            setattr(wrapper, attribute, getattr(func, attribute))
    wrapper.__wrapped__ = func
    return wrapper


def handle_db_errors(func):
    """Обработка исключений операций базы данных с выводом сообщений об ошибках."""

    def wrapper(*args, **kwargs):
        """
        Выполнение операции с обработкой исключений и выводом сообщений об ошибках.
        """
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print(
                "Ошибка: Файл данных не найден. "
                "Возможно, база данных не инициализирована."
            )
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except OSError as error:
            print(f"Ошибка работы с файлами: {error}")
        except Exception as error:
            print(f"Произошла непредвиденная ошибка: {error}")
        return None

    return _preserve_metadata(wrapper, func)


def confirm_action(action_name):
    """Фабрика декораторов подтверждения выполнения операции."""

    def decorator(func):
        """Добавление запроса подтверждения перед вызовом функции."""

        def wrapper(*args, **kwargs):
            """Выполнение операции после подтверждения пользователя."""
            try:
                answer = prompt.string(
                    f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ',
                    empty=True,
                )
            except (EOFError, KeyboardInterrupt):
                print()
                answer = None
            if answer != "y":
                print("Операция отменена.")
                return None
            return func(*args, **kwargs)

        return _preserve_metadata(wrapper, func)

    return decorator


def log_time(func):
    """Измерение времени выполнения функции."""

    def wrapper(*args, **kwargs):
        """Выполнение функции с выводом времени её выполнения."""
        started = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started
            print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд.")

    return _preserve_metadata(wrapper, func)


def create_cacher():
    """Создание функции кэширования с хранением результатов в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        """Получение результата из кэша или вычисление и сохранение нового значения."""
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    cache_result.clear = cache.clear
    cache_result.contains = cache.__contains__
    return cache_result
