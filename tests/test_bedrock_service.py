import json
import os
import unittest
from unittest.mock import patch

from backend.services.bedrock_service import BedrockService


class TestBedrockService(unittest.TestCase):
    def test_local_mode_uses_mock_response(self):
        with patch.dict(os.environ, {"LOCAL_MODE": "true"}, clear=False):
            service = BedrockService()
            result = json.loads(service.generate("test prompt"))
            self.assertIn("score", result)
            self.assertIn("approved", result)
            self.assertIn("requires_human_review", result)

    def test_aws_mode_uses_bedrock_runtime(self):
        fake_response = {
            "body": type("Body", (), {"read": lambda self: b'{"score": 90, "approved": true, "issues": [], "recommendations": [], "requires_human_review": false, "risk_level": "low", "status": "approved"}'})()
        }

        with patch.dict(
            os.environ,
            {
                "LOCAL_MODE": "false",
                "AWS_REGION": "us-east-1",
                "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
                "AWS_ACCESS_KEY_ID": "test-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret",
            },
            clear=False,
        ):
            with patch("backend.services.bedrock_service.boto3.client") as mock_client:
                mock_client.return_value.invoke_model.return_value = fake_response

                service = BedrockService()
                result = json.loads(service.generate("test prompt"))

                self.assertEqual(result["score"], 90)
                self.assertTrue(result["approved"])
                self.assertFalse(result["requires_human_review"])
                mock_client.assert_called_once()

    def test_risky_decision_requires_human_review(self):
        fake_response = {
            "body": type("Body", (), {"read": lambda self: b'{"score": 15, "approved": true, "issues": ["Low confidence"], "recommendations": ["Manual review required"], "status": "approved"}'})()
        }

        with patch.dict(
            os.environ,
            {
                "LOCAL_MODE": "false",
                "AWS_REGION": "us-east-1",
                "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
                "AWS_ACCESS_KEY_ID": "test-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret",
            },
            clear=False,
        ):
            with patch("backend.services.bedrock_service.boto3.client") as mock_client:
                mock_client.return_value.invoke_model.return_value = fake_response

                result = json.loads(BedrockService().generate("test prompt"))
                self.assertTrue(result["requires_human_review"])
                self.assertEqual(result["risk_level"], "high")

    def test_generate_falls_back_when_model_call_fails(self):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODE": "false",
                "AWS_REGION": "us-east-1",
                "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
                "AWS_ACCESS_KEY_ID": "test-key",
                "AWS_SECRET_ACCESS_KEY": "test-secret",
            },
            clear=False,
        ):
            with patch("backend.services.bedrock_service.boto3.client") as mock_client:
                mock_client.return_value.invoke_model.side_effect = TimeoutError("Bedrock timeout")

                result = json.loads(BedrockService().generate("test prompt"))
                self.assertEqual(result["status"], "fallback")
                self.assertTrue(result["requires_human_review"])


if __name__ == "__main__":
    unittest.main()
