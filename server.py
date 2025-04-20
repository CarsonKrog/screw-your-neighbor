from socket import *
import threading
import sys
import time

# Fully fetches new-line '\n' terminated string from the specified socket `conn'
def getLine(conn):
    msg = b''
    while True:
        ch = conn.recv(1)
        msg += ch
        if ch == b'\n' or len(ch) == 0:
            break
    return msg.decode()

# Invoked each time a client makes a new connection to the server
def handleClient(connInfo):
    clientConn, clientAddr = connInfo  # a pair of (socket, clientAddr) from accept()
    clientIP = clientAddr[0]
    print("Received connection from %s:%d" %(clientIP, clientAddr[1]))

    clientConn.close()

port = int(sys.argv[1])

# Set up listening sockepo
listener = socket(AF_INET, SOCK_STREAM)
listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listener.bind(('', port))
listener.listen(32)  # Support up to 32 simultaneous connections

running = True
while running:
    try:
        threading.Thread(target=handleClient, args=(listener.accept(),), daemon=True).start()
    except KeyboardInterrupt:
        print('\n[Shutting down]')
        running = False
