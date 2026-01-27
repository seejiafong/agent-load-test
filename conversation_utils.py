
# conversation_utils.py
import os
import json
import time

# -----------------------------
# SSE request helper
# -----------------------------
def post_stream_request(client, url, headers, payload, convo_name):
    """
    Sends a streaming POST request to the LLM endpoint, collects assistant output,
    and measures latency + TTFT (time to first token).
    """
    assistant_text = ""
    t_request_start = time.time()
    t_first_token = None

    with client.post(
        url,
        json=payload,
        headers=headers,
        stream=True,
        catch_response=True,
        name=f"{convo_name}",
    ) as response:
        try:
            if response.status_code != 200:
                response.failure(f"Bad status {response.status_code}")
                return None, None, None, None

            for line in response.iter_lines():
                if not line:
                    continue

                decoded = line.decode("utf-8")
                if decoded.strip() == "data: [DONE]":
                    break

                if decoded.startswith("data: "):
                    if t_first_token is None:
                        t_first_token = time.time()
                    try:
                        data = json.loads(decoded[6:])
                        delta = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if delta:
                            assistant_text += delta
                    except json.JSONDecodeError:
                        pass

            response.success()

        except Exception as e:
            response.failure(f"SSE error: {e}")
            return None, None, None, None

    t_request_end = time.time()
    return assistant_text, t_request_start, t_request_end, t_first_token


# -----------------------------
# Turn logging helper
# -----------------------------
def log_turn(turn_idx, payload, assistant_text, t_request_start, t_request_end, t_first_token):
    """
    Creates a structured log dictionary for a single conversation turn.
    """
    return {
        "turn_index": turn_idx,
        "request": payload,
        "response": assistant_text,
        "timing": {
            "request_start": t_request_start,
            "first_token": t_first_token,
            "request_end": t_request_end,
            "latency_ms": (t_request_end - t_request_start) * 1000,
            "ttft_ms": ((t_first_token - t_request_start) * 1000) if t_first_token else None,
        },
    }


# -----------------------------
# NDJSON writer helper
# -----------------------------
def write_conversation_log(conversation_log, convo_name, run_log_dir):
    """
    Appends a conversation log to NDJSON file for the given conversation type.
    """
    filepath = os.path.join(run_log_dir, f"{convo_name}.ndjson")
    with open(filepath, "a") as f:
        f.write(json.dumps(conversation_log) + "\n")
