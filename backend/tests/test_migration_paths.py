"""Both developers' previously deployed schema heads must upgrade without data loss."""

import os
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest


@pytest.mark.parametrize("old_head", ["1d34b4f763de", "8a9c2d41f603"])
def test_each_developer_schema_upgrades_to_shared_head_with_existing_products(tmp_path, old_head):
    database = tmp_path / "prior-developer.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + database.as_posix()}

    def alembic(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr

    alembic("upgrade", old_head)
    product_id, seller_id = str(uuid4()), str(uuid4())
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO products (id, seller_id, name, category, description, publish_status, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                product_id,
                seller_id,
                "Preserved developer product",
                "bags",
                "",
                "draft",
                "2026-11-06 00:00:00",
                "2026-11-06 00:00:00",
            ),
        )
    alembic("upgrade", "head")
    alembic("check")
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name, stock FROM products WHERE id = ?", (product_id,)
        ).fetchone() == ("Preserved developer product", 0)
        assert connection.execute("SELECT count(*) FROM review_audits").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM users").fetchone() == (0,)
