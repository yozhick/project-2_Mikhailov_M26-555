import prompt
from prettytable import PrettyTable

from primitive_db.core import (
    create_table,
    delete,
    drop_table,
    get_columns,
    insert,
    list_tables,
    select,
    update,
    validate_fields,
)
from primitive_db.parser import ParseError, parse_command
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    remove_table_data,
    save_metadata,
    save_table_data,
)

METADATA_FILE = "db_meta.json"


def print_help():
    """Показать команды работы со строками и управления таблицами."""
    print("\n***Операции с данными***")
    print("\nФункции:")
    print(
        "<command> insert into <имя_таблицы> values "
        "(<значение1>, <значение2>, ...) - создать запись."
    )
    print(
        "<command> select from <имя_таблицы> where "
        "<столбец> = <значение> - прочитать записи по условию."
    )
    print("<command> select from <имя_таблицы> - прочитать все записи.")
    print(
        "<command> update <имя_таблицы> set <столбец1> = <новое_значение1> "
        "where <столбец_условия> = <значение_условия> - обновить запись."
    )
    print(
        "<command> delete from <имя_таблицы> where "
        "<столбец> = <значение> - удалить запись."
    )
    print("<command> info <имя_таблицы> - вывести информацию о таблице.")
    print("\nУправление таблицами:")
    print("<command> create_table <имя_таблицы> <столбец1:тип> .. - создать таблицу")
    print("<command> list_tables - показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")
    print("\nОбщие команды:")
    print("<command> exit - выход из программы")
    print("<command> help - справочная информация\n")


def _execute_table_command(command, metadata):
    action = command["command"]
    if action == "list_tables":
        tables = list_tables(metadata)
        if tables:
            for table_name in tables:
                print(f"- {table_name}")
        else:
            print("Таблиц пока нет.")
        return

    table_name = command["table_name"]
    if action == "create_table":
        updated = create_table(metadata, table_name, command["columns"])
        if updated is not None:
            save_table_data(table_name, [])
            save_metadata(METADATA_FILE, updated)
            column_list = ", ".join(metadata[table_name]["columns"])
            print(f'Таблица "{table_name}" успешно создана со столбцами: {column_list}')
    elif action == "drop_table":
        updated = drop_table(metadata, table_name)
        if updated is not None:
            save_metadata(METADATA_FILE, updated)
            remove_table_data(table_name)
            print(f'Таблица "{table_name}" успешно удалена.')


def _print_records(columns, records):
    table = PrettyTable()
    table.field_names = list(columns)
    table.add_rows([[row[name] for name in columns] for row in records])
    print(table)


def _execute_data_command(command, metadata):
    action = command["command"]
    table_name = command["table_name"]
    columns = get_columns(metadata, table_name)
    table_data = load_table_data(table_name)
    for row in table_data:
        if set(row) != set(columns):
            raise ValueError(f'Данные таблицы "{table_name}" не соответствуют схеме.')
        validate_fields(metadata, table_name, row)

    where_clause = command.get("where_clause")
    validate_fields(metadata, table_name, where_clause or {})
    if action == "insert":
        updated = insert(metadata, table_name, command["values"], table_data=table_data)
        save_table_data(table_name, updated)
        print(
            f"Запись с ID={updated[-1]['ID']} успешно добавлена "
            f'в таблицу "{table_name}".'
        )
    elif action == "select":
        _print_records(columns, select(table_data, where_clause))
    elif action == "info":
        print(f"Таблица: {table_name}")
        print("Столбцы: " + ", ".join(metadata[table_name]["columns"]))
        print(f"Количество записей: {len(table_data)}")
    elif action == "update":
        set_clause = command["set_clause"]
        validate_fields(metadata, table_name, set_clause, updating=True)
        matching = select(table_data, where_clause)
        updated = update(table_data, set_clause, where_clause)
        if matching:
            save_table_data(table_name, updated)
            for row in matching:
                print(
                    f'Запись с ID={row["ID"]} в таблице "{table_name}" '
                    "успешно обновлена."
                )
        else:
            print("Подходящие записи не найдены.")
    elif action == "delete":
        matching = select(table_data, where_clause)
        updated = delete(table_data, where_clause)
        if matching:
            save_table_data(table_name, updated)
            for row in matching:
                print(
                    f"Запись с ID={row['ID']} успешно удалена "
                    f'из таблицы "{table_name}".'
                )
        else:
            print("Подходящие записи не найдены.")


def run():
    """Запустить цикл управления таблицами и данными."""
    print("***База данных***")
    print_help()
    while True:
        try:
            metadata = load_metadata(METADATA_FILE)
        except (OSError, ValueError) as error:
            print(f"Ошибка: не удалось загрузить метаданные: {error}")
            return
        try:
            user_input = prompt.string(">>>Введите команду: ", empty=True)
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not user_input:
            continue
        try:
            command = parse_command(user_input)
            if command is None:
                continue
            action = command["command"]
            if action == "exit":
                return
            elif action == "help":
                print_help()
            elif action in {"create_table", "drop_table", "list_tables"}:
                _execute_table_command(command, metadata)
            elif action in {"insert", "select", "update", "delete", "info"}:
                _execute_data_command(command, metadata)
            else:
                print(f"Функции {action} нет. Попробуйте снова.")
        except ParseError as error:
            print(f"Некорректное значение: {error}. Попробуйте снова.")
        except ValueError as error:
            print(f"Ошибка: {error}")
        except OSError as error:
            print(f"Ошибка работы с файлами: {error}")
