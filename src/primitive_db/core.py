import os

from primitive_db.utils import load_table_data, validate_table_name

SUPPORTED_TYPES = {"int", "str", "bool"}
PYTHON_TYPES = {"int": int, "str": str, "bool": bool}


def create_table(metadata, table_name, columns):
    """Создать таблицу; при ошибке вывести сообщение и вернуть None."""
    try:
        validate_table_name(table_name)
    except ValueError as error:
        print(f"Некорректное значение: {error} Попробуйте снова.")
        return None
    if table_name in metadata or (
        os.name == "nt"
        and any(name.casefold() == table_name.casefold() for name in metadata)
    ):
        print(f'Ошибка: Таблица "{table_name}" уже существует.')
        return None
    if not columns:
        print("Некорректное значение: не указаны столбцы. Попробуйте снова.")
        return None

    validated_columns = ["ID:int"]
    column_names = set()
    for column in columns:
        parts = column.split(":")
        if len(parts) != 2:
            print(f"Некорректное значение: {column}. Попробуйте снова.")
            return None
        name, data_type = parts
        if (
            not name.strip()
            or data_type not in SUPPORTED_TYPES
            or name in column_names
            or (name == "ID" and data_type != "int")
        ):
            print(f"Некорректное значение: {column}. Попробуйте снова.")
            return None
        column_names.add(name)
        if name != "ID":
            validated_columns.append(column)

    metadata[table_name] = {"columns": validated_columns}
    return metadata


def drop_table(metadata, table_name):
    """Удалить таблицу; при ошибке вывести сообщение и вернуть None."""
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return None
    del metadata[table_name]
    return metadata


def list_tables(metadata):
    """Вернуть имена таблиц в алфавитном порядке."""
    return sorted(metadata)


def get_columns(metadata, table_name):
    """Вернуть схему таблицы в порядке столбцов."""
    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')
    return dict(column.split(":") for column in metadata[table_name]["columns"])


def validate_fields(metadata, table_name, fields, *, updating=False):
    """Проверить имена столбцов и точные типы значений, включая условия where."""
    columns = get_columns(metadata, table_name)
    for name, value in fields.items():
        if name not in columns:
            raise ValueError(
                f'Столбец "{name}" не существует в таблице "{table_name}".'
            )
        if updating and name == "ID":
            raise ValueError("ID генерируется автоматически и не изменяется.")
        data_type = columns[name]
        if type(value) is not PYTHON_TYPES[data_type]:
            raise ValueError(f'Столбец "{name}" должен иметь тип {data_type}.')


def insert(metadata, table_name, values, *, table_data=None):
    """Добавить запись с новым ID; переданный список данных можно загрузить заранее."""
    columns = [name for name in get_columns(metadata, table_name) if name != "ID"]
    if len(values) != len(columns):
        raise ValueError(
            f"Ожидается значений: {len(columns)} (без ID), получено: {len(values)}."
        )
    record = dict(zip(columns, values, strict=True))
    validate_fields(metadata, table_name, record)
    if table_data is None:
        table_data = load_table_data(table_name)
    if any(type(row.get("ID")) is not int or row["ID"] < 1 for row in table_data):
        raise ValueError(f'Некорректные ID в данных таблицы "{table_name}".')
    identifiers = [row["ID"] for row in table_data]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f'Повторяющиеся ID в данных таблицы "{table_name}".')
    new_id = max(identifiers, default=0) + 1
    table_data.append({"ID": new_id, **record})
    return table_data


def _matches(record, where_clause):
    return all(
        name in record and type(record[name]) is type(value) and record[name] == value
        for name, value in where_clause.items()
    )


def select(table_data, where_clause=None):
    """Выбрать все записи или записи, удовлетворяющие всем условиям."""
    if where_clause is None:
        return list(table_data)
    return [row for row in table_data if _matches(row, where_clause)]


def update(table_data, set_clause, where_clause):
    """Обновить подходящие записи после проверки всех новых значений."""
    if not where_clause or not set_clause:
        raise ValueError("Для update нужны set и where.")
    if "ID" in set_clause:
        raise ValueError("ID генерируется автоматически и не изменяется.")
    matching = select(table_data, where_clause)
    for row in matching:
        for name, value in set_clause.items():
            if name not in row or type(value) is not type(row[name]):
                raise ValueError(f'Некорректное значение столбца "{name}".')
    for row in matching:
        row.update(set_clause)
    return table_data


def delete(table_data, where_clause):
    """Удалить подходящие записи, сохранив все остальные."""
    if not where_clause:
        raise ValueError("Для delete нужно условие where.")
    return [row for row in table_data if not _matches(row, where_clause)]
