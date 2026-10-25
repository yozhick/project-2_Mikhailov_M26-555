import shlex

import prompt

from primitive_db.core import create_table, drop_table, list_tables
from primitive_db.utils import load_metadata, save_metadata

METADATA_FILE = "db_meta.json"


def print_help():
    """Prints the help message for the current mode."""
    print("\n***Процесс работы с таблицей***")
    print("Функции:")
    print("<command> create_table <имя_таблицы> <столбец1:тип> .. - создать таблицу")
    print("<command> list_tables - показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")

    print("\nОбщие команды:")
    print("<command> exit - выход из программы")
    print("<command> help - справочная информация\n")


def run():
    """Запустить цикл команд управления таблицами."""
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
            try:
                args = shlex.split(user_input)
            except ValueError:
                raise ValueError(user_input) from None
            if not args:
                continue
            command, *arguments = args

            if command == "exit":
                if arguments:
                    raise ValueError(user_input)
                return
            elif command == "help":
                if arguments:
                    raise ValueError(user_input)
                print_help()
            elif command == "list_tables":
                if arguments:
                    raise ValueError(user_input)
                tables = list_tables(metadata)
                if tables:
                    for table_name in tables:
                        print(f"- {table_name}")
                else:
                    print("Таблиц пока нет.")
            elif command == "create_table":
                if len(arguments) < 2:
                    raise ValueError(user_input)
                table_name, *columns = arguments
                updated_metadata = create_table(metadata, table_name, columns)
                if updated_metadata is not None:
                    save_metadata(METADATA_FILE, updated_metadata)
                    column_list = ", ".join(metadata[table_name]["columns"])
                    print(
                        f'Таблица "{table_name}" успешно создана '
                        f"со столбцами: {column_list}"
                    )
            elif command == "drop_table":
                if len(arguments) != 1:
                    raise ValueError(user_input)
                table_name = arguments[0]
                updated_metadata = drop_table(metadata, table_name)
                if updated_metadata is not None:
                    save_metadata(METADATA_FILE, updated_metadata)
                    print(f'Таблица "{table_name}" успешно удалена.')
            else:
                print(f"Функции {command} нет. Попробуйте снова.")
        except ValueError as error:
            print(f"Некорректное значение: {error}. Попробуйте снова.")
        except OSError as error:
            print(f"Ошибка: не удалось сохранить метаданные: {error}")
