import socket
import threading
import time
from flask_socketio import SocketIO
from app.models import db,Session
from app import app
from ipaddress import IPv4Network
import ipaddress
from netifaces import interfaces, ifaddresses, AF_INET
from socket import inet_aton, inet_ntoa

socketio = SocketIO(app,async_mode='threading')

@socketio.on('connected')
def connect():
    print('Page connected')


MESSAGE_PORT = 50069
BROADCAST_PORT = 50068
BEACON_MESSAGE = b"BEACON"
ACK_MESSAGE = b"ACK"
CONNECTED_MESSAGE = b"CONNECT"
client_ips = []
TIMEOUT_SECONDS = 5

CHECK_INTERVAL_SECONDS = 3600 # 60 MINUTES
CONNECTED = False
CONNECTED_CLIENT = None
last_connection_checked = None
connection_event = threading.Event()


def send_data(message_name, data):
    global CONNECTED_CLIENT
    try:
        msg = (message_name + " " + data).encode("utf-8")
        recv_socket.sendto(msg,CONNECTED_CLIENT)
        print("sending message:", message_name + " " + data)
    except Exception as e:
        print(e)


def is_connected():
    global CONNECTED
    return CONNECTED

def send_connect(client):
    global CONNECTED,CONNECTED_CLIENT,last_connection_checked
    try:
        recv_socket.sendto(b"CONNECT",client)
        msg, addr = recv_socket.recvfrom(1024**2)
        if msg == b"CONNECT_ACK" and addr == client:
            print(f'[CONNECT] to {client}')
            CONNECTED = True
            print("setting CONNECTED to TRUE")
            CONNECTED_CLIENT = client
            last_connection_checked = time.time() #GET CONNECTION RECEIVED TIME
            connection_event.set()
    except Exception as e:
        print(f"Failed connection to client: {e}")

# Maurizio-start
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        # print("***********", s.getsockname())
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
# Maurizio-end


def send_beacon_packets():
    broadip = inet_ntoa( inet_aton(get_local_ip())[:3] + b'\xff' )
    while True:
        if not CONNECTED:
            try:
                sock.sendto(BEACON_MESSAGE, (broadip, BROADCAST_PORT))
                print("[BEACON] sent beacon for discovery")
            except Exception as e:
                print(f"Failed to send beacon packet: {e}")

            time.sleep(1)

            # Receive ACK packets from clients and store their IP addresses
            try:
                data, addr = recv_socket.recvfrom(1024**2 )
                
                if data == ACK_MESSAGE:
                    print(f"[ACK] from {addr}")
                    client_ips.append(addr)

            except socket.timeout:
                pass

def main():
    global sock, CONNECTED,CONNECTED_CLIENT,last_connection_checked,client_ips,socketio
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("[SOCKET] started socket for broadcasting")
    # Enable broadcasting
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Set the TTL value to 4
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)

    # Create a UDP socket for receiving ACK packets
    global recv_socket
    recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_socket.bind(("", MESSAGE_PORT))
    print("[SOCKET] started socket for communication")
    # Set a timeout for receiving ACK packets
    recv_socket.settimeout(TIMEOUT_SECONDS)

    # Spawn a thread to send beacon packets for the specified duration
    beacon_thread = threading.Thread(target=send_beacon_packets)
    beacon_thread.start()


    #Waits for a connection
    connection_event.wait()

    #Check messages, connections and send SOCKETIO notifications (all pages socket?)
    while(CONNECTED):
        try:
            msg,addr = recv_socket.recvfrom(1024**2)

            if addr == CONNECTED_CLIENT:
                if msg == CONNECTED_MESSAGE:
                    last_connection_checked = time.time()

                # Maurizio-start:
                elif msg.decode().startswith("FINISHED_EXERCISE "):
                    print("***** received finished_exercise")
                    msg = msg.decode()
                    tokens = msg.split(" ")
                    number = int(tokens[1])
                    id = int(tokens[2])
                    result = tokens[3]
                # Maurizio-end
                    print(tokens)
                    with app.app_context():
                        session = Session.query.filter_by(user_id=id, exercise=number).order_by(Session.number.desc()).first()
                        if session:
                            # session.result = result
                            
                            db.session.commit()
                            socketio.emit("exercise",number)
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
            