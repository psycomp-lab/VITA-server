import socket
import time

BROADCAST_PORT = 50068
ACK_MESSAGE = "ACK"

def receive_beacon_and_send_ack():
    # Create a UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client_socket.bind(("", BROADCAST_PORT))
    print("[CLIENT] Started listening for beacon")
    try:
        data, addr = client_socket.recvfrom(1024)
        print("[RECEIVED] Received beacon from server:", data.decode())

        # Send ACK message back to server
        client_socket.sendto(ACK_MESSAGE.encode(), (addr[0],50069))
        print(f"[ACK] Sent acknowledgment to server {addr}")
    except Exception as e:
        print(e)
    while True:
        try:
            msg,addr = client_socket.recvfrom(1024**2)
            print(msg.decode()+'qui')
            if msg == b'CONNECT':
                client_socket.sendto(b'CONNECT',addr)
                break
        except socket.timeout:
            pass

    print("QUI")
    while True:
        # Receive message
        try:
            msg,_=client_socket.recvfrom(1024)
            if msg.decode().startswith('DATA:'):
                print(msg)
                break
        except socket.timeout:
            pass

    time.sleep(5)
    message = "FINISHED_EXERCISE: "
    while True:
        inp = int(input("AZIONE"))
        if inp == 0:
            break
        elif inp == 6:
            client_socket.sendto(b'CONNECT',addr)
        elif inp == 7:
            client_socket.sendto(b'END_SESSION',addr)
        else:
            message = "FINISHED_EXERCISE: "+str(inp)+"ID: 1933858"+"RESULT: BELLO"
            client_socket.sendto(message.encode(),(addr))
            print(f"SENT EXERCISE {addr[0]}")


if __name__ == "__main__":
    receive_beacon_and_send_ack()