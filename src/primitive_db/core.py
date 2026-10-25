SUPPORTED_TYPES = {"int", "str", "bool"}


def create_table(metadata, table_name, columns):
    """Создать таблицу; при ошибке вывести сообщение и вернуть None."""
    if not table_name.strip():
        print(f"Некорректное значение: {table_name}. Попробуйте снова.")
        return None
    if table_name in metadata:
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
