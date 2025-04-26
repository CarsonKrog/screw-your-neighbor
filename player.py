from socket import *
from ui_functions import *
import sys
import select
import time
import curses
import json
import os
import traceback

def parse_list(message):
    return [int(x) for x in message.split(",")]

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

def recvAll(sock, size):
    data = b''
    while len(data) < size:
        more = sock.recv(size - len(data))
        if not more:
            raise EOFError('Socket closed before receiving full data')
        data += more
    return data

serverIP = sys.argv[1]
serverPort = int(sys.argv[2])
username = sys.argv[3]

def main(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    serverSock = socket(AF_INET, SOCK_STREAM)
    try:
        serverSock.connect((serverIP, serverPort))
        serverSock.sendall((username + "\n").encode())

        while True:
            try:
                msg = getLine(serverSock)
                if not msg:
                    break

                if msg[0:8] == "REJECTED":
                    curses.endwin()
                    reason = msg[9:]
                    print(f"Connection rejected: {reason}")
                    break

                elif msg[0:7] == "WAITING":
                    message = msg[8:]
                    table_message(stdscr, message)

                elif msg[0:5] == "TABLE":
                    dataSize = int(msg[6:])
                    data = serverSock.recv(dataSize).decode()
                    table_json = json.loads(data)
                    table = {int(k): v for k, v in table_json.items()}
                    draw_table(stdscr, table)

                elif msg[0:4] == "DEAL":
                    _, str_flip_order, player_card = msg.split(":")
                    flip_order = parse_list(str_flip_order)
                    deal(stdscr, flip_order, player_card)

                elif msg[0:13] == "PLAYER_ACTION":
                    seat = int(msg[14:15])
                    action = msg[16:]
                    player_action(stdscr, seat, action)

                elif msg[0:8] == "DECISION":
                    card = msg[9:]
                    decision = decision_card(stdscr, card)
                    serverSock.sendall(decision.encode())

                elif msg[0:6] == "REVEAL":
                    _, strSize, strFlipOrder = msg.split(":")
                    flip_order = parse_list(strFlipOrder)
                    dataSize = int(strSize)
                    data = serverSock.recv(dataSize).decode()
                    data_json = json.loads(data)
                    player_cards = {int(k): v for k, v in data_json.items()}
                    reveal_cards(stdscr, flip_order, player_cards)

                elif msg[0:6] == "LOSERS":
                    _, strUsernames, strCards = msg.split(":")
                    usernames = strUsernames.split(",")
                    cards = strCards.split(",")
                    losers(stdscr, usernames, cards)

            except OSError as e:
                curses.endwin()
                print(f"Error: {e}")
                break
            except Exception as e:
                print(f"Unexpected error while processing message: {e}")
                traceback.print_exc()
    except Exception as e:
        curses.endwin()
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    curses.wrapper(main)
