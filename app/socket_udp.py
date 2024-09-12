import socket
import threading
import time
from flask_socketio import SocketIO
from app.models import db, Session
from app import app
from socket import inet_aton, inet_ntoa

socketio = SocketIO(app, async_mode='threading')

# Global flags and synchronization primitives
PAUSE = False
RESTART = False
PAUSE_ACK = b"PAUSE_ACK"
RESTART_ACK = b"RESTART_ACK"

@socketio.on('restart')
def handle_restart():
    global RESTART
    RESTART = True

@socketio.on('pause')
def handle_pause():
    global PAUSE
    PAUSE = True

MESSAGE_PORT = 50069
BROADCAST_PORT = 50068

BEACON_MESSAGE = b"BEACON"
BEACON_ACK = b"BEACON_ACK"
CONNECT_MESSAGE = b"CONNECT"
CONNECT_ACK = b"CONNECT_ACK"
DATA_ACK = b"DATA_ACK"

saved_data = {}
client_ips = []

TIMEOUT_SECONDS = 5
CHECK_INTERVAL_SECONDS = 3600
CONNECTED = False
CONNECTED_CLIENT = None
last_connection_checked = None
connection_event = threading.Event()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_data(msg):
    while True:
        try:
            recv_socket.sendto(msg.encode("utf-8"), CONNECTED_CLIENT)
            resp, addr = recv_socket.recvfrom(1024 ** 2)
            if addr == CONNECTED_CLIENT and resp == DATA_ACK:
                print(f"[DATA] sent data to client {msg}")
                save_data(msg)
                connection_event.set()
                break
        except Exception as e:
            print(f"Failed to send data to client: {e}")

def is_connected():
    return CONNECTED

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception as e:
        print(f"Failed to get local ip: {e}")
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def send_connect(client):
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked
    try:
        recv_socket.sendto(CONNECT_MESSAGE, client)
        msg, addr = recv_socket.recvfrom(1024 ** 2)
        if msg == CONNECT_ACK and addr == client:
            print("[CONNECT] connected to client")
            CONNECTED = True
            CONNECTED_CLIENT = client
            last_connection_checked = time.time()
    except Exception as e:
        print(f"Failed connection to client: {e}")

def send_beacon_packets():
    broadip = inet_ntoa(inet_aton(get_local_ip())[:3] + b'\xff')
    while True:
        if not CONNECTED:
            try:
                sock.sendto(BEACON_MESSAGE, ("127.0.0.1", BROADCAST_PORT))
                print("[BEACON] sent beacon for discovery")
            except Exception as e:
                print(f"Failed to send beacon packet: {e}")

            try:
                data, addr = recv_socket.recvfrom(1024 ** 2)
                if data == BEACON_ACK:
                    print("[ACK] received a discovery ack from client")
                    if addr not in client_ips:
                        client_ips.append(addr)
            except socket.timeout:
                pass

def main():
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked, RESTART, PAUSE

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)

    recv_socket.bind(("", MESSAGE_PORT))
    print("[SOCKET] started socket for communication")
    recv_socket.settimeout(TIMEOUT_SECONDS)

    beacon_thread = threading.Thread(target=send_beacon_packets)
    beacon_thread.start()

    connection_event.wait()

    index = 0
    time.sleep(5)

    while CONNECTED:
        if index >= len(saved_data.get("list_exercises", [])):
            CONNECTED = False
            CONNECTED_CLIENT = None
            socketio.emit("end_session")
            break

        if PAUSE:
            msg = "PAUSE"
        elif RESTART:
            msg = "RESTART"
        else:
            msg = "WAITING "+ saved_data.get("list_exercises", [])[index] +" "+ saved_data.get("id", "")+" "+saved_data.get("session", "")
        try:
            recv_socket.sendto(msg.encode("utf-8"), CONNECTED_CLIENT)
            print(f"[SENT] sent {msg}")
            msg, addr = recv_socket.recvfrom(1024 ** 2)

            if addr == CONNECTED_CLIENT:
                last_connection_checked = time.time()

                if msg.decode().startswith("FINISHED_EXERCISE "):
                    index += 1
                    print("***** received finished_exercise")
                    msg = msg.decode()
                    tokens = msg.split(" ")
                    number = int(tokens[1])
                    id = int(tokens[2])
                    result = tokens[3].encode("utf-8")

                    with app.app_context():
                        session = Session.query.filter_by(user_id=id, exercise=number).order_by(Session.number.desc()).first()
                        if session:
                            session.result = result
                            db.session.commit()
                            socketio.emit("exercise", number)
                            print(f"Updated session {number} for user {id} with result: {result}")
                        else:
                            print(f"No session found for user {id} with number {number}")
                elif msg == RESTART_ACK:
                    RESTART = False
                    print("[RESTART_ACK] received")
                elif msg == PAUSE_ACK:
                    PAUSE = False
                    print("[PAUSE_ACK] received")
                else:
                    print(msg.decode() + "QUI")

        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error while checking connection: {e}")

        if time.time() - last_connection_checked > CHECK_INTERVAL_SECONDS:
            CONNECTED = False
            CONNECTED_CLIENT = None
            socketio.emit("disconnect-vr")

def save_data(msg: str):
    global saved_data
    parts = msg.rstrip().split(" ")
    saved_data["id"] = parts[1]
    saved_data["session"] = parts[2]
    saved_data["list_exercises"] = parts[3:]
