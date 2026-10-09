"""GET /jobs/{id} -> {job_id, status, result (parsed result_json or null), error}."""

import json
import os

import boto3

table = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "ap-south-1")).Table(os.environ["TABLE_NAME"])


def _resp(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def handler(event, context):
    job_id = (event.get("pathParameters") or {}).get("id", "")
    if not job_id:
        return _resp(400, {"error": "missing job id"})
    item = table.get_item(Key={"job_id": job_id}).get("Item")
    if item is None:
        return _resp(404, {"error": "job not found"})
    result = json.loads(item["result_json"]) if item.get("result_json") else None
    return _resp(200, {"job_id": job_id, "status": item["status"], "result": result, "error": item.get("error")})
