import curses
import time

CARD_DELAY = 0.5


BOX_HEIGHT = 10
BOX_WIDTH = 60

def flush_input_curses(stdscr):
    stdscr.nodelay(True)
    while stdscr.getch() != -1:
        pass
    stdscr.nodelay(False)

def get_player_positions(stdscr):
    max_y, max_x = stdscr.getmaxyx()
    box_top = (max_y - BOX_HEIGHT) // 2
    box_left = (max_x - BOX_WIDTH) // 2
    center_x = box_left + BOX_WIDTH // 2
    center_y = box_top + BOX_HEIGHT // 2

    spacing_x = 20
    spacing_y = 8

    return {
        0: (center_y-3, box_left - 16),                        # Far left
        1: (box_top - spacing_y, center_x - spacing_x),        # Top-left
        2: (box_top - spacing_y, center_x + spacing_x),        # Top-right
        3: (center_y-3, box_left + BOX_WIDTH + 16),            # Far right
        4: (box_top + BOX_HEIGHT + 2, center_x + spacing_x),   # Bottom-right
        5: (box_top + BOX_HEIGHT + 2, center_x - spacing_x),   # Bottom-left
    }

def draw_card(value=None, suit=None):
    if value is None or suit is None:
        card = [
            " _____",
            "|     |",
            "|     |",
            "|     |",
            "|_____|"
        ]
    else:
        val_str = f"{value:<2}"
        card = [
            " _____",
            f"|{val_str}   |",
            f"|  {suit}  |",
            "|     |",
            "|_____|"
        ]
    return card

