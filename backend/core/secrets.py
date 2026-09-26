import json
import logging
import os

logger = logging.getLogger(__name__)

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


def get_secret(secret_name: str, fallback_env_name: str | None = None, default: str | None = None) -> str | None:
    env_value = fallback_env_name and os.getenv(fallback_env_name)
    if env_value:
        return env_value

    if os.getenv("USE_AWS_SECRETS_MANAGER", "false").lower() == "true" and boto3 is not None:
        try:
            client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = client.get_secret_value(SecretId=secret_name)
            if "SecretString" in response:
                secret_value = response["SecretString"]
                try:
                    parsed = json.loads(secret_value)
                    if isinstance(parsed, dict):
                        if fallback_env_name and fallback_env_name.lower() in {key.lower(): key for key in parsed}:
                            key = next(k for k in parsed if k.lower() == fallback_env_name.lower())
                            return str(parsed[key])
                        for value in parsed.values():
                            return str(value)
                    return str(parsed)
                except json.JSONDecodeError:
                    return str(secret_value)
        except Exception as exc:
            logger.warning("Secrets Manager lookup failed for '%s': %s", secret_name, exc)

    return default
