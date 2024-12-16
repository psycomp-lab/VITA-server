import threading
from app import app
from app.socket_udp import main,socketio
from app import routes  # noqa: F401






def run_flask():
    socketio.run(app,port=5000)

if __name__ == "__main__":
    thread_app = threading.Thread(target=run_flask)
    thread_app.start()
    main()
