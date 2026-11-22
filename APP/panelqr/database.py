from __future__ import annotations

from typing import Any

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def init_app(app) -> None:
    app.teardown_appcontext(close_db)


def get_db() -> psycopg.Connection:
    if "db" not in g:
        g.db = psycopg.connect(
            current_app.config["DATABASE_URL"],
            row_factory=dict_row,
            connect_timeout=5,
        )
    return g.db


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict | None:
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict]:
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def execute(query: str, params: tuple[Any, ...] = ()) -> dict | None:
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone() if cursor.description else None


def close_db(error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is None:
        return
    try:
        if error is None:
            connection.commit()
        else:
            connection.rollback()
    finally:
        connection.close()
