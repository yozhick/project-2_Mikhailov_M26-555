import json
import os

from primitive_db.constants import (
    CONTROL_CHARACTER_LIMIT,
    DATA_DIR,
    INVALID_FILENAME_CHARACTERS,
    JSON_INDENT,
    TEMP_SUFFIX_BYTES,
    TEXT_ENCODING,
    WINDOWS_RESERVED_NAMES,
)


def validate_table_name(table_name):
    """Имя таблицы должно подходить для отдельного файла в Windows и Linux."""
    if (
        not table_name.strip()
        or table_name in {".", ".."}
        or any(
            char in INVALID_FILENAME_CHARACTERS or ord(char) < CONTROL_CHARACTER_LIMIT
            for char in table_name
        )
        or table_name.endswith((" ", "."))
        or table_name.split(".")[0].upper() in WINDOWS_RESERVED_NAMES
    ):
        raise ValueError(f'Некорректное имя таблицы: "{table_name}".')


def _table_filepath(table_name):
    """Получить путь к файлу таблицы после проверки её имени."""
    validate_table_name(table_name)
    return os.path.join(DATA_DIR, f"{table_name}.json")


def _save_json(filepath, data):
    """Сначала записать временный файл, затем заменить целевой целиком."""
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
    """Загрузить метаданные или вернуть пустой словарь для новой базы."""
    try:
        with open(filepath, encoding=TEXT_ENCODING) as file:
            data = json.load(file)
    except FileNotFoundError:
        return {}

    if not isinstance(data, dict):
        raise ValueError("Метаданные должны содержать JSON-объект.")
    return data


def save_metadata(filepath, data):
    """Сохранить имена таблиц и их столбцы в JSON-файл."""
    _save_json(filepath, data)


def load_table_data(table_name):
    """Загрузить строки таблицы; отсутствующий файл означает пустую таблицу."""
    try:
        with open(_table_filepath(table_name), encoding=TEXT_ENCODING) as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError(f'Некорректный формат данных таблицы "{table_name}".')
    return data


def save_table_data(table_name, data):
    """Сохранить строки в data/<имя_таблицы>.json."""
    _save_json(_table_filepath(table_name), data)


def remove_table_data(table_name):
    """При удалении таблицы удалить и её строки."""
    try:
        os.remove(_table_filepath(table_name))
    except FileNotFoundError:
        pass
