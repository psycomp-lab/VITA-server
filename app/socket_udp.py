import socket
import threading
import time
from flask_socketio import SocketIO
from app.models import db, Session
from app import app
from socket import inet_aton, inet_ntoa

socketio = SocketIO(app, async_mode='threading')

@socketio.on('connected')
def connect():
    print('Page connected')

MESSAGE_PORT = 50069
BROADCAST_PORT = 50068
BEACON_MESSAGE = b"BEACON"
BEACON_ACK = b"ACK"
CONNECT_MESSAGE = b"CONNECT"
CONNECT_ACK = b"CONNECT_ACK"
DATA_ACK = b"DATA_ACK"
client_ips = []
TIMEOUT_SECONDS = 5
CHECK_INTERVAL_SECONDS = 3600
CONNECTED = False
CONNECTED_CLIENT = None
last_connection_checked = None
connection_event = threading.Event()

LIST_MSG = []

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_data(msg):
    try:
            recv_socket.sendto(msg.encode("utf-8"), CONNECTED_CLIENT)
            #resp, addr = recv_socket.recvfrom(1024 ** 2)
            '''if addr == CONNECTED_CLIENT and resp == DATA_ACK:
                parts = msg.split("_")
                for digit in parts[3]:
                    LIST_MSG.append(int(digit))
                break'''
            connection_event.set()
    except Exception as e:
        print(e)


def is_connected():
    return CONNECTED

# Maurizio-start
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        # print("***********", s.getsockname())
    except Exception as e:
        print(f"Failed to get local ip: {e}")
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
# Maurizio-end

def send_connect(client):
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked
    try:
        recv_socket.sendto(CONNECT_MESSAGE, client)
        msg, addr = recv_socket.recvfrom(1024 ** 2)
        if msg == CONNECT_ACK and addr == client:
            print(f'[CONNECT] to {client}')
            CONNECTED = True
            CONNECTED_CLIENT = client
            last_connection_checked = time.time()  # GET CONNECTION RECEIVED TIME
    except Exception as e:
        print(f"Failed connection to client: {e}")


def send_beacon_packets():
    broadip = inet_ntoa( inet_aton(get_local_ip())[:3] + b'\xff' )
    while True:
        if not CONNECTED:
            try:
                sock.sendto(BEACON_MESSAGE, (broadip, BROADCAST_PORT))
                print("[BEACON] sent beacon for discovery")
            except Exception as e:
                print(f"Failed to send beacon packet: {e}")

            # Receive ACK packets from clients and store their IP addresses
            try:
                data, addr = recv_socket.recvfrom(1024 ** 2)
                if data == BEACON_ACK:
                    print(f"[ACK] from {addr}")
                    if addr not in client_ips:
                        client_ips.append(addr)
            except socket.timeout:
                pass


def main():
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked

    # Enable broadcasting
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Set the TTL value to 4
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)

    # Create a UDP socket for receiving ACK packets
    recv_socket.bind(("", MESSAGE_PORT))
    print("[SOCKET] started socket for communication")

    # Set a timeout for receiving ACK packets
    recv_socket.settimeout(TIMEOUT_SECONDS)

    # Spawn a thread to send beacon packets for the specified duration
    beacon_thread = threading.Thread(target=send_beacon_packets)
    beacon_thread.start()

    # Waits for a connection
    connection_event.wait()

    # Check messages, connections and send SOCKETIO notifications (all pages socket?)
    while CONNECTED:
        try:
        
            msg, addr = recv_socket.recvfrom(1024 ** 2)

            if addr == CONNECTED_CLIENT:

                last_connection_checked = time.time()

                if msg.decode().startswith("FINISHED_EXERCISE "):
                    print("***** received finished_exercise")
                    msg = msg.decode()
                    tokens = msg.split(" ")
                    number = int(tokens[1])
                    id = int(tokens[2])
                    result = tokens[3]
                    print(tokens)
                    with app.app_context():
                        session = Session.query.filter_by(user_id=id, exercise=number).order_by(Session.number.desc()).first()
                        if session:
                            #session.result = result
                            db.session.commit()
                            socketio.emit("exercise", number)
                            print(f"Updated session {number} for user {id} with result: {result}")
                        else:
                            print(f"No session found for user {id} with number {number}")
                elif msg.decode() == "END_SESSION":
                    socketio.emit("end_session")
                else:
                    print(msg.decode())
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error while checking connection: {e}")

        # CHECK TIME NOW - LAST CHECK LESS THAN THE INTERVAL
        if time.time() - last_connection_checked > CHECK_INTERVAL_SECONDS:
            CONNECTED = False
            CONNECTED_CLIENT = None
            socketio.emit("disconnect-vr")
