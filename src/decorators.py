import time

import prompt

from primitive_db.constants import WRAPPER_ATTRIBUTES


def _preserve_metadata(wrapper, func):
    """Сохранить имя, описание и ссылку на исходную функцию без новых библиотек."""
    for attribute in WRAPPER_ATTRIBUTES:
        if hasattr(func, attribute):
            setattr(wrapper, attribute, getattr(func, attribute))
    wrapper.__wrapped__ = func
    return wrapper


def handle_db_errors(func):
    """Вывести понятную ошибку и вернуть None вместо прерывания программы."""

    def wrapper(*args, **kwargs):
        """Вызвать операцию и вывести понятное сообщение при исключении."""
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
    """Выполнить опасное действие только после ответа y."""

    def decorator(func):
        """Добавить запрос подтверждения перед вызовом функции."""

        def wrapper(*args, **kwargs):
            """Запросить подтверждение и выполнить действие при ответе y."""
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
    """Измерить длительность вызова монотонными часами."""

    def wrapper(*args, **kwargs):
        """Выполнить функцию и вывести длительность её вызова."""
        started = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started
            print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд.")

    return _preserve_metadata(wrapper, func)


def create_cacher():
    """Создать независимый кэш в замыкании возвращаемой функции."""
    cache = {}

    def cache_result(key, value_func):
        """Вычислить отсутствующее значение и вернуть результат по ключу."""
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    cache_result.clear = cache.clear
    cache_result.contains = cache.__contains__
    return cache_result
