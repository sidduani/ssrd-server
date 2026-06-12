import socket
import threading
import random
import string
import os

# Render dynamically assigns a port via environment variables
PORT = int(os.environ.get("PORT", 6000))
connected_clients = {}

def generate_credentials():
    while True:
        uid = str(random.randint(100000, 999999))
        if uid not in connected_clients:
            break
    pwd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return uid, pwd

def handle_client(conn, addr):
    my_id, my_pwd = generate_credentials()
    connected_clients[my_id] = {"conn": conn, "password": my_pwd}
    try:
        conn.sendall(f"CREDENTIALS:{my_id}:{my_pwd}".encode('utf-8'))
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data: break
            if data.startswith("CONNECT:"):
                _, target_id, target_pwd = data.split(":")
                if target_id in connected_clients and target_id != my_id:
                    if connected_clients[target_id]["password"] == target_pwd:
                        target_conn = connected_clients[target_id]["conn"]
                        target_conn.sendall(f"PAIR_AS_SENDER:{addr[0]}".encode('utf-8'))
                        conn.sendall(f"PAIR_AS_RECEIVER:{target_conn.getpeername()[0]}".encode('utf-8'))
                    else:
                        conn.sendall(b"ERROR:Incorrect Password")
                else:
                    conn.sendall(b"ERROR:Invalid ID or Partner Offline")
    except Exception: pass
    finally:
        if my_id in connected_clients: del connected_clients[my_id]
        conn.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(50)
    print(f"Server active on port {PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()