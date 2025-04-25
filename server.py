from socket import *
import threading
import sys
import time
import random
import json

def create_shuffled_deck():
    values = ['A'] + [str(n) for n in range(2, 11)] + ['J', 'Q', 'K']
    suits = ['♠', '♥', '♦', '♣']
    deck = [f"{value}{suit}" for suit in suits for value in values]
    random.shuffle(deck)
    return deck

# Fully fetches new-line '\n' terminated string from the specified socket `conn'
def getLine(conn):
    msg = b''
    while True:
        ch = conn.recv(1)
        msg += ch
        if ch == b'\n' or len(ch) == 0:
            break
    return msg.decode()[:-1]

def addPlayer(username):
    global table, playerCount
    
    if playerCount == 0:
        table[0] = [username, 4, True]
        playerCount += 1
        return 0
    else:
        for i in range(5):
            if i not in table:
                table[i] = [username, 4, False]
                playerCount += 1
                return i

def broadcast(controlMsg, data):
    for seat, socket in playerConnections.items():
        socket.sendall(controlMsg.encode())
        if type(data) == str:
            socket.sendall(data.encode())
        else:
            socket.sendall(data)

def listenForPlayers(socket):
    while True:
        threading.Thread(target=handlePlayer, args=(socket.accept(),), daemon=True).start()

def handlePlayer(connInfo):
    global gameRunning
    clientConn, clientAddr = connInfo
    clientIP = clientAddr[0]
    print("Received connection from %s:%d" % (clientIP, clientAddr[1]))
    username = getLine(clientConn)

    with tableLock:
        if gameRunning:
            print("REJECTED CONNECTION: GAME_RUNNING")
            clientConn.sendall("REJECTED:GAME_RUNNING\n".encode())
            clientConn.close()
            return
        elif playerCount >= 6:
            print("REJECTED CONNECTION: TABLE_FULL")
            clientConn.sendall("REJECTED:TABLE_FULL\n".encode())
            clientConn.close()
            return

        seat = addPlayer(username)
        playerConnections[seat] = clientConn

    print(table)
    
    table_json = json.dumps(table).encode()
    sizeOfData = sys.getsizeof(table_json)
    broadcast(f"TABLE:{sizeOfData}\n", table_json)

def handleDisconnect():
    # if someone quits nuke the game
    pass

def startGame():
    global gameRunning
    gameRunning = True
    print("GAME STARTED")

def runGame():
    pass

port = int(sys.argv[1])

# Set up listening sockepo
listener = socket(AF_INET, SOCK_STREAM)
listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listener.bind(('', port))
listener.listen(32)  # Support up to 32 simultaneous connections
#listener.settimeout(1)  # 1 second timeout for accept()

tableLock = threading.Lock()
table = {} # {seat: [username, lives, isDealer]}
playerConnections = {} # {seat: socket}
playerCount = 0
gameRunning = False
startGameThreadRunning = False

INBETWEEN_ROUND_TIME = 10

running = True

# spawn thread to listen for new player connections
threading.Thread(target=listenForPlayers, args=(listener,), daemon=True).start()

while running:
    try:
        if gameRunning:
            runGame()
        elif playerCount > 1 and not startGameThreadRunning:
            threading.Timer(INBETWEEN_ROUND_TIME, startGame).start()
            print(f"Game will begin in {INBETWEEN_ROUND_TIME} seconds...")
            startGameThreadRunning = True
    except KeyboardInterrupt:
        print('\n[Shutting down]')
        running = False
