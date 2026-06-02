import socket
import threading
import os
import sys
import time
import mimetypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_mime_type(filename):
    mime, _ = mimetypes.guess_type(filename)
    return mime or 'application/octet-stream'

def resolve_path(request_path):
    if not request_path or request_path == '/':
        request_path = '/index.html'
    clean = request_path.lstrip('/')
    normalized = os.path.normpath(clean)
    if normalized.startswith('..') or os.path.isabs(normalized):
        return None
    abs_path = os.path.join(BASE_DIR, normalized)
    if not abs_path.startswith(BASE_DIR):
        return None
    return abs_path

def build_response(status_code, body, mime='text/plain'):
    status_map = {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found', 500: 'Internal Server Error'}
    status_text = status_map.get(status_code, 'Unknown')
    headers = (
        f'HTTP/1.1 {status_code} {status_text}\r\n'
        f'Content-Type: {mime}\r\n'
        f'Content-Length: {len(body)}\r\n'
        f'Connection: close\r\n'
        f'\r\n'
    )
    return headers.encode() + body

def handle_tcp(conn, addr):
    client_ip = addr[0]
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        data = conn.recv(4096)
        if not data:
            return
        request_line = data.decode('utf-8', errors='ignore').split('\r\n')[0]
        parts = request_line.split()
        if len(parts) < 2 or parts[0] != 'GET':
            conn.sendall(build_response(400, b'Bad Request'))
            return
        path = parts[1]
        print(f'[{ts}] [{client_ip}] GET {path}')
        abs_path = resolve_path(path)
        if abs_path is None or not os.path.isfile(abs_path):
            print(f'[{ts}] [{client_ip}] {path} -> 404')
            conn.sendall(build_response(404, b'404 Not Found'))
            return
        with open(abs_path, 'rb') as f:
            body = f.read()
        mime = get_mime_type(abs_path)
        print(f'[{ts}] [{client_ip}] {path} -> 200 ({mime})')
        conn.sendall(build_response(200, body, mime))
    except Exception as e:
        print(f'[{ts}] [{client_ip}] ERROR: {e}')
        try:
            conn.sendall(build_response(500, b'Internal Server Error'))
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass

def run_http_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 8000))
    sock.listen(5)
    print('[HTTP] Web server listening on port 8000')
    while True:
        try:
            conn, addr = sock.accept()
            threading.Thread(target=handle_tcp, args=(conn, addr), daemon=True).start()
        except:
            break

def run_udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 9000))
    print('[UDP] Echo server listening on port 9000')
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            payload = data.decode('utf-8', errors='replace')
            print(f'[UDP] Received from {addr[0]}:{addr[1]} -> {payload}')
            sock.sendto(data, addr)
        except:
            break

if __name__ == '__main__':
    threading.Thread(target=run_http_server, daemon=True).start()
    threading.Thread(target=run_udp_server, daemon=True).start()
    print('[SERVER] Running. Press Ctrl+C to stop.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('[SERVER] Shutting down...')
        sys.exit(0)
