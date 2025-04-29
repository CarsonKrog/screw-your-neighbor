from socket import *
import threading
import sys
import time
import random
import json
import traceback

class PlayerDisconnect(Exception):
    pass

class GameState:
    def __init__(self):
        self.table = {}            # seat -> [username, lives, isDealer]
        self.playerConnections = {} # seat -> socket
        self.playerCount = 0
        self.gameRunning = False
        self.startGameThreadRunning = False
        self.cancelCountdown = False
        self.lock = threading.Lock()
        self.dealer = None

def create_list_string(data):
    # Flatten the list if it contains sublists
    flattened_data = []
    for item in data:
        if isinstance(item, list):  # Check if the item is a list
            flattened_data.extend(item)  # Add the sublist elements to the flattened list
        else:
            flattened_data.append(item)  # Otherwise, add the item itself

    # Now join the flattened list
    return ",".join(map(str, flattened_data))

def create_shuffled_deck():
    values = ['A'] + [str(n) for n in range(2, 11)] + ['J', 'Q', 'K']
    suits = ['♠', '♥', '♦', '♣']
    deck = [f"{value}{suit}" for suit in suits for value in values]
    random.shuffle(deck)
    return deck

def get_losing_seats(table):
    rank_order = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                  '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13}

    seat_ranks = {}
    for seat, card in table.items():
        if len(card) > 1:
            rank = card[1][:-1]  # Remove suit
        else:
            rank = card[0][:-1]  # Remove suit
        seat_ranks[seat] = rank_order[rank]

    min_rank = min(seat_ranks.values())

    losing_seats = [seat for seat, rank in seat_ranks.items() if rank == min_rank]

    return losing_seats

def getLine(conn):
    msg = b''
    while True:
        ch = conn.recv(1)
        if not ch:
            break
        msg += ch
        if ch == b'\n':
            break
    return msg.decode()[:-1]

def addPlayer(state, username):
    if state.playerCount == 0:
        state.table[0] = [username, 4, True]  # Seat 0 is dealer
        state.playerCount += 1
        return 0
    else:
        for i in range(6):
            if i not in state.table:
                state.table[i] = [username, 4, False]
                state.playerCount += 1
                return i

def broadcast(state, data):
    for seat, conn in state.playerConnections.items():
        try:
            if type(data) == str:
                conn.sendall(data.encode())
            else:
                conn.sendall(data)
        except (BrokenPipeError, ConnectionResetError):
            break


def listenForPlayers(state, listenerSocket):
    while running:
        try:
            clientConn, clientAddr = listenerSocket.accept()
            threading.Thread(target=handlePlayer, args=(state, (clientConn, clientAddr)), daemon=True).start()
        except Exception as e:
            print(f"Accept failed: {e}")
            sys.exit(1)

def handlePlayer(state, connInfo):
    clientConn, clientAddr = connInfo
    print(f"Received connection from {clientAddr[0]}:{clientAddr[1]}")
    username = getLine(clientConn)

    with state.lock:
        if state.gameRunning:
            print("REJECTED CONNECTION: GAME_RUNNING")
            clientConn.sendall("REJECTED:GAME_RUNNING\n".encode())
            clientConn.close()
            return
        elif state.playerCount >= 6:
            print("REJECTED CONNECTION: TABLE_FULL")
            clientConn.sendall("REJECTED:TABLE_FULL\n".encode())
            clientConn.close()
            return

        seat = addPlayer(state, username)
        state.playerConnections[seat] = clientConn
        
        if state.dealer is None:
            state.dealer = seat

        print("Current table:", state.table)

        table_json = json.dumps(state.table).encode()
        broadcast(state, f"TABLE:{len(table_json)}\n")
        time.sleep(0.1)
        broadcast(state, table_json)

def handleDisconnect(state):
    with state.lock:
        disconnected_seats = []
        
        # Identify disconnected players
        for seat, conn in list(state.playerConnections.items()):
            try:
                # Check if connection is still alive
                conn.send(b"PING\n")
            except (BrokenPipeError, ConnectionResetError):
                disconnected_seats.append(seat)
        
        for seat in disconnected_seats:
            username = state.table[seat][0]
            print(f"Player {username} disconnected from seat {seat}")
            
            try:
                state.playerConnections[seat].close()
            except:
                pass
            
            # Remove from connections and table
            del state.playerConnections[seat]
            del state.table[seat]
            state.playerCount -= 1
            
        if state.gameRunning:
            state.gameRunning = False
        elif state.startGameThreadRunning:
            state.startGameThreadRunning = False
            state.cancelCountdown = True

def startGame(state):
    if not state.cancelCountdown:
        with state.lock:
            state.gameRunning = True
            state.startGameThreadRunning = False
        print("GAME STARTED")
    else:
        state.cancelCountdown = False

def get_player_action(conn, card):
    conn.sendall(f"DECISION:{card}\n".encode())
    decision = getLine(conn)
    return decision

