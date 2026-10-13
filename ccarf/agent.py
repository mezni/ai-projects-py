import json
import os
from anthropic import Anthropic, transform_schema
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from a .env file
load_dotenv()

# Initialize the Anthropic client
client = Anthropic()

# Set model
model = "claude-haiku-4-5-20251001"


# 1. Define structured output model
class TicketClassification(BaseModel):
    category: str = Field(
        description="The primary category: Shipping, Billing, or Technical"
    )
    urgency: str = Field(description="Estimated urgency level: Low, Medium, or High")


# 2. Define evaluation dataset (Test Cases)
EVAL_DATASET = [
    {
        "id": "test_1",
        "question": "My order #4821 has not arrived yet.",
        "expected_category": "Shipping",
        "expected_urgency": "Medium",
    },
    {
        "id": "test_2",
        "question": "I was double charged on my invoice for this month.",
        "expected_category": "Billing",
        "expected_urgency": "High",
    },
    {
        "id": "test_3",
        "question": "The login button gives a 500 server error on web.",
        "expected_category": "Technical",
        "expected_urgency": "High",
    },
    {
        "id": "test_4",
        "question": "Where can I find tracking for my parcel?",
        "expected_category": "Shipping",
        "expected_urgency": "Low",
    },
]


def add_user_message(messages, text):
    messages.append({"role": "user", "content": text})


def add_assistant_message(messages, text):
    messages.append({"role": "assistant", "content": text})


def chat_structured(messages, system_prompt, response_model):
    """Executes chat request with structured output JSON constraint."""
    json_schema = transform_schema(response_model)

    params = {
        "model": model,
        "max_tokens": 1000,
        "messages": messages,
        "system": system_prompt,
        "output_config": {"format": {"type": "json_schema", "schema": json_schema}},
    }

    message = client.messages.create(**params)
    return json.loads(message.content[0].text)


def run_evaluations(dataset):
    """Runs through the evaluation dataset and scores accuracy."""
    system_prompt = "Classify the customer support ticket into category and urgency."
    passed_cases = 0
    total_cases = len(dataset)

    print("=========================================")
    print("      RUNNING EVALUATION DATASET         ")
    print("=========================================\n")

    for case in dataset:
        conversation = []
        add_user_message(conversation, f"Classify ticket: {case['question']}")

        # Get structured output prediction
        actual = chat_structured(conversation, system_prompt, TicketClassification)

        # Compare outputs with expected labels
        category_match = actual["category"].lower() == case["expected_category"].lower()
        urgency_match = actual["urgency"].lower() == case["expected_urgency"].lower()

        is_passed = category_match and urgency_match
        if is_passed:
            passed_cases += 1

        print(f"ID: {case['id']}")
        print(f'Ticket: "{case["question"]}"')
        print(
            f"Expected: Category='{case['expected_category']}', Urgency='{case['expected_urgency']}'"
        )
        print(
            f"Actual:   Category='{actual['category']}', Urgency='{actual['urgency']}'"
        )
        print(f"Status:  {'✅ PASS' if is_passed else '❌ FAIL'}\n")

    print("=========================================")
    accuracy = (passed_cases / total_cases) * 100
    print(f"Final Accuracy: {accuracy:.1f}% ({passed_cases}/{total_cases} passed)")
    print("=========================================")


# --- Example Usage ---
if __name__ == "__main__":
    run_evaluations(EVAL_DATASET)
