# Understand Python

Framework-neutral Python SDK for sending logs and exceptions to Understand.io.

This package is for Python applications. It does not run inside Laravel and it
does not reimplement the browser JavaScript SDK. Where it shares configuration
names with the Laravel package, that is config parity only.

## Installation

Install from PyPI:

```bash
python3 -m pip install understand-python
```

Or add it to `requirements.txt`:

```text
understand-python
```

## Configuration

Set your Understand.io input token:

```bash
export UNDERSTAND_TOKEN="your-input-token"
export UNDERSTAND_ENV="production"
```

Or configure it directly in code:

```python
from understand import UnderstandConfig

config = UnderstandConfig(
    token="your-input-token",
    environment="production",
)
```

## Basic Usage

Send a log message:

```python
from understand import UnderstandConfig, UnderstandLogger

logger = UnderstandLogger.from_config(
    UnderstandConfig(token="your-input-token", environment="production")
)

logger.error("Understand.io test error", context={"source": "my-app"})
```

Capture and send an exception:

```python
from understand import UnderstandConfig, UnderstandLogger

logger = UnderstandLogger.from_config(
    UnderstandConfig(token="your-input-token", environment="production")
)

try:
    raise RuntimeError("Payment capture failed")
except RuntimeError as exc:
    logger.exception(exc, context={"feature": "payments"})
```

## Stdlib Logging

Attach Understand to Python's built-in `logging` package:

```python
import logging

from understand import UnderstandConfig, UnderstandLogger
from understand.integrations.logging import UnderstandLoggingHandler

understand_logger = UnderstandLogger.from_config(
    UnderstandConfig.from_env()
)

logging.getLogger().addHandler(UnderstandLoggingHandler(understand_logger))
logging.getLogger().setLevel(logging.INFO)

logging.error("This error is sent to Understand.io")
```

Exceptions logged with `exc_info=True` are sent as structured exception events:

```python
try:
    raise ValueError("Invalid checkout amount")
except ValueError:
    logging.exception("Checkout failed")
```

## Request Context

For web applications, attach request-like metadata before logging:

```python
from understand import RequestContext, UnderstandConfig, UnderstandLogger

logger = UnderstandLogger.from_config(
    UnderstandConfig(token="your-input-token", environment="production")
)

logger.field_provider.set_request_context(
    RequestContext(
        path="/checkout/payments",
        method="POST",
        route_name="payments.create",
        query={"debug": "1"},
        body={"amount": 4999, "password": "hidden automatically"},
        client_ip="203.0.113.10",
        user_agent="Mozilla/5.0",
        user_id="user-123",
        session_id="session-id",
    )
)
```

Fields like `password`, `password_confirmation`, `access_token`, `secret_key`,
`token`, and `access_key` are replaced with `[value hidden]` by default.

Environment variables:

- `UNDERSTAND_TOKEN`
- `UNDERSTAND_ENABLED`
- `UNDERSTAND_API_URL`
- `UNDERSTAND_HANDLER`
- `UNDERSTAND_ENV`
- `UNDERSTAND_SQL`
- `UNDERSTAND_SQL_BINDINGS`
- `UNDERSTAND_QUERY_STRING`
- `UNDERSTAND_REQUEST_BODY`
- `UNDERSTAND_POST_DATA` as a SDK config-parity alias for request body collection
- `UNDERSTAND_HIDDEN_REQUEST_FIELDS`
- `UNDERSTAND_SSL_CA_BUNDLE`

For browser JavaScript error tracking, use the separate `understand-js` SDK.

## Long-Running Workers

For long-running workers, call `reset_context()` between jobs to regenerate the
request token and clear collected data:

```python
for job in jobs:
    logger.reset_context()

    try:
        process_job(job)
    except Exception as exc:
        logger.exception(exc, context={"job_id": job.id})
```

## Local Testing Without Sending Data

Use `CallbackHandler` to inspect payloads without making network requests:

```python
import json

from understand import CallbackHandler, UnderstandConfig, UnderstandLogger

events = []
logger = UnderstandLogger.from_config(
    UnderstandConfig(token="test-token", environment="local"),
    handler=CallbackHandler(lambda payload: events.append(json.loads(payload))),
)

logger.error("Local test error")

print(json.dumps(events, indent=2))
```
