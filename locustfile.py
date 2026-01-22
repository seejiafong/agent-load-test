import json
import os
import uuid
import time
from queue import Queue, Empty
from locust.exception import StopUser
from locust import HttpUser, task, between, events

# locust -f locustfile.py --host http://localhost:8000

CONVERSATIONS_DIR = "data"

# -------------------------
# Build invocation queue
# -------------------------
invocation_queue = Queue()
TOTAL_INVOCATIONS = 0

for filename in os.listdir(CONVERSATIONS_DIR):
    if not filename.endswith(".json"):
        continue

    with open(os.path.join(CONVERSATIONS_DIR, filename), "r") as f:
        spec = json.load(f)

    name = spec["name"]
    invocations = spec["invocations"]
    conversation = spec["conversation"]

    for _ in range(invocations):
        invocation_queue.put({
            "name": name,
            "conversation": conversation
        })
        TOTAL_INVOCATIONS += 1

if TOTAL_INVOCATIONS == 0:
    raise RuntimeError("No invocations configured!")

print(f"Loaded {TOTAL_INVOCATIONS} total invocations")

# -------------------------
# Single User class
# -------------------------
class ConversationUser(HttpUser):
    wait_time = between(0.01, 0.02)
    stop_timeout = 0

    @task
    def run_once(self):
        try:
            job = invocation_queue.get_nowait()
        except Empty:
            # No work left → stop user
            self.environment.runner.quit_user(self)
            return

        session_id = str(uuid.uuid4())
        conversation = job["conversation"]
        name = job["name"]

        for turn in conversation:
            payload = {
                "role": turn["role"],
                "content": turn["content"]
            }

            url = f"/stream/assistant/{session_id}"

            with self.client.post(
                url,
                json=payload,
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                },
                stream=True,
                catch_response=True,
                name=f"/stream/assistant/{name}"
            ) as response:
                try:
                    if response.status_code != 200:
                        response.failure(f"Bad status {response.status_code}")
                        break

                    # Consume SSE stream
                    for line in response.iter_lines():
                        if not line:
                            continue
                        decoded = line.decode("utf-8")
                        if decoded.strip() == "data: [DONE]":
                            break

                    response.success()

                except Exception as e:
                    response.failure(f"SSE error: {e}")
                    break

            time.sleep(0.05)

        invocation_queue.task_done()
        raise StopUser()