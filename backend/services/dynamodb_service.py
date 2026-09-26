from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config
from botocore.exceptions import ClientError

from backend.config import settings


def _get_resource():
    config = Config(retries={"max_attempts": 3, "mode": "adaptive"})
    return boto3.resource(
        "dynamodb",
        region_name=settings.dynamodb_region,
        config=config,
    )


def _table(table_name: str | None = None):
    name = table_name or settings.dynamodb_table_name
    if not name:
        raise ValueError("DYNAMODB_TABLE_NAME is not configured.")
    return _get_resource().Table(name)


def put_item(item: dict, table_name: str | None = None) -> None:
    """Write an item. Item must contain the table's partition key."""
    _table(table_name).put_item(Item=item)


def get_item(key: dict, table_name: str | None = None) -> dict | None:
    """Fetch a single item by key. Returns None if not found."""
    try:
        response = _table(table_name).get_item(Key=key)
        return response.get("Item")
    except ClientError:
        return None


def delete_item(key: dict, table_name: str | None = None) -> None:
    _table(table_name).delete_item(Key=key)


def query_items(
    partition_key_name: str,
    partition_key_value: str,
    index_name: str | None = None,
    table_name: str | None = None,
) -> list[dict]:
    """Safe parameterized query using boto3 Key condition expression."""
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key(partition_key_name).eq(partition_key_value),
    }
    if index_name:
        kwargs["IndexName"] = index_name
    response = _table(table_name).query(**kwargs)
    return response.get("Items", [])


def filter_items(
    attr_name: str,
    attr_value: str,
    table_name: str | None = None,
) -> list[dict]:
    """Safe scan with Attr filter expression — use sparingly in production."""
    response = _table(table_name).scan(
        FilterExpression=Attr(attr_name).eq(attr_value),
    )
    return response.get("Items", [])


def scan_items(table_name: str | None = None) -> list[dict]:
    """Full table scan — use sparingly, prefer query_items in production."""
    response = _table(table_name).scan()
    return response.get("Items", [])
