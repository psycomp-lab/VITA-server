import socket
import threading
import time
from flask_socketio import SocketIO
from app.models import db, Session
from app import app
from socket import inet_aton, inet_ntoa

socketio = SocketIO(app, async_mode='threading')

@socketio.on('Continue')
def handle_continue():
    print('Avvisa visore continua')

@socketio.on('Pause')
def handle_pause():
    print('Avvisa visore pausa')

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
                print("[DATA] sent data to client")
                save_data(msg)
                connection_event.set()
                break
        except Exception as e:
            print(f"Failed to send data to client: {e}")

def is_connected():
    return CONNECTED

# Get the local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception as e:
        print(f"Failed to get local ip: {e}")
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Send a connect message to the client
def send_connect(client):
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked
    try:
        recv_socket.sendto(CONNECT_MESSAGE, client)
        msg, addr = recv_socket.recvfrom(1024 ** 2)
        if msg == CONNECT_ACK and addr == client:
            print("[CONNECT] connected to client")
            CONNECTED = True
            CONNECTED_CLIENT = client
            last_connection_checked = time.time()  # Get the time connection was received
    except Exception as e:
        print(f"Failed connection to client: {e}")

# Send beacon packets for client discovery
def send_beacon_packets():
    broadip = inet_ntoa(inet_aton(get_local_ip())[:3] + b'\xff')
    while True:
        if not CONNECTED:
            try:
                sock.sendto(BEACON_MESSAGE, ("127.0.0.1", BROADCAST_PORT))
                print("[BEACON] sent beacon for discovery")
            except Exception as e:
                print(f"Failed to send beacon packet: {e}")

            # Receive ACK packets from clients and store their IP addresses
            try:
                data, addr = recv_socket.recvfrom(1024 ** 2)
                if data == BEACON_ACK:
                    print("[ACK] received a discovery ack from client")
                    if addr not in client_ips:
                        client_ips.append(addr)
            except socket.timeout:
                pass

# Main function to manage connections and data
def main():
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked

    # Set the TTL value to 20 for broadcasting
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)

    # Create a UDP socket for receiving ACK packets
    recv_socket.bind(("", MESSAGE_PORT))
    print("[SOCKET] started socket for communication")

    # Set a timeout for receiving ACK packets
    recv_socket.settimeout(TIMEOUT_SECONDS)

    # Spawn a thread to send beacon packets
    beacon_thread = threading.Thread(target=send_beacon_packets)
    beacon_thread.start()

    # Wait for a connection
    connection_event.wait()

    index = 0
    time.sleep(5)
    # Check messages, connections and send SOCKETIO notifications
    while CONNECTED:
        if index >= len(saved_data["list_exercises"]):
            CONNECTED = False
            CONNECTED_CLIENT = None
            socketio.emit("end_session")
            break

        msg = "WAITING "+ saved_data["list_exercises"][index] +" "+ saved_data["id"]+" "+saved_data["session"]
        try:
            recv_socket.sendto(msg.encode("utf-8"), CONNECTED_CLIENT)
            msg, addr = recv_socket.recvfrom(1024 ** 2)

            if addr == CONNECTED_CLIENT:
                last_connection_checked = time.time()

                if msg.decode().startswith("FINISHED_EXERCISE "):
                    #CONTROLLO SUL MESSAGGIO
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
                else:
                    print(msg.decode())
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error while checking connection: {e}")

        # Check if the connection has timed out
        if time.time() - last_connection_checked > CHECK_INTERVAL_SECONDS:
            CONNECTED = False
            CONNECTED_CLIENT = None
            socketio.emit("disconnect-vr")

# Save the received data
def save_data(msg: str):
    global saved_data
    parts = msg.rstrip().split(" ")
    saved_data["id"] = parts[1]
    saved_data["session"] = parts[2]
    list_exercises = []
    for n in range(3, len(parts)):
        list_exercises.append(parts[n])
    saved_data["list_exercises"] = list_exercises
