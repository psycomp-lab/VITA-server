import socket

BROADCAST_PORT = 50068
MESSAGE_PORT = 50069
BEACON_ACK = b"BEACON_ACK"
CONNECT_ACK = b"CONNECT_ACK"
DATA_ACK = b"DATA_ACK"

def receive_beacon_and_send_ack():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client_socket.bind(("", BROADCAST_PORT))
    print("[CLIENT] Started listening for beacon")

    try:
        data, addr = client_socket.recvfrom(1024)
        if data == b"BEACON":
            print("[RECEIVED] Received beacon from server")
            client_socket.sendto(BEACON_ACK, (addr[0], MESSAGE_PORT))
            print(f"[ACK] Sent acknowledgment to server {addr}")
    except Exception as e:
        print(f"Error receiving beacon: {e}")

    while True:
        try:
            msg, addr = client_socket.recvfrom(1024)
            if msg == b"CONNECT":
                client_socket.sendto(CONNECT_ACK, addr)
                print("[CONNECTED] Connected to server")
            elif msg.startswith(b"SESSION"):
                print(f"[DATA] Received data: {msg.decode()}")
                client_socket.sendto(DATA_ACK, addr)
            elif msg.decode().startswith("WAITING"):
                parts = msg.decode().split(" ")
                s = "FINISHED_EXERCISE "+parts[1]+" 1933858 bello"
                print(s)
                client_socket.sendto(s.encode("utf-8"),addr)
            elif msg == b"RESTART":
                client_socket.sendto(b"RESTART_ACK",addr)
            elif msg == b"PAUSE":
                client_socket.sendto(b"PAUSE_ACK",addr)
            elif msg == b"CONNECT":
                client_socket.sendto(CONNECT_ACK, addr)
                print("Headset is stil connected")
        except socket.timeout:
            pass

if __name__ == "__main__":
    receive_beacon_and_send_ack()