def flip_card(stdscr, y, x_center, value, suit):
    frames = [
        [
            " _____",
            "|     |",
            "|     |",
            "|     |",
            "|_____|"
        ],
        [
            "   | |",
            "   | |",
            "   | |",
            "   | |",
            "   |_|"
        ],
        draw_card(value, suit)
    ]
    for frame in frames:
        for i, line in enumerate(frame):
            stdscr.addstr(y + i, x_center - len(line) // 2, line)
        stdscr.refresh()
        time.sleep(0.1)

def flip_card_at_position(stdscr, seat_index, card_str):
    positions = get_player_positions(stdscr)

    y, x = positions[seat_index]

    value = card_str[:-1]
    suit = card_str[-1]

    flip_card(stdscr, y + 1, x, value, suit)
    #stdscr.refresh()

def draw_center_box(stdscr):
    max_y, max_x = stdscr.getmaxyx()
    top = (max_y - BOX_HEIGHT) // 2
    left = (max_x - BOX_WIDTH) // 2
    for i in range(BOX_HEIGHT):
        if i == 0 or i == BOX_HEIGHT - 1:
            stdscr.addstr(top + i, left, "+" + "-" * (BOX_WIDTH - 2) + "+")
        else:
            stdscr.addstr(top + i, left, "|" + " " * (BOX_WIDTH - 2) + "|")

def draw_player_label(stdscr, y, x_center, name, lives, isDealer):
    label = f"{name} [ {lives} ]"
    if isDealer:
        stdscr.addstr(y, x_center - len(label) // 2, label, curses.A_UNDERLINE)
    else:
        stdscr.addstr(y, x_center - len(label) // 2, label)

def draw_blank_card(stdscr, y, x_center):
    card = draw_card()
    for i, line in enumerate(card):
        stdscr.addstr(y + i, x_center - len(line) // 2, line)

def deal(stdscr, flip_order, card):
    positions = get_player_positions(stdscr)
    for key in flip_order:
        y, x = positions[key]
        draw_blank_card(stdscr, y + 1, x)
        stdscr.refresh()
        time.sleep(CARD_DELAY)

    if card == "NONE":
        return

    value = card[:-1]
    suit = card[-1]

    max_y, max_x = stdscr.getmaxyx()
    card_lines = draw_card(value, suit)

    card_height = len(card_lines)
    card_width = max(len(line) for line in card_lines)

    # Find the top-left corner of the table box
    table_top = (max_y - BOX_HEIGHT) // 2
    table_left = (max_x - BOX_WIDTH) // 2

    # Center card inside the table
    card_y = table_top + (BOX_HEIGHT - card_height) // 2
    card_x = table_left + (BOX_WIDTH - card_width) // 2

    for i, line in enumerate(card_lines):
        stdscr.addstr(card_y + i, card_x, line)

    stdscr.refresh()

    stdscr.refresh()


def reveal_cards(stdscr, flip_order, values):
    positions = get_player_positions(stdscr)

    for key in flip_order:
        y, x = positions[key]
        cards = values[key]

        if cards[0][0] == "K":
            continue
        
        for i, card_str in enumerate(cards):
            value = card_str[:-1]
            suit = card_str[-1]
            x_offset = x + i * 8  # Adjust horizontal space between cards
            flip_card(stdscr, y + 1, x_offset, value, suit)
            stdscr.refresh()
            time.sleep(CARD_DELAY)

def player_action(stdscr, seat, action):
    positions = get_player_positions(stdscr)
    y, x = positions[seat]
    stdscr.addstr(y + 7, x - len(action) // 2, action)
    stdscr.refresh()

def table_message(stdscr, message):
    clear_waiting(stdscr)
    max_y, max_x = stdscr.getmaxyx()
    msg_y = (max_y - 10) // 2 + 4
    msg_x = (max_x - len(message)) // 2
    stdscr.addstr(msg_y, msg_x, message, curses.A_BOLD)
    stdscr.refresh()

def clear_waiting(stdscr):
    max_y, max_x = stdscr.getmaxyx()
    msg_y = (max_y - BOX_HEIGHT) // 2 + 4
    filler = "|" + " " * 58 + "|"
    msg_x = (max_x - len(filler)) // 2
    stdscr.addstr(msg_y, msg_x, filler)
    stdscr.refresh()


def draw_table(stdscr, players):
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    draw_center_box(stdscr)

    positions = get_player_positions(stdscr)

    for i in range(6):
        if i in players:
            name, lives, isDealer = players[i]
            y, x = positions[i]
            draw_player_label(stdscr, y, x, name, lives, isDealer)

    stdscr.refresh()

def decision_card(stdscr, card):
    value = card[:-1]
    suit = card[-1]

    max_y, max_x = stdscr.getmaxyx()
    card_lines = draw_card(value, suit)

    card_height = len(card_lines)
    card_width = max(len(line) for line in card_lines)

    # Calculate the center of the table box, not the whole screen
    table_top = (max_y - BOX_HEIGHT) // 2
    table_left = (max_x - BOX_WIDTH) // 2

    # Center inside the box
    card_y = table_top + (BOX_HEIGHT - card_height) // 2
    card_x = table_left + (BOX_WIDTH - card_width) // 2

    for i, line in enumerate(card_lines):
        stdscr.addstr(card_y + i, card_x, line)

    prompt = "[s] switch || [k] keep"
    prompt_x = table_left + (BOX_WIDTH - len(prompt)) // 2
    stdscr.addstr(card_y + card_height + 1, prompt_x, prompt)

    stdscr.refresh()

    flush_input_curses(stdscr)
    
    decision = 'keep\n'
    while True:
        key = stdscr.getch()
        if key == ord('s'):
            decision = 'switch\n'
            break
        elif key == ord('k'):
            break

    stdscr.move(card_y + card_height + 1, prompt_x)

    # replace prompt with table edges
    stdscr.addstr(card_y + card_height + 1, prompt_x - 19 , "|                                                          |")
    stdscr.clrtoeol()
    stdscr.refresh()
    return decision

def new_card(stdscr, card):
    value = card[:-1]
    suit = card[-1]

    max_y, max_x = stdscr.getmaxyx()
    card_lines = draw_card(value, suit)

    card_height = len(card_lines)
    card_width = max(len(line) for line in card_lines)

    # Find the top-left corner of the table box
    table_top = (max_y - BOX_HEIGHT) // 2
    table_left = (max_x - BOX_WIDTH) // 2

    # Center card inside the table
    card_y = table_top + (BOX_HEIGHT - card_height) // 2
    card_x = table_left + (BOX_WIDTH - card_width) // 2

    for i, line in enumerate(card_lines):
        stdscr.addstr(card_y + i, card_x, line)

    stdscr.refresh()

def losers(stdscr, usernames, cards):
    max_y, max_x = stdscr.getmaxyx()

    # Centered message at the top
    message = f"{', '.join(usernames)} lost with"
    msg_x = (max_x - len(message)) // 2
    stdscr.addstr(2, msg_x, message)

    # Use one card to determine card dimensions
    sample_card = draw_card("A", "♠")
    card_width = len(sample_card[0])
    card_height = len(sample_card)

    total = len(cards)
    spacing = 4
    total_width = total * card_width + (total - 1) * spacing
    start_x = (max_x - total_width) // 2
    card_y = 4  # Line where cards start

    for i, card_str in enumerate(cards):
        value = card_str[:-1]
        suit = card_str[-1]
        card_lines = draw_card(value, suit)
        card_x = start_x + i * (card_width + spacing)

        for j, line in enumerate(card_lines):
            stdscr.addstr(card_y + j, card_x, line)

    stdscr.refresh()
