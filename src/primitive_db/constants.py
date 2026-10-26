"""Общие настройки хранения, типов данных и разбора команд."""

METADATA_FILE = "db_meta.json"
DATA_DIR = "data"
TEXT_ENCODING = "utf-8"
JSON_INDENT = 2
TEMP_SUFFIX_BYTES = 8

ID_FIELD = "ID"
ID_TYPE = "int"
ID_COLUMN = f"{ID_FIELD}:{ID_TYPE}"
PYTHON_TYPES = {"int": int, "str": str, "bool": bool}
SUPPORTED_TYPES = frozenset(PYTHON_TYPES)

STRING_QUOTES = "\"'"
TOKEN_SEPARATORS = "(),="
BOOLEAN_VALUES = {"true": True, "false": False}

WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}"
    for prefix in ("COM", "LPT")
    for number in (1, 2, 3, 4, 5, 6, 7, 8, 9)
}
INVALID_FILENAME_CHARACTERS = '<>:"/\\|?*'
CONTROL_CHARACTER_LIMIT = 32

WRAPPER_ATTRIBUTES = ("__name__", "__qualname__", "__doc__", "__module__")
