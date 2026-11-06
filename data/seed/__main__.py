"""uv run python -m data.seed [--small]

Creates the schema and a few known rows the eval cases rely on (client C-1042, etc.).
Needs DATABASE_URL, e.g. postgresql://postgres:postgres@localhost:5433/postgres
"""

from __future__ import annotations

import argparse
import os

import psycopg

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS clients (
    client_id text PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('personal', 'commercial'))
);
CREATE TABLE IF NOT EXISTS policies (
    policy_id text PRIMARY KEY,
    client_id text NOT NULL REFERENCES clients,
    line text NOT NULL CHECK (line IN ('personal', 'commercial')),
    product text NOT NULL,
    premium numeric(12, 2) NOT NULL,
    effective_date date NOT NULL,
    renewal_date date NOT NULL,
    status text NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS policy_chunks (
    id bigserial PRIMARY KEY,
    policy_id text NOT NULL REFERENCES policies,
    source_doc text NOT NULL,
    content text NOT NULL,
    embedding vector(1024)
);
"""

CLIENTS = [
    ("C-1042", "Dana Whitfield", "personal"),
    ("C-2001", "Marcus Lee", "personal"),
    ("C-3001", "Rise & Shine Bakery LLC", "commercial"),
    ("C-3002", "Northside Plumbing Inc", "commercial"),
]
POLICIES = [
    ("POL-1042", "C-1042", "personal", "HO-3", 1840.00, "2026-03-01", "2027-03-01"),
    ("POL-1043", "C-1042", "personal", "Auto", 1210.00, "2026-06-15", "2026-12-15"),
    ("POL-2001", "C-2001", "personal", "HO-3", 2105.00, "2026-01-10", "2027-01-10"),
    ("POL-3001", "C-3001", "commercial", "BOP", 6400.00, "2026-01-01", "2026-12-01"),
    ("POL-3002", "C-3002", "commercial", "GL", 9150.00, "2025-11-20", "2026-11-20"),
    ("POL-3003", "C-3002", "commercial", "Auto", 4300.00, "2026-02-01", "2027-02-01"),
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--small", action="store_true", help="only the rows eval cases rely on")
    p.parse_args()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(SCHEMA)
        conn.cursor().executemany(
            "INSERT INTO clients VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", CLIENTS
        )
        conn.cursor().executemany(
            "INSERT INTO policies (policy_id, client_id, line, product, premium, effective_date,"
            " renewal_date) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            POLICIES,
        )
    print(f"seeded {len(CLIENTS)} clients and {len(POLICIES)} policies")


if __name__ == "__main__":
    main()
