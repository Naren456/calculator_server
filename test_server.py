import socket
import threading

import pytest

import server


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/add?a=2&b=3", (200, "5")),
        ("/sub?a=10&b=4", (200, "6")),
        ("/mul?a=6&b=7", (200, "42")),
        ("/div?a=9&b=3", (200, "3")),
        ("/div?a=1&b=0", (400, "Bad Request")),
        ("/add?a=1", (400, "Bad Request")),
        ("/pow?a=2&b=8", (404, "Not Found")),
    ],
)
def test_calculate(path, expected):
    assert server.calculate(path) == expected


def request(method="GET", target="/add?a=2&b=3", body=b"", host=True):
    headers = []
    if host:
        headers.append("Host: localhost")
    headers.append(f"Content-Length: {len(body)}")
    return (
        f"{method} {target} HTTP/1.1\r\n"
        + "\r\n".join(headers)
        + "\r\n\r\n"
    ).encode() + body


def read_response(connection, buffer=b""):
    while b"\r\n\r\n" not in buffer:
        buffer += connection.recv(4096)
    headers, buffer = buffer.split(b"\r\n\r\n", 1)
    content_length = int(
        next(
            line.split(b":", 1)[1]
            for line in headers.split(b"\r\n")
            if line.lower().startswith(b"content-length:")
        )
    )
    while len(buffer) < content_length:
        buffer += connection.recv(4096)
    body = buffer[:content_length]
    return headers.split(b"\r\n", 1)[0], body, buffer[content_length:]


def test_handle_request_rejects_invalid_method_and_missing_host():
    assert b"405 Method Not Allowed" in server.handle_request(request("POST"))
    assert b"400 Bad Request" in server.handle_request(request(host=False))


def test_keep_alive_handles_fragmented_and_pipelined_requests():
    client, server_socket = socket.socketpair()
    thread = threading.Thread(target=server.serve_client, args=(server_socket,))
    thread.start()
    requests = [
        request(target="/add?a=2&b=3"),
        request(target="/sub?a=10&b=4"),
        request(target="/mul?a=6&b=7"),
        request(target="/div?a=1&b=0"),
        request(target="/pow?a=2&b=8"),
        request("POST", "/add"),
    ]

    try:
        client.sendall(requests[0][:20])
        client.sendall(requests[0][20:] + b"".join(requests[1:]))
        buffer = b""
        responses = []
        for _ in requests:
            status, body, buffer = read_response(client, buffer)
            responses.append((status, body))

        assert responses == [
            (b"HTTP/1.1 200 OK", b"5"),
            (b"HTTP/1.1 200 OK", b"6"),
            (b"HTTP/1.1 200 OK", b"42"),
            (b"HTTP/1.1 400 Bad Request", b"Bad Request"),
            (b"HTTP/1.1 404 Not Found", b"Not Found"),
            (b"HTTP/1.1 405 Method Not Allowed", b"Method Not Allowed"),
        ]
    finally:
        client.close()
        thread.join(timeout=1)

    assert not thread.is_alive()