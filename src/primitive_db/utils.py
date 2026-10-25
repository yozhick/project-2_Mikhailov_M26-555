import json


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
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
