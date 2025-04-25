from socket import *
from ui_functions import *
import sys
import select
import time
import curses
import json  # Added this import
import os
import time

def getLine(conn):
    msg = b''
    while True:
        ch = conn.recv(1)
        msg += ch
        if ch == b'\n' or len(ch) == 0:
            msg = msg[:-1]
            break
    return msg.decode()

serverIP = sys.argv[1]
serverPort = int(sys.argv[2])
serverSock = socket(AF_INET, SOCK_STREAM)
username = sys.argv[3]

def main(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    try:
        serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSock.connect((serverIP, serverPort))
        serverSock.sendall((username + "\n").encode())

        while True:
            try:
                msg = getLine(serverSock)
                if not msg:
                    break
                elif msg.startswith("REJECTED:"):
                    curses.endwin()
                    reason = msg.split(":", 1)[1]
                    print(f"Connection rejected: {reason}")
                    sys.exit(1)  # Exit the program after rejection
                elif msg[0:5] == "TABLE":
                    data = serverSock.recv(int(msg[6:])).decode()
                    table_json = json.loads(data)
                    table = {int(k): v for k, v in table_json.items()}
                    logging.debug(f"Received TABLE data: {table}")
                    draw_table(stdscr, table)
                elif msg == "DEAL":
                    pass
                elif msg == "PLAYER_ACTION":
                    pass
                elif msg == "REVEAL":
                    pass
            except OSError as e:
                curses.endwin()
                print(f"Error: {e}")
                print("Server has closed the connection or encountered an error.")
                break
    except Exception as e:
        curses.endwin()
        print(f"An unexpected error occurred: {e}")
    finally:
        serverSock.close()
        print("Socket closed. Exiting...")

if __name__ == "__main__":
    curses.wrapper(main)
