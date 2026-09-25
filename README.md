# HTTP Calculator Server

A small HTTP/1.1 calculator server built with Python's standard library and raw TCP sockets.

## Features

- Persistent HTTP connections
- Multiple requests over one TCP connection
- Fragmented and pipelined request handling
- Exact `Content-Length` request framing
- `GET` endpoints for addition, subtraction, multiplication, and division

## Requirements

- Python 3.10 or newer
- `pytest` for running tests

## Run the server

```bash
python3 server.py
```

The server listens on `127.0.0.1:8080` by default. Configure the address and port with:

```bash
python3 server.py --host 127.0.0.1 --port 8080
```

## API

Each request must include a `Host` header and `Content-Length: 0`.

```text
GET /add?a=2&b=3 HTTP/1.1
Host: localhost
Content-Length: 0
```

Available endpoints:

| Endpoint | Example | Result |
| --- | --- | --- |
| `/add` | `/add?a=2&b=3` | `5` |
| `/sub` | `/sub?a=10&b=4` | `6` |
| `/mul` | `/mul?a=6&b=7` | `42` |
| `/div` | `/div?a=9&b=3` | `3` |

Invalid requests return `400 Bad Request`, unknown paths return `404 Not Found`, and non-`GET` methods return `405 Method Not Allowed`.

## Tests

Create or activate a virtual environment, install pytest, and run:

```bash
python3 -m pip install pytest
python3 -m pytest -q
```

The test suite covers arithmetic, request validation, fragmented requests, and six pipelined requests on one persistent connection.# calculator_server
