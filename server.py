#!/usr/bin/env python3
"""A small HTTP/1.1 calculator server using only TCP sockets."""

import argparse
import socket
from urllib.parse import parse_qs, urlsplit


MAX_REQUEST_SIZE = 64 * 1024


def response(status, body, keep_alive=True):
    reason = {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
    }[status]
    body_bytes = body.encode("utf-8")
    connection = "keep-alive" if keep_alive else "close"
    headers = (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Connection: {connection}\r\n"
        "\r\n"
    ).encode("ascii")
    return headers + body_bytes


def calculate(path):
    parsed = urlsplit(path)
    if parsed.path not in {"/add", "/sub", "/mul", "/div"}:
        return 404, "Not Found"

    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"a", "b"} or any(len(values) != 1 for values in query.values()):
        return 400, "Bad Request"

    try:
        left = int(query["a"][0])
        right = int(query["b"][0])
        if parsed.path == "/add":
            result = left + right
        elif parsed.path == "/sub":
            result = left - right
        elif parsed.path == "/mul":
            result = left * right
        else:
            if right == 0:
                return 400, "Bad Request"
            result = left // right
    except (TypeError, ValueError, ZeroDivisionError):
        return 400, "Bad Request"

    return 200, str(result)


def handle_request(request):
    header_block, body = request.split(b"\r\n\r\n", 1)
    lines = header_block.decode("iso-8859-1").split("\r\n")
    request_line = lines[0].split()
    if len(request_line) != 3:
        return response(400, "Bad Request")

    method, target, version = request_line
    if version != "HTTP/1.1":
        return response(400, "Bad Request")
    if method != "GET":
        return response(405, "Method Not Allowed")

    headers = {}
    for line in lines[1:]:
        if not line or ":" not in line:
            return response(400, "Bad Request")
        name, value = line.split(":", 1)
        headers[name.lower().strip()] = value.strip()

    try:
        content_length = int(headers.get("content-length", "0"))
    except ValueError:
        return response(400, "Bad Request")
    if content_length < 0 or content_length != len(body):
        return response(400, "Bad Request")
    if "host" not in headers:
        return response(400, "Bad Request")

    status, result = calculate(target)
    return response(status, result)


def serve_client(connection):
    buffer = b""
    try:
        while True:
            separator = buffer.find(b"\r\n\r\n")
            while separator < 0:
                chunk = connection.recv(4096)
                if not chunk:
                    return
                buffer += chunk
                if len(buffer) > MAX_REQUEST_SIZE:
                    connection.sendall(response(400, "Bad Request", False))
                    return
                separator = buffer.find(b"\r\n\r\n")

            header_end = separator + 4
            header_lines = buffer[:separator].split(b"\r\n")
            content_length = 0
            for line in header_lines[1:]:
                if line.lower().startswith(b"content-length:"):
                    try:
                        content_length = int(line.split(b":", 1)[1].strip())
                    except ValueError:
                        content_length = -1
                    break

            request_end = header_end + max(content_length, 0)
            while content_length >= 0 and len(buffer) < request_end:
                chunk = connection.recv(4096)
                if not chunk:
                    return
                buffer += chunk
                if len(buffer) > MAX_REQUEST_SIZE:
                    connection.sendall(response(400, "Bad Request", False))
                    return

            if content_length < 0:
                request_end = header_end
            request = buffer[:request_end]
            buffer = buffer[request_end:]
            connection.sendall(handle_request(request))
    finally:
        connection.close()


def run(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen()
        print(f"Calculator server listening on {host}:{port}", flush=True)
        while True:
            connection, _ = server.accept()
            serve_client(connection)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP/1.1 socket calculator")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    arguments = parser.parse_args()
    run(arguments.host, arguments.port)