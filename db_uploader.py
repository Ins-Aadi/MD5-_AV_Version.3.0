"""
db_uploader.py
Small CLI helper for adding/listing signatures in the database.
Uses parameterized queries only - never build SQL by string-concatenating
user input, which was the SQL-injection bug in the original script.
"""

import argparse
import logging
from db_connect import _get_pool
import mysql.connector

logger = logging.getLogger("NeuralDefender.Uploader")


def add_signature(sign_type: str, sign_value: str):
    if sign_type not in ("hash", "string"):
        raise ValueError("sign_type must be 'hash' or 'string'")

    connection = _get_pool().get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO signatures (type, signature) VALUES (%s, %s)",
            (sign_type, sign_value),
        )
        connection.commit()
        cursor.close()
        print(f"Added signature: type={sign_type} value={sign_value}")
    except mysql.connector.Error as err:
        logger.error("DB error: %s", err)
        print(f"Failed to add signature: {err}")
    finally:
        connection.close()


def list_signatures():
    connection = _get_pool().get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, type, signature FROM signatures")
        for row in cursor.fetchall():
            print(row)
        cursor.close()
    except mysql.connector.Error as err:
        logger.error("DB error: %s", err)
        print(f"Failed to list signatures: {err}")
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neural Defender signature uploader")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a new signature")
    add_p.add_argument("type", choices=["hash", "string"])
    add_p.add_argument("value")

    sub.add_parser("list", help="List all signatures")

    args = parser.parse_args()

    if args.command == "add":
        add_signature(args.type, args.value)
    elif args.command == "list":
        list_signatures()
