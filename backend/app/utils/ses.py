from __future__ import annotations

import asyncio
import json
import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)

ses_client = boto3.client("ses", region_name=settings.AWS_REGION)
sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)


async def send_email_via_ses(
    to_address: str,
    from_address: str,
    from_name: str,
    reply_to: str | None,
    subject: str,
    html_body: str,
    configuration_set: str,
) -> str:
    source = f"{from_name} <{from_address}>"
    args: dict[str, object] = {
        "Source": source,
        "Destination": {"ToAddresses": [to_address]},
        "Message": {
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
        },
        "ConfigurationSetName": configuration_set,
    }
    if reply_to:
        args["ReplyToAddresses"] = [reply_to]
    response = await asyncio.to_thread(ses_client.send_email, **args)
    return str(response["MessageId"])


async def enqueue_send_job(message_body: dict[str, object]) -> None:
    await asyncio.to_thread(
        sqs_client.send_message,
        QueueUrl=settings.AWS_SQS_SEND_QUEUE_URL,
        MessageBody=json.dumps(message_body),
    )


async def receive_sqs_messages(queue_url: str) -> list[dict[str, object]]:
    response = await asyncio.to_thread(
        sqs_client.receive_message,
        QueueUrl=queue_url,
        MaxNumberOfMessages=settings.SQS_MAX_MESSAGES,
        WaitTimeSeconds=settings.SQS_POLL_WAIT_SECONDS,
    )
    return [
        {"receipt_handle": message["ReceiptHandle"], "body": json.loads(message["Body"])}
        for message in response.get("Messages", [])
    ]


async def delete_sqs_message(queue_url: str, receipt_handle: str) -> None:
    await asyncio.to_thread(
        sqs_client.delete_message,
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle,
    )
