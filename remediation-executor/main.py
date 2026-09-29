import asyncio
import json
import os

from confluent_kafka import Consumer, Producer
from mcp import Client


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

APPROVED_TOPIC = "remediation.approved"
EXECUTED_TOPIC = "remediation.executed"

MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://localhost:8001/mcp"
)

# The Kafka event can tell me which remediation to execute, but I'll only execute actions that this executor explicitly allows.
ALLOWED_ACTIONS = {
    "restart_service"
}


consumer = Consumer({
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
    "group.id": "remediation-executor",
    "auto.offset.reset": "latest"
})

producer = Producer({
    "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS
})


async def execute_remediation(decision: dict) -> dict:

    action = decision["action"]
    service = decision["service"]

    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported remediation action: {action}")

    async with Client(MCP_SERVER_URL) as client:

        # we made action dynamic as it allows the executor to eventually support multiple remediation actions
        result = await client.call_tool(
            action,
            {"service": service}
        )

        if result.is_error:
            raise RuntimeError(result.content)

        return json.loads(result.content[0].text)


def publish_execution_result(decision: dict, result: dict):

    event = {
        "incidentId": decision["incidentId"],
        "action": decision["action"],
        "service": decision["service"],
        "status": "EXECUTED",
        "result": result
    }

    producer.produce(
        EXECUTED_TOPIC,
        key=decision["incidentId"],
        value=json.dumps(event)
    )

    producer.flush()


def main():

    consumer.subscribe([APPROVED_TOPIC])

    print("Remediation executor started.")

    try:

        while True:

            message = consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                print(f"Kafka error: {message.error()}")
                continue

            decision = json.loads(message.value().decode("utf-8"))

            print("\nReceived approved remediation:")
            print(json.dumps(decision, indent=2))

            try:

                result = asyncio.run(
                    execute_remediation(decision)
                )

                print("\nRemediation result:")
                print(json.dumps(result, indent=2))

                publish_execution_result(
                    decision,
                    result
                )

                print("\nPublished remediation.executed")

            except Exception as error:

                print(
                    f"\nRemediation execution failed: {error}"
                )

    finally:

        consumer.close()


if __name__ == "__main__":
    main()


# Kafka
#   │
#   │ {"action": "restart_service",
#   │  "service": "payment-service"}
#   ▼
# main.py
#   │
#   │ action = "restart_service"
#   ▼
# execute_remediation()
#   │
#   │ client.call_tool(
#   │     "restart_service",
#   │     {"service": "payment-service"}
#   │ )
#   ▼
# MCP Server :8001
#   │
#   ▼
# restart_service("payment-service")
#   │
#   ▼
# {
#   "status": "simulated",
#   ...
# }