def new_dealer(state):
    if state.dealer in state.table:
        state.table[state.dealer][2] = False
    new_dealer = (state.dealer + 1) % 6
    while True:
        if new_dealer in state.table and state.table[new_dealer][1] > 0:
            state.dealer = new_dealer
            state.table[state.dealer][2] = True
            break
        else:
            new_dealer = (new_dealer + 1) % 6

def players_left(state):
    alive = sum(1 for seat in state.table.values() if seat[1] > 0)
    
    # more than 1 player
    if alive > 1:
        return 1
    # only 1 player left
    elif alive == 1:
        return 0
    # no players left: means a tie where all players had 1 life left. so no one should lose a life
    else:
        return -1

def generate_flip_order(state):
    dealer_seat = state.dealer
    flip_order = []
    
    for i in range(6):
        seat = (dealer_seat + 1 + i) % 6
        if seat in state.table and state.table[seat][1] > 0:
            flip_order.append(seat)
    
    return flip_order

def reset_lives(state):
    for seat, data in state.table.items():
        data[1] = 4
    new_dealer(state)

def play_round(state, deck, order, flip_order):
    table = {}
    flip_order_string = create_list_string(flip_order)

    # Deal cards out
    for seat in order:
        conn = state.playerConnections[seat]
        if seat in flip_order:
            card = deck.pop()
            table[seat] = [card]
            conn.sendall(f"DEAL:{flip_order_string}:{card}\n".encode())
        else:
            conn.sendall(f"DEAL:{flip_order_string}:NONE\n".encode())

    print(table)

    time.sleep(1)

    # Ask first player for decision
    first_seat = flip_order[0]

    if table[first_seat][0][:-1] == "K":
        broadcast(state, f"FLIP_CARD:{first_seat}:{table[first_seat][0]}\n")
    else:
        conn = state.playerConnections[first_seat]
        decision = get_player_action(conn, table[first_seat][0])
        if decision == "switch":
            # switch cards in table
            next_seat = flip_order[1]

            if table[next_seat][0][:-1] != "K":
                temp = table[first_seat]
                table[first_seat] = table[next_seat]
                table[next_seat] = temp
                # send player new card
                conn.sendall(f"NEW_CARD:{table[first_seat][0]}\n".encode())
                time.sleep(0.1)

        # broadcast decision
        broadcast(state, f"PLAYER_ACTION:{first_seat}:{decision}\n")

    time.sleep(1)

    # Ask remaining players for decision
    if flip_order[1:-1]:
        for seat in flip_order[1:-1]:
            if table[seat][0][0] == "K":
                broadcast(state, f"FLIP_CARD:{seat}:{table[seat][0]}\n")
            else:
                conn = state.playerConnections[seat]
                decision = get_player_action(conn, table[seat][0])
                if decision == "switch":
                    # switch cards in table
                    next_seat = (seat + 1) % 6
                    while next_seat not in flip_order:
                        next_seat = (next_seat + 1) % 6

                    if table[next_seat][0][0] != "K":
                        temp = table[seat]
                        table[seat] = table[next_seat]
                        table[next_seat] = temp
                        # send player new card
                        conn.sendall(f"NEW_CARD:{table[seat][0]}\n".encode())
                        time.sleep(0.1)

                # broadcast decision
                broadcast(state, f"PLAYER_ACTION:{seat}:{decision}\n")
            time.sleep(1)

        # Ask Dealer 
        seat = flip_order[-1]

        if table[seat][0][0] == "K":
            broadcast(state, f"FLIP_CARD:{seat}:{table[seat][0]}\n")
        else:
            conn = state.playerConnections[seat]
            decision = get_player_action(conn, table[seat][0])
            if decision == "switch":
                # Give dealer card from the deck
                table[seat].append(deck.pop())
                # send player new card
                conn.sendall(f"NEW_CARD:{table[seat][0]}\n".encode())
                time.sleep(0.1)

                # broadcast decision
            broadcast(state, f"PLAYER_ACTION:{seat}:{decision}\n")
        time.sleep(1)
    else:
        # only 2 players so this player is the dealer
        seat = flip_order[1]

        if table[seat][0][0] == "K":
            broadcast(state, f"FLIP_CARD:{seat}:{table[seat][0]}\n")
        else:
            conn = state.playerConnections[seat]
            decision = get_player_action(conn, table[seat][0])
            if decision == "switch":
                # Give dealer card from the deck
                table[seat].append(deck.pop())
                # send player new card
                conn.sendall(f"NEW_CARD:{table[seat][0]}\n".encode())
                # broadcast decision
                time.sleep(0.1)
            
            # broadcast decision
            broadcast(state, f"PLAYER_ACTION:{seat}:{decision}\n")

        
    time.sleep(1)

    print(table)    
    reveal_json = json.dumps(table).encode()
    broadcast(state, f"REVEAL:{len(reveal_json)}:{flip_order_string}\n")
    time.sleep(0.5)
    broadcast(state, reveal_json)

    time.sleep(3)

    losing_seats = get_losing_seats(table)
    losing_usernames = []
    losing_cards = []
    for seat in losing_seats:
        losing_usernames.append(state.table[seat][0])
        if len(table[seat]) > 1:
            losing_cards.append(table[seat][1])
        else:
            losing_cards.append(table[seat][0])
        lives = state.table[seat][1]
        state.table[seat][1] = lives - 1

    time.sleep(3)

    broadcast(state, f"LOSERS:{create_list_string(losing_usernames)}:{create_list_string(losing_cards)}\n")

    time.sleep(3)

    round_result = players_left(state)
    
    if round_result == 1: # more than 1 player left
        return 1
    elif round_result == 0: # only 1 player left
        return 0
    else: # players with 1 life left tied: therefore they don't lose a life and the game continues
        for seat in losing_seats:
            lives = state.table[seat][1]
            state.table[seat][1] = lives + 1
        return -1

