"""A small deterministic transformation DSL for migration mappings.

Expressions are parsed into a constrained AST rather than executed as arbitrary
Python.  Each operation returns a value plus lineage so a transformed field can
be explained after the migration.
"""
from __future__ import annotations

import datetime as dt
import decimal
import re
from dataclasses import dataclass
from typing import Any, Mapping


class TransformError(ValueError):
    pass


@dataclass(frozen=True)
class TransformResult:
    value: Any
    operation: str
    inputs: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple[Any, ...]
    kwargs: tuple[tuple[str, Any], ...] = ()

    def keyword_args(self) -> dict[str, Any]:
        return dict(self.kwargs)


_ALLOWED = {
    "TRIM",
    "UPPER",
    "LOWER",
    "PARSE_DATE",
    "DECIMAL",
    "MAP_ENUM",
    "SPLIT_NAME",
    "NORMALIZE_CURRENCY",
    "COALESCE",
    "IDENTITY",
}


_TOKEN = re.compile(r"\s*(?:(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)|(?P<string>\"(?:[^\"\\\\]|\\\\.)*\")|(?P<number>-?\d+(?:\.\d+)?)|(?P<punct>[(),=]))")


def parse(expression: str) -> Expr:
    """Parse a simple function-call expression such as DECIMAL(source.balance, scale=4)."""
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(expression):
        match = _TOKEN.match(expression, position)
        if not match:
            raise TransformError(f"invalid expression near: {expression[position:]}" )
        kind = next(key for key, value in match.groupdict().items() if value is not None)
        tokens.append((kind, match.group(kind)))
        position = match.end()
    index = 0

    def take(kind: str) -> str:
        nonlocal index
        if index >= len(tokens) or tokens[index][0] != kind:
            actual = tokens[index] if index < len(tokens) else "<eof>"
            raise TransformError(f"expected {kind}, got {actual}")
        value = tokens[index][1]
        index += 1
        return value

    op = take("name")
    if op not in _ALLOWED:
        raise TransformError(f"unsupported transformation: {op}")
    take("punct")
    args: list[Any] = []
    kwargs: list[tuple[str, Any]] = []
    while index < len(tokens) and tokens[index] != ("punct", ")"):
        if tokens[index][0] == "name" and index + 1 < len(tokens) and tokens[index + 1] == ("punct", "="):
            key = take("name")
            take("punct")
            kwargs.append((key, _literal(take(tokens[index][0]))))
        else:
            token_kind = tokens[index][0]
            args.append(_literal(take(token_kind)))
        if index < len(tokens) and tokens[index] == ("punct", ","):
            take("punct")
    take("punct")
    if index != len(tokens):
        raise TransformError("trailing tokens in transformation")
    return Expr(op, tuple(args), tuple(kwargs))


def _literal(token: str) -> Any:
    if token.startswith('"'):
        return bytes(token[1:-1], "utf-8").decode("unicode_escape")
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)
    return token


def _source_value(reference: Any, row: Mapping[str, Any]) -> tuple[Any, str]:
    if not isinstance(reference, str) or not reference.startswith("source."):
        return reference, "literal"
    field = reference.split(".", 1)[1]
    return row.get(field), field


def evaluate(expr: Expr | str, row: Mapping[str, Any]) -> TransformResult:
    parsed = parse(expr) if isinstance(expr, str) else expr
    if parsed.op == "IDENTITY":
        value, source = _source_value(parsed.args[0], row)
        return TransformResult(value, parsed.op, (source,))
    if parsed.op in {"TRIM", "UPPER", "LOWER"}:
        value, source = _source_value(parsed.args[0], row)
        if value is None:
            return TransformResult(None, parsed.op, (source,), ("NULL_INPUT",))
        text = str(value).strip()
        if parsed.op == "UPPER":
            text = text.upper()
        elif parsed.op == "LOWER":
            text = text.lower()
        return TransformResult(text, parsed.op, (source,))
    if parsed.op == "PARSE_DATE":
        value, source = _source_value(parsed.args[0], row)
        fmt = str(parsed.args[1]) if len(parsed.args) > 1 else "%Y-%m-%d"
        fmt = {"DD/MM/YYYY": "%d/%m/%Y", "YYYY-MM-DD": "%Y-%m-%d"}.get(fmt, fmt)
        if value in (None, ""):
            return TransformResult(None, parsed.op, (source,), ("NULL_INPUT",))
        try:
            return TransformResult(dt.datetime.strptime(str(value).strip(), fmt).date().isoformat(), parsed.op, (source,))
        except ValueError as exc:
            raise TransformError(f"invalid date {value!r}: {exc}") from exc
    if parsed.op == "DECIMAL":
        value, source = _source_value(parsed.args[0], row)
        if value in (None, ""):
            return TransformResult(None, parsed.op, (source,), ("NULL_INPUT",))
        scale = int(parsed.keyword_args().get("scale", 4))
        try:
            quant = decimal.Decimal("1").scaleb(-scale)
            return TransformResult(str(decimal.Decimal(str(value)).quantize(quant)), parsed.op, (source,))
        except decimal.InvalidOperation as exc:
            raise TransformError(f"invalid decimal {value!r}") from exc
    if parsed.op == "MAP_ENUM":
        value, source = _source_value(parsed.args[0], row)
        mapping = parsed.args[1] if len(parsed.args) > 1 and isinstance(parsed.args[1], Mapping) else parsed.keyword_args().get("mapping", {})
        return TransformResult(mapping.get(str(value), mapping.get(value)), parsed.op, (source,))
    if parsed.op == "SPLIT_NAME":
        value, source = _source_value(parsed.args[0], row)
        if not value:
            return TransformResult({"first_name": "", "last_name": ""}, parsed.op, (source,), ("NULL_INPUT",))
        parts = str(value).strip().split(None, 1)
        return TransformResult({"first_name": parts[0], "last_name": parts[1] if len(parts) > 1 else ""}, parsed.op, (source,))
    if parsed.op == "NORMALIZE_CURRENCY":
        amount, amount_source = _source_value(parsed.args[0], row)
        currency, currency_source = _source_value(parsed.args[1], row)
        rates = parsed.keyword_args().get("rates", {})
        if amount in (None, "") or currency in (None, ""):
            return TransformResult(None, parsed.op, (amount_source, currency_source), ("NULL_INPUT",))
        rate = decimal.Decimal(str(rates.get(str(currency).upper(), 1)))
        value = (decimal.Decimal(str(amount)) * rate).quantize(decimal.Decimal("0.0001"))
        return TransformResult(str(value), parsed.op, (amount_source, currency_source))
    if parsed.op == "COALESCE":
        for argument in parsed.args:
            value, source = _source_value(argument, row)
            if value not in (None, ""):
                return TransformResult(value, parsed.op, (source,))
        return TransformResult(None, parsed.op, tuple(str(arg) for arg in parsed.args), ("ALL_NULL",))
    raise TransformError(f"unhandled operation: {parsed.op}")
