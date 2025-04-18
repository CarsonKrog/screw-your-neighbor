from socket import *
import threading
import sys
import select
import time

serverIP = sys.argv[1]
serverPort = int(sys.argv[2])
clientSock = socket(AF_INET, SOCK_STREAM)
username = sys.argv[3]

# receive data by '\n'
def recvByN(sock):
    data = b""
    while True:
        chunk = sock.recv(1)
        if not chunk or chunk == b"\n":
            break
        data += chunk
    return data.decode()


# Listen for messages from the server
def listenForMessages(sock):
    global running
    while True:
        try:
            msg = recvByN(sock)
            if not msg:
                print("Server Disconnected")
                running = False
                break
            print(msg, flush=True)
        except OSError:
            break  # Stop listening if socket is closed


# Connnect to the server
try:
    clientSock.connect((serverIP, serverPort))
    print("Connected.")

    # spawn new thread that listens for clients
    threading.Thread(target=listenForMessages, args=(clientSock,), daemon=True).start()
    running = True
    while running:
        try:
            # Check input with timeout. this way if running becomes false it can exit the program
            if sys.stdin in select.select([sys.stdin], [], [], 1)[0]:
                msg = input() + "\n"
                clientSock.send(msg.encode())
        except KeyboardInterrupt:
            print('\n[Shutting down]')
            break
except Exception as e:
    print(f"Error: {e}")
finally:
    clientSock.close()    # close socket
    sys.exit(0)
