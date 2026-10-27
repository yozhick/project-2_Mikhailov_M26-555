import shlex

from primitive_db.constants import BOOLEAN_VALUES, STRING_QUOTES, TOKEN_SEPARATORS


def tokenize(text):
    """Разбиение строки команды на токены с сохранением строковых значений."""
    tokens = []
    position = 0
    while position < len(text):
        character = text[position]
        if character.isspace():
            position += 1
            continue
        if character in TOKEN_SEPARATORS:
            tokens.append(character)
            position += 1
            continue
        start = position
        if character in STRING_QUOTES:
            quote = character
            position += 1
            while position < len(text):
                if text[position] == "\\" and quote == '"':
                    position += 2
                elif text[position] == quote:
                    position += 1
                    break
                else:
                    position += 1
            else:
                raise ValueError(f"проверьте кавычки рядом с {text[start:]!r}")
        else:
            while (
                position < len(text)
                and not text[position].isspace()
                and text[position] not in TOKEN_SEPARATORS + STRING_QUOTES
            ):
                position += 1
        tokens.append(text[start:position])
    return tokens


def parse_value(token):
    """Преобразование значения команды в соответствующий тип данных."""
    if token.startswith(tuple(STRING_QUOTES)):
        try:
            return shlex.split(token, comments=False, posix=True)[0]
        except (ValueError, IndexError):
            raise ValueError(f"некорректная строка {token!r}") from None
    if token.lower() in BOOLEAN_VALUES:
        return BOOLEAN_VALUES[token.lower()]
    digits = token[1:] if token.startswith(("+", "-")) else token
    if digits and all("0" <= character <= "9" for character in digits):
        return int(token)
    raise ValueError(
        f"значение {token!r}: используйте int, true/false или строку в кавычках"
    )


def _name(token):
    """Разбор и проверка идентификатора таблицы или столбца."""
    name = parse_value(token) if token.startswith(('"', "'")) else token
    if not isinstance(name, str) or not name.strip() or name in {"(", ")", ",", "="}:
        raise ValueError(f"некорректное имя {token!r}")
    return name


def _assignments(tokens, separator, stop_word=None):
    """Разбор выражений в блоках where и set."""
    result = {}
    position = 0
    while position < len(tokens):
        if position + 2 >= len(tokens) or tokens[position + 1] != "=":
            raise ValueError("ожидается <столбец> = <значение>")
        name = _name(tokens[position])
        if name in result:
            raise ValueError(f'столбец "{name}" указан несколько раз')
        result[name] = parse_value(tokens[position + 2])
        position += 3
        if position == len(tokens):
            break
        if stop_word and tokens[position].lower() == stop_word:
            break
        if tokens[position].lower() != separator:
            raise ValueError(f"между условиями ожидается {separator!r}")
        position += 1
        if position == len(tokens):
            raise ValueError("после разделителя ожидается условие")
    if not result:
        raise ValueError("условие не задано")
    return result, position


def parse_where_clause(clause):
    """Преобразование блока where в словарь условий."""
    result, _ = _assignments(tokenize(clause), "and")
    return result


def parse_set_clause(clause):
    """Преобразование блока set в словарь изменений."""
    result, _ = _assignments(tokenize(clause), ",")
    return result


def _values(tokens):
    """Разбор списка значений команды insert."""
    if not tokens:
        return []
    values = []
    for position, token in enumerate(tokens):
        if position % 2:
            if token != ",":
                raise ValueError("значения должны разделяться запятыми")
        else:
            values.append(parse_value(token))
    if len(tokens) % 2 == 0:
        raise ValueError("после запятой ожидается значение")
    return values


def parse_command(user_input):
    """
    Разбор команды пользователя с преобразованием аргументов
    в соответствующие типы данных.
    """
    tokens = tokenize(user_input)
    if not tokens:
        return None
    command = tokens[0].lower()
    result = {"command": command}
    if command in {"exit", "help", "list_tables"}:
        if len(tokens) != 1:
            raise ValueError(f"{command} не принимает аргументы")
    elif command in {"drop_table", "info"}:
        if len(tokens) != 2:
            raise ValueError(f"ожидается {command} <имя_таблицы>")
        result["table_name"] = _name(tokens[1])
    elif command == "create_table":
        if len(tokens) < 3:
            raise ValueError("ожидается create_table <имя_таблицы> <столбец:тип> ...")
        result["table_name"] = _name(tokens[1])
        result["columns"] = [_name(token) for token in tokens[2:]]
    elif command == "insert":
        if (
            len(tokens) < 6
            or tokens[1].lower() != "into"
            or tokens[3].lower() != "values"
            or tokens[4] != "("
            or tokens[-1] != ")"
        ):
            raise ValueError("ожидается insert into <таблица> values (<значения>)")
        result["table_name"] = _name(tokens[2])
        result["values"] = _values(tokens[5:-1])
    elif command in {"select", "delete"}:
        if len(tokens) < 3 or tokens[1].lower() != "from":
            raise ValueError(f"ожидается {command} from <таблица> [where <условие>]")
        result["table_name"] = _name(tokens[2])
        if len(tokens) == 3 and command == "select":
            result["where_clause"] = None
        else:
            if len(tokens) < 5 or tokens[3].lower() != "where":
                raise ValueError("ожидается where <столбец> = <значение>")
            result["where_clause"], _ = _assignments(tokens[4:], "and")
    elif command == "update":
        if len(tokens) < 4 or tokens[2].lower() != "set":
            raise ValueError(
                "ожидается update <таблица> set <изменения> where <условие>"
            )
        result["table_name"] = _name(tokens[1])
        assignments = tokens[3:]
        result["set_clause"], end = _assignments(assignments, ",", stop_word="where")
        if end == len(assignments):
            raise ValueError("для update обязательно условие where")
        result["where_clause"], _ = _assignments(assignments[end + 1 :], "and")
    return result
