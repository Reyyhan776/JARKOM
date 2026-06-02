import socket
import threading
import time

WEBSERVER_HOST = '127.0.0.1'
WEBSERVER_PORT = 8000

cache = {}
cache_lock = threading.Lock()

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [PROXY] {msg}')

def parse_request(data):
    try:
        text = data.decode('utf-8', errors='ignore')
        line = text.split('\r\n')[0]
        parts = line.split()
        if len(parts) >= 2:
            return parts[0], parts[1]
    except:
        pass
    return None, None

def forward(data):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((WEBSERVER_HOST, WEBSERVER_PORT))
        sock.sendall(data)
        resp = b''
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
            except socket.timeout:
                break
        sock.close()
        return resp, 200
    except socket.timeout:
        return b'HTTP/1.1 504 Gateway Timeout\r\nContent-Type: text/plain\r\nContent-Length: 15\r\nConnection: close\r\n\r\nGateway Timeout', 504
    except:
        return b'HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/plain\r\nContent-Length: 11\r\nConnection: close\r\n\r\nBad Gateway', 502

def handle_client(conn, addr):
    client_ip = addr[0]
    log(f'Client connected: {client_ip}')
    try:
        data = conn.recv(4096)
        if not data:
            return
        method, path = parse_request(data)
        if method != 'GET' or path is None:
            conn.sendall(b'HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n')
            return
        log(f'{client_ip} -> {method} {path}')
        with cache_lock:
            if path in cache:
                log(f'CACHE HIT: {path}')
                conn.sendall(cache[path])
                return
        log(f'CACHE MISS: {path} -> forwarding to {WEBSERVER_HOST}:{WEBSERVER_PORT}')
        resp_bytes, status = forward(data)
        if status == 200:
            with cache_lock:
                cache[path] = resp_bytes
                log(f'CACHED: {path}')
        conn.sendall(resp_bytes)
        log(f'{client_ip} {path} -> {status}')
    except Exception as e:
        log(f'Error: {e}')
        try:
            conn.sendall(b'HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\n')
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 8888))
    sock.listen(10)
    log(f'Proxy server listening on port 8888')
    log(f'Forwarding to {WEBSERVER_HOST}:{WEBSERVER_PORT}')
    try:
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        log('Shutting down...')
    finally:
        sock.close()

if __name__ == '__main__':
    main()
