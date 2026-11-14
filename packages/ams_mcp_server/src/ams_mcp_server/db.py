import json
import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


@contextmanager
def conn():
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as c:
        yield c


def audit(tool: str, caller: str, args: dict, approval: str | None = None) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO audit_log (tool, caller, args, approval) VALUES (%s, %s, %s, %s)",
            (tool, caller, json.dumps(args, default=str), approval),
        )