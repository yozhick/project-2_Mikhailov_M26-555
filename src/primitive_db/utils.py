import json
import os

from primitive_db.constants import (
    DATA_DIR,
    INVALID_FILENAME_CHARACTERS,
    IS_WINDOWS,
    JSON_INDENT,
    TEMP_SUFFIX_BYTES,
    TEXT_ENCODING,
    WINDOWS_CONTROL_CHARACTER_LIMIT,
    WINDOWS_INVALID_FILENAME_CHARACTERS,
    WINDOWS_RESERVED_NAMES,
)


def validate_table_name(table_name):
    """Проверка допустимости имени таблицы с учётом ограничений операционной системы."""
    invalid_common = (
        not table_name.strip()
        or table_name in {".", ".."}
        or any(char in INVALID_FILENAME_CHARACTERS for char in table_name)
    )
    invalid_windows = IS_WINDOWS and (
        any(
            char in WINDOWS_INVALID_FILENAME_CHARACTERS
            or ord(char) < WINDOWS_CONTROL_CHARACTER_LIMIT
            for char in table_name
        )
        or table_name.endswith((" ", "."))
        or table_name.split(".")[0].upper() in WINDOWS_RESERVED_NAMES
    )
    if invalid_common or invalid_windows:
        raise ValueError(f'Некорректное имя таблицы: "{table_name}".')


def _table_filepath(table_name):
    """Формирование пути к файлу данных таблицы с проверкой её имени."""
    validate_table_name(table_name)
    return os.path.join(DATA_DIR, f"{table_name}.json")


def _save_json(filepath, data):
    """Сохранение данных в JSON-файл."""
    filepath = os.path.abspath(filepath)
    directory = os.path.dirname(filepath)
    os.makedirs(directory, exist_ok=True)
    suffix = os.urandom(TEMP_SUFFIX_BYTES).hex()
    candidate = os.path.join(directory, f".{os.path.basename(filepath)}.{suffix}.tmp")
    temporary_path = None
    try:
        with open(candidate, mode="x", encoding=TEXT_ENCODING) as file:
            temporary_path = candidate
            json.dump(data, file, ensure_ascii=False, indent=JSON_INDENT)
            file.write("\n")
        os.replace(temporary_path, filepath)
        temporary_path = None
    finally:
        if temporary_path is not None:
            os.remove(temporary_path)


def load_metadata(filepath):
    """Загрузка метаданных базы данных из JSON-файла."""
    try:
        with open(filepath, encoding=TEXT_ENCODING) as file:
            data = json.load(file)
    except FileNotFoundError:
        return {}

    if not isinstance(data, dict):
        raise ValueError("Метаданные должны содержать JSON-объект.")
    return data


def save_metadata(filepath, data):
    """Сохранение метаданных базы данных в JSON-файл."""
    _save_json(filepath, data)


def load_table_data(table_name):
    """Загрузка данных таблицы из JSON-файла."""
    try:
        with open(_table_filepath(table_name), encoding=TEXT_ENCODING) as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f'Некорректный формат данных таблицы "{table_name}".')
    return data


def save_table_data(table_name, data):
    """Сохранение данных таблицы в JSON-файл."""
    _save_json(_table_filepath(table_name), data)


def remove_table_data(table_name):
    """Удаление файла данных таблицы."""
    try:
        os.remove(_table_filepath(table_name))
    except FileNotFoundError:
        pass
