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
IN_SESSION = False

saved_data = {}
client_ips = []
DATA = None
CONNECTED = False
CONNECTED_CLIENT = None
last_connection_checked = None

TIMEOUT_SECONDS = 5
CHECK_INTERVAL_SECONDS = 120
connection_event = threading.Event()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def get_data():
    return saved_data

def get_clients():
    return client_ips

def disconnect():
    global CONNECTED_CLIENT,CONNECTED,DATA,last_connection_checked,client_ips,saved_data
    CONNECTED = False
    CONNECTED_CLIENT = None
    DATA = None
    last_connection_checked = None
    client_ips = []
    saved_data.clear()
    connection_event.clear()

def send_data():
    global CONNECTED,CONNECTED_CLIENT,DATA,IN_SESSION
    DATA = "SESSION "+saved_data["id"]+" "+str(saved_data["session"])+" "
    for ex in saved_data["list_exercises"]:
        DATA += str(ex) + " "
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            recv_socket.sendto(DATA.encode("utf-8"), CONNECTED_CLIENT)
            resp, addr = recv_socket.recvfrom(1024 ** 2)
            if addr == CONNECTED_CLIENT and resp == DATA_ACK:
                connection_event.set()
                IN_SESSION = True
                return True
        except OSError as e:
            retries += 1
            if e.errno == 10054:
                print("****Error the headset was forcefully disconnected")
                disconnect()
                socketio.emit("disconnect-vr")
    return False       


def is_connected():
    return CONNECTED


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception as e:
        print(f"****Failed to get local ip: {e}")
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
            print("[CONNECT_ACK] connected to client")
            CONNECTED = True
            CONNECTED_CLIENT = client
            last_connection_checked = time.time()
    except Exception as e:
        print(f"****Failed connection to client: {e}")

def send_beacon_packets():
    global client_ips
    broadip = inet_ntoa(inet_aton(get_local_ip())[:3] + b'\xff')
    while True:
        if not CONNECTED:
            try:
                sock.sendto(BEACON_MESSAGE, ("127.0.0.1", BROADCAST_PORT))
                print(f"[BEACON] sent beacon for discovery: {broadip}")
            except Exception as e:
                print(f"****Failed to send beacon packet: {e}")
            try:
                data, addr = recv_socket.recvfrom(1024 ** 2)
                if data == BEACON_ACK:
                    print("[BEACON_ACK] received a discovery ack from client")
                    if addr not in client_ips:
                        client_ips.append(addr)
            except socket.timeout:
                pass
        else:
            if not IN_SESSION:
                check = False
                for _ in range(3):
                    try:
                        if CONNECTED_CLIENT:
                            recv_socket.sendto(CONNECT_MESSAGE,CONNECTED_CLIENT)
                        else:
                            break
                        msg,addr = recv_socket.recvfrom(1024 ** 2)
                        if msg == CONNECT_ACK:
                            check = True
                            print("****Headset is still connected")
                            break
                    except socket.timeout:
                        pass
                    except OSError as e:
                        if e.errno == 10054:
                            print("****Error the headset was forcefully disconnected")
                            disconnect()
                            socketio.emit("disconnect-vr")
                if not check:
                    print("****Lost connection with headset")
                    disconnect()
                    socketio.emit("disconnect-vr")
                
                time.sleep(30)
                    
                
                    
def main():
    global CONNECTED, CONNECTED_CLIENT, last_connection_checked, RESTART, PAUSE, IN_SESSION

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)

    recv_socket.bind(("", MESSAGE_PORT))
    print("[SOCKET] started socket for communication")
    recv_socket.settimeout(TIMEOUT_SECONDS)

    beacon_thread = threading.Thread(target=send_beacon_packets)
    beacon_thread.start()

    while True:
        connection_event.wait()

        index = 0
        time.sleep(5)

        while CONNECTED:
            if index >= len(saved_data.get("list_exercises", [])):
                IN_SESSION = False
                disconnect()
                socketio.emit("end_session")
                break
            req = str(saved_data.get("list_exercises", [])[index])
            if PAUSE:
                msg = "PAUSE"
            elif RESTART:
                msg = "RESTART"
            else:
                msg = "WAITING "+ req
            try:
                recv_socket.sendto(msg.encode("utf-8"), CONNECTED_CLIENT)
                print(f"****Sent {msg}")
                msg, addr = recv_socket.recvfrom(1024 ** 2)

                if addr == CONNECTED_CLIENT:
                    last_connection_checked = time.time()

                    if msg.decode().startswith("FINISHED_EXERCISE "):
                        msg = msg.decode()
                        tokens = msg.split(" ")
                        number = int(tokens[1])
                        id = tokens[2]
                        result = tokens[3].encode("utf-8")

                        if number == int(req):
                            index += 1
                            with app.app_context():
                                session = Session.query.filter_by(user_id=id, exercise=number).order_by(Session.number.desc()).first()
                                if session:
                                    session.result = result
                                    db.session.commit()
                                    socketio.emit("exercise", number)
                                    print(f"****Updated session {number} for user {id} with result: {result}")
                                else:
                                    print(f"****No session found for user {id} with number {number}")

                    elif msg == RESTART_ACK:
                        RESTART = False
                        print("[RESTART_ACK] received")
                    elif msg == PAUSE_ACK:
                        PAUSE = False
                        print("[PAUSE_ACK] received")
                    elif msg.decode().startswith("DOING"):
                        print(f"****Received {msg.decode()}")
                        parts = msg.decode().split(" ")
                        ex = parts[1]
                        if ex != req:
                            with app.app_context():
                                index += 1
                                session = Session.query.filter_by(user_id=saved_data.get("id"), exercise=req).order_by(Session.number.desc()).first()
                                if session:
                                    session.result = b"NON REGISTRATO"
                                    db.session.commit()
                                    socketio.emit("exercise", req)
                                    print(f"****Result for exercise {req} not registered")
                    elif msg == b"END_SESSION":
                        disconnect()
                        print("****This is the end session. Closing the socket")
                        socketio.emit("end_session")
                    else:
                        print(f"****Received {msg.decode()}")
            
            except socket.timeout:
                pass
            except OSError as e:
                if e.errno == 10054:
                    print("[ERROR] the headset was forcefully disconnected")
                    disconnect()
                    socketio.emit("disconnect-vr")
                    break
            except Exception as e:
                print(f"****Error while checking connection: {e}")

            time.sleep(10)

            if time.time() - last_connection_checked > CHECK_INTERVAL_SECONDS:
                IN_SESSION = False
                disconnect()
                socketio.emit("disconnect-vr")

def save_data(id:str,session:str,list_exercises:list):
    global saved_data
    saved_data["id"] = id
    saved_data["session"] = session
    saved_data["list_exercises"] = list_exercises
   