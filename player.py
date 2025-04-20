from socket import *
from ui_functions import *
import sys
import select
import time
import curses

# receive data by '\n'
def recvByN(sock):
    data = b""
    while True:
        chunk = sock.recv(1)
        if not chunk or chunk == b"\n":
            break
        data += chunk
    return data.decode()

serverIP = sys.argv[1]
serverPort = int(sys.argv[2])
clientSock = socket(AF_INET, SOCK_STREAM)
username = sys.argv[3]

# Connnect to the server
try:
    clientSock.connect((serverIP, serverPort))
    print("Connected.")
except Exception as e:
    print(f"Error: {e}")
finally:
    clientSock.close()    # close socket
