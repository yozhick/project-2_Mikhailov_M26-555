import ast
import re

TOKEN = re.compile(r"\s*(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[(),=]|[^\s(),=\"']+)")
INTEGER = re.compile(r"[+-]?[0-9]+")


class ParseError(ValueError):
    """Некорректный синтаксис пользовательской команды."""


def tokenize(text):
    """Разбить строку, сохраняя кавычки и разделители внутри строковых значений."""
    tokens = []
    position = 0
    while position < len(text):
        if not text[position:].strip():
            break
        match = TOKEN.match(text, position)
        if match is None:
            raise ParseError(f"проверьте кавычки рядом с {text[position:]!r}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens


def parse_value(token):
    """Строки требуют кавычек, числа и true/false преобразуются в Python-типы."""
    if token.startswith(('"', "'")):
        try:
            value = ast.literal_eval(token)
        except (SyntaxError, ValueError):
            raise ParseError(f"некорректная строка {token!r}") from None
        if isinstance(value, str):
            return value
    elif token.lower() in {"true", "false"}:
        return token.lower() == "true"
    elif INTEGER.fullmatch(token):
        return int(token)
    raise ParseError(
        f"значение {token!r}: используйте int, true/false или строку в кавычках"
    )


def _name(token):
    name = parse_value(token) if token.startswith(('"', "'")) else token
    if not isinstance(name, str) or not name.strip() or name in {"(", ")", ",", "="}:
        raise ParseError(f"некорректное имя {token!r}")
    return name


def _assignments(tokens, separator, stop_word=None):
    result = {}
    position = 0
    while position < len(tokens):
        if position + 2 >= len(tokens) or tokens[position + 1] != "=":
            raise ParseError("ожидается <столбец> = <значение>")
        name = _name(tokens[position])
        if name in result:
            raise ParseError(f'столбец "{name}" указан несколько раз')
        result[name] = parse_value(tokens[position + 2])
        position += 3
        if position == len(tokens):
            break
        if stop_word and tokens[position].lower() == stop_word:
            break
        if tokens[position].lower() != separator:
            raise ParseError(f"между условиями ожидается {separator!r}")
        position += 1
        if position == len(tokens):
            raise ParseError("после разделителя ожидается условие")
    if not result:
        raise ParseError("условие не задано")
    return result, position


def parse_where_clause(clause):
    """Преобразовать age = 28 [and ...] в словарь условий."""
    result, _ = _assignments(tokenize(clause), "and")
    return result


def parse_set_clause(clause):
    """Преобразовать age = 29, is_active = false в словарь изменений."""
    result, _ = _assignments(tokenize(clause), ",")
    return result


def _values(tokens):
    if not tokens:
        return []
    values = []
    for position, token in enumerate(tokens):
        if position % 2:
            if token != ",":
                raise ParseError("значения должны разделяться запятыми")
        else:
            values.append(parse_value(token))
    if len(tokens) % 2 == 0:
        raise ParseError("после запятой ожидается значение")
    return values


def parse_command(user_input):
    """Разобрать команду без потери типов и содержимого строк в кавычках."""
    tokens = tokenize(user_input)
    if not tokens:
        return None
    command = tokens[0].lower()
    result = {"command": command}
    if command in {"exit", "help", "list_tables"}:
        if len(tokens) != 1:
            raise ParseError(f"{command} не принимает аргументы")
    elif command in {"drop_table", "info"}:
        if len(tokens) != 2:
            raise ParseError(f"ожидается {command} <имя_таблицы>")
        result["table_name"] = _name(tokens[1])
    elif command == "create_table":
        if len(tokens) < 3:
            raise ParseError("ожидается create_table <имя_таблицы> <столбец:тип> ...")
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
            raise ParseError("ожидается insert into <таблица> values (<значения>)")
        result["table_name"] = _name(tokens[2])
        result["values"] = _values(tokens[5:-1])
    elif command in {"select", "delete"}:
        if len(tokens) < 3 or tokens[1].lower() != "from":
            raise ParseError(f"ожидается {command} from <таблица> [where <условие>]")
        result["table_name"] = _name(tokens[2])
        if len(tokens) == 3 and command == "select":
            result["where_clause"] = None
        else:
            if len(tokens) < 5 or tokens[3].lower() != "where":
                raise ParseError("ожидается where <столбец> = <значение>")
            result["where_clause"], _ = _assignments(tokens[4:], "and")
    elif command == "update":
        if len(tokens) < 4 or tokens[2].lower() != "set":
            raise ParseError(
                "ожидается update <таблица> set <изменения> where <условие>"
            )
        result["table_name"] = _name(tokens[1])
        assignments = tokens[3:]
        result["set_clause"], end = _assignments(assignments, ",", stop_word="where")
        if end == len(assignments):
            raise ParseError("для update обязательно условие where")
        result["where_clause"], _ = _assignments(assignments[end + 1 :], "and")
    return result
