# Load Test

A load testing suite using [Locust](https://locust.io/) to test streaming API endpoints with realistic conversation scenarios.

## Overview

This project consists of sample conversations under the **data** folder.  
Each conversation should exercise a different agent workflow.  
The number of such concurrent workflows is defined as "invocations" within the conversation json file.

## Features

- **Conversation-based load testing**: Define realistic multi-turn conversations in JSON format
- **SSE streaming support**: Properly handles Server-Sent Events responses
- **Configurable invocations**: Specify how many times each conversation should be executed
- **Session management**: Generates unique session IDs for each conversation flow
- **Performance metrics**: Automatic collection of response times, success/failure rates, and more via Locust

## Requirements

- Python 3.13 or higher
- Poetry (for dependency management)

## Installation

1. Clone or navigate to this repository
2. Install dependencies using Poetry:

```bash
uv venv --python=3.13
bash act-env.sh
uv pip install poetry
poetry install
```

This will install:
- `locust` - Load testing framework

## Project Structure

```
load-test/
├── locustfile.py           # Main Locust load test file
├── data/                   # Test conversation data
│   └── conversation_A.json # Example conversation scenario
├── pyproject.toml          # Poetry configuration
├── README.md              # This file
└── .venv/                 # Virtual environment
```

## Configuration

### Conversation Format

Create conversation files in the `data/` directory as JSON files. Each file is 1 multiturn conversation:

```json
{
  "name": "conversation_A",
  "invocations": 25, //number of such concurrent conversations
  "conversation": [
    { "role": "user", "content": "Hello" },
    { "role": "user", "content": "Explain async APIs" }
  ]
}
```

**Fields:**
- `name` (string): Identifier for this conversation scenario
- `invocations` (number): How many times this conversation should be executed across all users
- `conversation` (array): Multi-turn conversation with role/content pairs


## Usage

### Running Tests

#### Using Locust Web UI

```bash
poetry run locust -f locustfile.py --host http://localhost:8000
```

Then open `http://localhost:8000` in your browser to start the load test.

#### Headless Mode (Command Line)

```bash
poetry run locust -f locustfile.py \
  --headless \
  --users 55 \
  -r 55 \
  --host http://localhost:8000
```

**Parameters:**
- `--headless`: Run without web UI
- `--users`: Number of concurrent users
- `-r`: Ramp-up rate (users spawned per second)
- `--host`: Target API endpoint

#### Using VS Code Debugger

A debug configuration is included for VS Code. Press `F5` to start debugging with:
- 55 concurrent users
- Target: `http://localhost:8000`

## How It Works

1. **Load Phase**: All conversation files in the `data/` directory are loaded into a queue with the specified number of invocations
2. **User Execution**: Each virtual user retrieves one conversation from the queue and executes it
3. **Conversation Flow**: For each turn in a conversation:
   - A unique session ID is generated
   - A POST request is sent to `/stream/assistant/{session_id}`
   - The SSE stream response is consumed until `[DONE]` is received
   - Results are recorded as success or failure
4. **Completion**: Users stop when no more conversations remain in the queue

## API Requirements

The target API should:
- Accept POST requests to `/stream/assistant/{session_id}`
- Support the following headers:
  - `Accept: text/event-stream`
  - `Content-Type: application/json`
- Expect JSON payload with `role` and `content` fields
- Return Server-Sent Events (SSE) format responses
- Indicate completion with `data: [DONE]`

## Metrics

Locust automatically provides:
- Request count and response times
- Success/failure rates
- Request/second (RPS) throughput
- Failure reasons and error messages
- P50, P95, P99 response time percentiles

## Troubleshooting

**No invocations configured error**
- Ensure at least one JSON conversation file exists in the `data/` directory
- Verify each conversation file has a valid `invocations` count (> 0)

**Connection refused**
- Ensure your target API is running on the specified host
- Check that the API endpoint is accessible: `http://target-host/stream/assistant/{id}`

**SSE parsing errors**
- Verify the API returns proper SSE format
- Check that responses end with `data: [DONE]`

## License

This project is provided as-is for testing purposes.
