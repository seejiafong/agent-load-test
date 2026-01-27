""" Example class testing against openrouter api"""

import json
import os
import uuid
import time
from datetime import datetime
from random import choices
from locust import HttpUser, task, between, events
from conversation_utils import post_stream_request, log_turn, write_conversation_log

CONVERSATIONS_DIR = "data"

RUN_LOG_DIR = "logs"

URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
}

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global RUN_LOG_DIR

    timestamp = datetime.now().strftime("%m%d%H:%M")
    RUN_LOG_DIR = os.path.join("logs", f"run-{timestamp}")

    os.makedirs(RUN_LOG_DIR, exist_ok=True)

    print(f"[Locust] Logging conversations to {RUN_LOG_DIR}")


# -------------------------
# Load conversation specs
# -------------------------
conversations = []

for filename in os.listdir(CONVERSATIONS_DIR):
    if not filename.endswith(".json"):
        continue

    with open(os.path.join(CONVERSATIONS_DIR, filename), "r") as f:
        spec = json.load(f)

    conversations.append({
        "name": spec["name"],
        "weight": spec["weight"],
        "conversation": spec["conversation"],
    })

if not conversations:
    raise RuntimeError("No conversations found!")

names = [c["name"] for c in conversations]
weights = [c["weight"] for c in conversations]

# -------------------------
# User definition
# -------------------------
class ConversationUser(HttpUser):
    # wait 1 - 3 seconds between tasks
    wait_time = between(1, 3)

    @task
    def run_conversation(self):
        convo = choices(conversations, weights=weights, k=1)[0]
        session_id = str(uuid.uuid4())
        messages = []

        conversation_log = {
            "conversation_name": convo["name"],
            "session_id": session_id,
            "started_at": time.time(),
            "turns": [],
        }

        for turn_idx, turn in enumerate(convo["conversation"]):
            messages.append({
                "role": turn["role"],
                "content": turn["content"],
            })

            payload = {
                "model": "openai/gpt-4o",
                "messages": messages.copy(),
                "stream": True,
            }

            assistant_text, t_request_start, t_request_end, t_first_token = post_stream_request(
                self.client, URL, HEADERS, payload, convo["name"]
                #+"_"+session_id[0:5]
            )

            if assistant_text is None:
                break  # Stop on failure

            conversation_log["turns"].append(
                log_turn(turn_idx, payload, assistant_text, t_request_start, t_request_end, t_first_token)
            )

            messages.append({
                "role": "assistant",
                "content": assistant_text,
            })

            time.sleep(0.2)

        conversation_log["ended_at"] = time.time()
        conversation_log["total_latency_ms"] = (conversation_log["ended_at"] - conversation_log["started_at"]) * 1000

        write_conversation_log(conversation_log, convo["name"]+"_"+session_id[0:5], RUN_LOG_DIR)