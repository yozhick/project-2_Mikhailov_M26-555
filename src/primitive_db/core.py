import json
import os

from decorators import confirm_action, create_cacher, handle_db_errors, log_time
from primitive_db.constants import (
    ID_COLUMN,
    ID_FIELD,
    ID_TYPE,
    PYTHON_TYPES,
    SUPPORTED_TYPES,
)
from primitive_db.utils import load_table_data, validate_table_name

_select_cache = create_cacher()


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Создать таблицу; ошибки обрабатывает декоратор."""
    validate_table_name(table_name)
    if table_name in metadata or (
        os.name == "nt"
        and any(name.casefold() == table_name.casefold() for name in metadata)
    ):
        raise ValueError(f'Таблица "{table_name}" уже существует.')
    if not columns:
        raise ValueError("Не указаны столбцы.")

    validated_columns = [ID_COLUMN]
    column_names = set()
    for column in columns:
        parts = column.split(":")
        if len(parts) != 2:
            raise ValueError(f"Некорректный столбец: {column}.")
        name, data_type = parts
        if (
            not name.strip()
            or data_type not in SUPPORTED_TYPES
            or name in column_names
            or (name == ID_FIELD and data_type != ID_TYPE)
        ):
            raise ValueError(f"Некорректный столбец: {column}.")
        column_names.add(name)
        if name != ID_FIELD:
            validated_columns.append(column)

    metadata[table_name] = {"columns": validated_columns}
    _select_cache.clear()
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удалить таблицу; при ошибке вывести сообщение и вернуть None."""
    if table_name not in metadata:
        raise KeyError(table_name)
    del metadata[table_name]
    _select_cache.clear()
    return metadata


@handle_db_errors
def list_tables(metadata):
    """Вернуть имена таблиц в алфавитном порядке."""
    return sorted(metadata)


def _get_columns(metadata, table_name):
    """Получить схему или передать ошибку внешнему обработчику операции."""
    if table_name not in metadata:
        raise KeyError(table_name)
    return dict(column.split(":") for column in metadata[table_name]["columns"])


@handle_db_errors
def get_columns(metadata, table_name):
    """Вернуть схему таблицы в порядке столбцов."""
    return _get_columns(metadata, table_name)


def _validate_fields(metadata, table_name, fields, *, updating=False):
    """Проверить существование и типы полей до изменения данных."""
    columns = _get_columns(metadata, table_name)
    for name, value in fields.items():
        if name not in columns:
            raise KeyError(name)
        if updating and name == ID_FIELD:
            raise ValueError("ID генерируется автоматически и не изменяется.")
        data_type = columns[name]
        if type(value) is not PYTHON_TYPES[data_type]:
            raise ValueError(f'Столбец "{name}" должен иметь тип {data_type}.')
    return True


@handle_db_errors
def validate_fields(metadata, table_name, fields, *, updating=False):
    """Проверить поля и вернуть True; при ошибке декоратор вернёт None."""
    return _validate_fields(metadata, table_name, fields, updating=updating)


@handle_db_errors
@log_time
def insert(metadata, table_name, values, *, table_data=None):
    """Добавить запись с новым ID; переданный список данных можно загрузить заранее."""
    columns = [name for name in _get_columns(metadata, table_name) if name != ID_FIELD]
    if len(values) != len(columns):
        raise ValueError(
            f"Ожидается значений: {len(columns)} (без ID), получено: {len(values)}."
        )
    record = dict(zip(columns, values, strict=True))
    _validate_fields(metadata, table_name, record)
    if table_data is None:
        table_data = load_table_data(table_name)
    if any(
        type(row.get(ID_FIELD)) is not int or row[ID_FIELD] < 1 for row in table_data
    ):
        raise ValueError(f'Некорректные ID в данных таблицы "{table_name}".')
    identifiers = [row[ID_FIELD] for row in table_data]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f'Повторяющиеся ID в данных таблицы "{table_name}".')
    new_id = max(identifiers, default=0) + 1
    table_data.append({ID_FIELD: new_id, **record})
    _select_cache.clear()
    return table_data


def _matches(record, where_clause):
    """Сравнить поля с условием с учётом точных типов значений."""
    return all(
        name in record and type(record[name]) is type(value) and record[name] == value
        for name, value in where_clause.items()
    )


def _select_rows(table_data, where_clause=None):
    """Отфильтровать строки без кэширования и вывода в консоль."""
    if where_clause is None:
        return list(table_data)
    return [row for row in table_data if _matches(row, where_clause)]


@handle_db_errors
def find_records(table_data, where_clause):
    """Найти строки для изменения без сообщений о времени и кэше выборки."""
    return _select_rows(table_data, where_clause)


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Кэшировать выборку по снимку данных и условия, возвращая независимую копию."""
    key = json.dumps(
        [table_data, where_clause],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    if _select_cache.contains(key):
        print("Результат запроса получен из кэша.")
    result = _select_cache(
        key,
        lambda: json.dumps(_select_rows(table_data, where_clause), ensure_ascii=False),
    )
    return json.loads(result)


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Обновить подходящие записи после проверки всех новых значений."""
    if not where_clause or not set_clause:
        raise ValueError("Для update нужны set и where.")
    if ID_FIELD in set_clause:
        raise ValueError("ID генерируется автоматически и не изменяется.")
    matching = _select_rows(table_data, where_clause)
    for row in matching:
        for name, value in set_clause.items():
            if name not in row or type(value) is not type(row[name]):
                raise ValueError(f'Некорректное значение столбца "{name}".')
    if matching:
        _select_cache.clear()
    for row in matching:
        row.update(set_clause)
    return table_data


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Удалить подходящие записи, сохранив все остальные."""
    if not where_clause:
        raise ValueError("Для delete нужно условие where.")
    remaining = [row for row in table_data if not _matches(row, where_clause)]
    if len(remaining) != len(table_data):
        _select_cache.clear()
    return remaining