def runGame(state):
    game_over = False

    print("TABLE", state.table)

    table_json = json.dumps(state.table).encode()
    broadcast(state, f"TABLE:{len(table_json)}\n")
    time.sleep(0.1)
    broadcast(state, table_json)

    order = generate_flip_order(state)

    deck = create_shuffled_deck()
    print(deck)
    while not game_over:
        print(f"deck size {len(deck)}")
        if state.table[state.dealer][1] == 0:
            new_dealer(state)

            if len(deck) < (state.playerCount + 1):
                print("NEW DECK")
                deck = create_shuffled_deck()

            table_json = json.dumps(state.table).encode()
            broadcast(state, f"TABLE:{len(table_json)}\n")
            time.sleep(0.1)
            broadcast(state, table_json)
            time.sleep(2)

        elif len(deck) < (state.playerCount + 1):
            deck = create_shuffled_deck()
            print("NEW DECK")
            new_dealer(state)

            table_json = json.dumps(state.table).encode()
            broadcast(state, f"TABLE:{len(table_json)}\n")
            time.sleep(0.1)
            broadcast(state, table_json)
            time.sleep(2)

        flip_order = generate_flip_order(state)
        result = play_round(state, deck, order, flip_order)

        if result == 0:
            game_over = True
            state.gameRunning = False
            winner = state.table[generate_flip_order(state)[0]][0]
            return winner
        else:
            table_json = json.dumps(state.table).encode()
            broadcast(state, f"TABLE:{len(table_json)}\n")
            time.sleep(0.1)
            broadcast(state, table_json)
            time.sleep(2)

port = int(sys.argv[1])

listener = socket(AF_INET, SOCK_STREAM)
listener.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
listener.bind(('', port))
listener.listen(32)

state = GameState()
running = True

startTime = 0.0

# Start listening for players
threading.Thread(target=listenForPlayers, args=(state, listener), daemon=True).start()

INBETWEEN_ROUND_TIME = 30

try:
    while running:
        try:
            if state.gameRunning:
                winner = runGame(state)
                print("Game over")
                # broadcast table message of who won

                table_json = json.dumps(state.table).encode()
                broadcast(state, f"TABLE:{len(table_json)}\n")
                time.sleep(0.1)
                broadcast(state, table_json)
                time.sleep(0.1)
                broadcast(state, f"WAITING:Gamer Over - {winner} wins\n")
                time.sleep(3)

                # reset table state 
                reset_lives(state)
                #new_dealer()
                
                # send new table info
                table_json = json.dumps(state.table).encode()
                broadcast(state, f"TABLE:{len(table_json)}\n")
                time.sleep(0.1)
                broadcast(state, table_json)
                with state.lock:
                    state.gameRunning = False
            elif state.playerCount > 1 and not state.startGameThreadRunning:
                with state.lock:
                    state.startGameThreadRunning = True
                    threading.Timer(INBETWEEN_ROUND_TIME, startGame, args=(state,)).start()
                startTime = time.time()
                #broadcast(state, f"WAITING:Game will begin in %0.0f\n" %(INBETWEEN_ROUND_TIME - (time.time() - startTime)))
                broadcast(state, f"WAITING:Game will begin in {int(INBETWEEN_ROUND_TIME - (time.time() - startTime)):02}\n")
                print("Game will begin in %0.0f seconds\n" %(INBETWEEN_ROUND_TIME - (time.time() - startTime)))
            elif state.startGameThreadRunning and not state.cancelCountdown:
                broadcast(state, f"WAITING:Game will begin in {int(INBETWEEN_ROUND_TIME - (time.time() - startTime)):02}\n")
            elif state.playerCount == 1:
                broadcast(state, f"WAITING:Waiting for more players to join\n")
            time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            handleDisconnect(state)
            reset_lives(state)
            print("Current table:", state.table)
            # Notify remaining players
            print(f"player count {state.playerCount}")
            if state.playerCount > 0:
                table_json = json.dumps(state.table).encode()
                broadcast(state, f"TABLE:{len(table_json)}\n")
                time.sleep(0.1)
                broadcast(state, table_json)
            time.sleep(1)
            broadcast(state, f"WAITING:Player disconnected - ended game\n")
            time.sleep(3)
except KeyboardInterrupt:
    print("\n[Shutting down]")
    running = False
except Exception as e:
    traceback.print_exc()
finally:
    listener.close()
    for conn in state.playerConnections.values():
        conn.close()
