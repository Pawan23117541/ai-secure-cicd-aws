"""Phase 2 check: can this computer talk to Amazon Bedrock?

Run:  python scripts/test_bedrock.py
"""

import os

import boto3

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.anthropic.claude-haiku-4-5-20251001-v1:0")
REGION = os.environ.get("AWS_REGION", "eu-north-1")

client = boto3.client("bedrock-runtime", region_name=REGION)
question = "In one sentence, what is a CI/CD pipeline?"
response = client.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": question}]}],
    inferenceConfig={"maxTokens": 200, "temperature": 0.2},
)
print("Model:", MODEL_ID)
print("Answer:", response["output"]["message"]["content"][0]["text"])
print("Tokens used:", response["usage"])
