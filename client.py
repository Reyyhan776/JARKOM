import socket
import time
import statistics
import argparse
import sys

PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8888
UDP_HOST = '127.0.0.1'
UDP_PORT = 9000

def tcp_get(path):
    print(f'[TCP] Connecting to {PROXY_HOST}:{PROXY_PORT} ...')
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((PROXY_HOST, PROXY_PORT))
        request = (
            f'GET {path} HTTP/1.1\r\n'
            f'Host: localhost\r\n'
            f'Connection: close\r\n'
            f'\r\n'
        )
        sock.sendall(request.encode())
        response = b''
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                break
        sock.close()
        print(response.decode('utf-8', errors='replace'))
    except ConnectionRefusedError:
        print(f'[TCP] ERROR: Cannot connect to {PROXY_HOST}:{PROXY_PORT}')
        print('[TCP] Make sure proxy.py is running')
        sys.exit(1)
    except Exception as e:
        print(f'[TCP] ERROR: {e}')
        sys.exit(1)

def udp_ping(count=10, timeout=1.0):
    print(f'[UDP] Pinging {UDP_HOST}:{UDP_PORT} ({count} packets)')
    print()
    rtts = []
    sent = 0
    received = 0
    total_bytes = 0
    start = time.time()

    for seq in range(1, count + 1):
        payload = f'Ping {seq} {time.time()}'.encode()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        t0 = time.time()
        try:
            sock.sendto(payload, (UDP_HOST, UDP_PORT))
            sent += 1
            data, _ = sock.recvfrom(1024)
            t1 = time.time()
            rtt = (t1 - t0) * 1000
            rtts.append(rtt)
            received += 1
            total_bytes += len(data)
            print(f'[UDP] seq={seq} rtt={rtt:.2f}ms size={len(data)}B')
        except socket.timeout:
            print(f'[UDP] seq={seq} timed out')
        except Exception as e:
            print(f'[UDP] seq={seq} error: {e}')
        finally:
            sock.close()

    duration = time.time() - start
    loss = ((sent - received) / sent * 100) if sent else 0
    print()
    print('=' * 40)
    print('  QoS STATISTICS')
    print('=' * 40)
    print(f'  Packets sent     : {sent}')
    print(f'  Packets received : {received}')
    print(f'  Packet loss      : {loss:.1f}%')
    if rtts:
        print(f'  RTT min          : {min(rtts):.2f} ms')
        print(f'  RTT avg          : {statistics.mean(rtts):.2f} ms')
        print(f'  RTT max          : {max(rtts):.2f} ms')
        if len(rtts) > 1:
            diffs = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
            jitter = statistics.stdev(diffs) if len(diffs) > 1 else 0
            print(f'  Jitter           : {jitter:.2f} ms')
        else:
            print(f'  Jitter           : 0.00 ms')
        throughput = (total_bytes * 8) / duration / 1000 if duration > 0 else 0
        print(f'  Throughput       : {throughput:.2f} kbps')
    else:
        print(f'  RTT              : N/A (all packets lost)')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Jarkom TCP/UDP Client')
    parser.add_argument('--mode', choices=['tcp', 'udp'], required=True, help='tcp or udp')
    parser.add_argument('--path', default='/index.html', help='path for TCP request')
    parser.add_argument('--count', type=int, default=10, help='UDP ping count')
    parser.add_argument('--timeout', type=float, default=1.0, help='UDP timeout in seconds')
    args = parser.parse_args()
    if args.mode == 'tcp':
        tcp_get(args.path)
    else:
        udp_ping(args.count, args.timeout)
