import json, uuid, logging
from wind_agg.models import ClaimRequest
from wind_agg.aggregate import process_claim
from pydantic import ValidationError
import logging
logging.basicConfig(level=logging.INFO)

log = logging.getLogger()
log.setLevel(logging.INFO)

def lambda_handler(event, context):
    corr_id = str(uuid.uuid4())
    try:
        body = json.loads(event.get("body") or "{}")
        req  = ClaimRequest.model_validate(body)
        result = process_claim(req, corr_id)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json",
                        "X-Correlation-Id": corr_id},
            "body": result.model_dump_json()
        }
    except (ValidationError, ValueError) as ve:
        log.warning("%s input error: %s", corr_id, ve)
        return {
            "statusCode": 422,
            "body": json.dumps({"detail": str(ve),
                                "correlation_id": corr_id})
        }
    except Exception as ex:
        log.exception("%s unhandled", corr_id)
        return {"statusCode": 500,
                "body": json.dumps({"detail": "internal error",
                                    "correlation_id": corr_id})}