import json
import os
import tempfile
from pathlib import Path

DATA_DIR = Path("data")


def validate_table_name(table_name):
    """Имя таблицы должно подходить для отдельного файла в Windows и Linux."""
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update(
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    if (
        not table_name.strip()
        or table_name in {".", ".."}
        or any(char in '<>:"/\\|?*' or ord(char) < 32 for char in table_name)
        or table_name.endswith((" ", "."))
        or table_name.split(".")[0].upper() in reserved
    ):
        raise ValueError(f'Некорректное имя таблицы: "{table_name}".')


def _table_filepath(table_name):
    validate_table_name(table_name)
    return Path(DATA_DIR) / f"{table_name}.json"


def _save_json(filepath, data):
    """Сначала записать временный файл, затем заменить целевой целиком."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=filepath.parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, filepath)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_metadata(filepath):
    """Загрузить метаданные или вернуть пустой словарь для новой базы."""
    try:
        with open(filepath, encoding="utf-8") as file:
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
        with _table_filepath(table_name).open(encoding="utf-8") as file:
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
    _table_filepath(table_name).unlink(missing_ok=True)
