
import socket

HOST = "0.0.0.0"
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(5)

print(f"IoT receiver listening on port {PORT}")

while True:
    conn, address = server.accept()

    with conn:
        print("Connected:", address)
        data = conn.recv(1024).decode("utf-8")
        print("Received:", data)

        conn.sendall(b"ACK")
