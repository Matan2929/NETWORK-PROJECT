# Author: Matan Shapira
import queue
import socket
import traceback
import threading
from tcp_by_size import send_with_size, recv_by_size
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import pygame
import time
import random

pygame.init()

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 1200
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Game')

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (50, 100, 200)
BG = (204,220,254)

LOGIN_PAGE = pygame.image.load('login_screen.png')
ROOMS_PAGE = pygame.image.load('room_screen.png')
WAIT_FOR_PAGE = pygame.image.load('wait_for_player.png')
JOINED_PAGE = pygame.image.load('joined_room.png')
PLAYER_LEFT = pygame.image.load('player_exit.png')
P1_ROCK = pygame.image.load('rock.png')
P1_PAPER = pygame.image.load('Paper.png')
P1_SCISSORS = pygame.image.load('Scissors.png')
P1 = P1_ROCK
P1_X_ROCK = 20
P1_Y_ROCK = 950

P2_ROCK = pygame.transform.flip(P1_ROCK,True,False)
P2_PAPER = pygame.transform.flip(P1_PAPER,True,False)
P2_SCISSORS = pygame.transform.flip(P1_SCISSORS,True,False)
P2 = P2_ROCK
P2_X_ROCK = 736
P2_Y_ROCK = 950

FINISH = False

GAME_OVER = pygame.image.load('game_over.png')
PLAY_AGAIN = pygame.image.load('PlayAgain_button.png')
EXIT_GAME = pygame.image.load('exit_button.png')
PLAY_AGAIN_PAGE = pygame.image.load('play_again_page.png')
WAIT_FOR_PLAY_AGAIN_PAGE = pygame.image.load('wait_for_play_again.png')

YOU_ARROW = pygame.image.load('red_arrow.png')
MENU = pygame.image.load('menu_icon.jpg')
GO_TO_MENU = False
TIME = 10
FONT = pygame.font.Font(None, 100)

connected = False
RSA_KEY = None
CONTINUE_RECIVING_DATA = True
def AES_encrypt_CBC(key, plain_text):
    cipher = AES.new(key, AES.MODE_CBC)
    iv = cipher.iv
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text, iv

def AES_decrypt_CBC(key, cipher_text, iv):
    decrypt_cipher = AES.new(key, AES.MODE_CBC, iv)
    plain_text = unpad(decrypt_cipher.decrypt(cipher_text), AES.block_size)
    return plain_text

def send_encryped(sock, bdata, key):
    if type(bdata) == str:
        bdata = bdata.encode()
    cipher, iv = AES_encrypt_CBC(key, bdata)
    send_with_size(sock, iv)
    send_with_size(sock, cipher)

def receive_decrypted(sock, key):
    iv = recv_by_size(sock)
    enc_data = recv_by_size(sock)
    data = AES_decrypt_CBC(key, enc_data, iv)
    return data

#  generating rsa key and
def send_key_rsa():
    rsa_key = RSA.generate(3072)
    public_rsa_key = rsa_key.publickey().export_key()
    cipher = PKCS1_OAEP.new(rsa_key)
    return public_rsa_key, cipher


def recv_key(encrypted_key, cipher):
    decrypted_key = cipher.decrypt(encrypted_key)
    return decrypted_key

def handle_rsa(sock):
    public_rsa_key, cipher = send_key_rsa()
    sock.send(public_rsa_key)
    encrypted_key = sock.recv(4096)
    key = recv_key(encrypted_key, cipher)
    return key

def send_data(sock,data):
    global RSA_KEY
    send_encryped(sock,data,RSA_KEY)

def recv_data(sock):
    global RSA_KEY
    sock.settimeout(2)
    data = receive_decrypted(sock,RSA_KEY)
    return data

# Function to handle text input
def handle_input(input_text, event):
    if event.key == pygame.K_BACKSPACE:
        input_text = input_text[:-1]  # Remove last character
    elif event.key == pygame.K_RETURN:
        pass  # Do nothing on pressing Enter key
    else:
        input_text += event.unicode  # Add typed character
    return input_text

def main_request():
    global CONTINUE_RECIVING_DATA,P1,P1_ROCK,P1_X_ROCK,P1_Y_ROCK,P2,P2_ROCK,P2_X_ROCK,P2_Y_ROCK,FINISH,TIME
    CONTINUE_RECIVING_DATA = False
    P1 = P1_ROCK
    P1_X_ROCK = 20
    P1_Y_ROCK = 950
    P2 = P2_ROCK
    P2_X_ROCK = 736
    P2_Y_ROCK = 950
    FINISH = False
    TIME = 10
def protocol_build_reply(request,sock):
    try:
        request = request.decode()
        fields = request.split('~')
        request_code = request[:4]
        to_send = ''
        if request_code == 'EXTR':
            to_send = request_code
        elif request_code == 'ERRR':
            print(request)
            to_send = fields[2]
        elif request_code == 'SIGS' or request_code == 'LOGS':
            to_send = request_code
        elif request_code == 'CRES' or request_code == 'JOIS':
            to_send = request_code
        elif request_code == 'STRT':
            to_send = request_code
        elif request_code == 'MAIN':
            main_request()
            to_send = request_code
        elif request_code == 'RSPS':
            to_send = request
        elif request_code == 'PLYS':
            to_send = request
        elif request_code == 'PLYR':
            to_send = request_code
        elif request_code == 'WINS':
            to_send = request
        return to_send.encode()
    except Exception as err:
        print(f'Server replay bad format -> {err}')


def handle_request(request,sock):
    try:
        request_code = request[:4]
        to_send = protocol_build_reply(request, sock)
        if request_code == b'EXTR':
            return to_send, True
    except Exception as err:
        print(traceback.format_exc())
        to_send = b'ERRR~001~General error'
    return to_send, False

def login_page(sock):
    global screen
    global BG
    global LOGIN_PAGE
    global SCREEN_WIDTH
    global SCREEN_HEIGHT
    global GO_TO_MENU
    # Font
    font = pygame.font.Font(None, 40)


    # Input box dimensions and position
    input_box_width = 400
    input_box_height = 50
    input_box_spacing = 20

    # For choosing sign up/login

    # Sign In Button
    sign_in_button_width = 130
    sign_in_button_height = 50
    sign_in_button_x = (SCREEN_WIDTH - sign_in_button_width) // 2 -130
    sign_in_button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 120
    sign_in_button_rect = pygame.Rect(sign_in_button_x, sign_in_button_y, sign_in_button_width, sign_in_button_height)
    sign_in_button_text = 'Sign In'
    sign_in_button_color = GREEN
    sign_in_button_pressed_color = (100, 100, 100)

    # Sign Up Button
    sign_up_button_width = 130
    sign_up_button_height = 50
    sign_up_button_x = (SCREEN_WIDTH - sign_up_button_width) // 2 + +130
    sign_up_button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 120
    sign_up_button_rect = pygame.Rect(sign_up_button_x, sign_up_button_y, sign_up_button_width, sign_up_button_height)
    sign_up_button_text = 'Sign Up'
    sign_up_button_color = GREEN
    sign_up_button_pressed_color = (100, 100, 100)

    running = True
    sign_in_button_pressed = False
    sign_up_button_pressed = False
    code_to_send = ''
    exit_game = False
    while running:
        current_time = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                exit_game = True
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if sign_in_button_rect.collidepoint(event.pos):
                        sign_in_button_pressed = True
                elif sign_up_button_rect.collidepoint(event.pos):
                        sign_up_button_pressed = True

        # Clear the screen
        screen.fill(BG)
        screen.blit(LOGIN_PAGE, (188, 70))
        # Draw input boxes

        # Draw button
        if sign_in_button_pressed:
            pygame.draw.rect(screen, sign_in_button_pressed_color, sign_in_button_rect, border_radius=10)
            code_to_send = 'LOGR'
            running = False

        elif sign_up_button_pressed:
            pygame.draw.rect(screen, sign_up_button_pressed_color, sign_up_button_rect, border_radius=10)
            code_to_send = 'SIGR'
            running = False

        else:
            pygame.draw.rect(screen, sign_in_button_color, sign_in_button_rect, border_radius=10)
            pygame.draw.rect(screen, sign_up_button_color, sign_up_button_rect, border_radius=10)
        button_text_rendered = font.render(sign_in_button_text, True, WHITE)
        screen.blit(button_text_rendered, (sign_in_button_x + 15, sign_in_button_y + 10))
        button_text_rendered = font.render(sign_up_button_text, True, WHITE)
        screen.blit(button_text_rendered, (sign_up_button_x + 15, sign_up_button_y + 10))

        # Update the display
        pygame.display.flip()
        time.sleep(0.1)
    # If pressed exit
    if exit_game:
        return True

    # Input box 1
    input_box1_x = (SCREEN_WIDTH - input_box_width) // 2
    input_box1_y = (SCREEN_HEIGHT - input_box_height) // 2 - input_box_height - input_box_spacing + 120
    input_box1 = pygame.Rect(input_box1_x, input_box1_y, input_box_width, input_box_height)
    input_text1 = ''
    input_text_rendered1 = font.render('Username', True, GRAY)

    # Input box 2
    input_box2_x = (SCREEN_WIDTH - input_box_width) // 2
    input_box2_y = (SCREEN_HEIGHT - input_box_height) // 2 + input_box_spacing + 120
    input_box2 = pygame.Rect(input_box2_x, input_box2_y, input_box_width, input_box_height)
    input_text2 = ''
    input_text_rendered2 = font.render('Password', True, GRAY)



    # Submitting Button
    button_width = 130
    button_height = 50
    button_x = (SCREEN_WIDTH - button_width) // 2
    button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 120
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    button_text = 'Submit'
    button_color = GRAY
    button_pressed_color = (100, 100, 100)

    # Cursor variables
    cursor_visible = True
    last_cursor_switch = 0
    cursor_blink_interval = 0.5  # in seconds
    running = True
    active_input_box = None
    previous_input_box = None
    button_pressed = False
    exit_game = False
    try_again = False
    to_send = ''
    # submitting login/sign up data
    while running:
        current_time = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                exit_game = True
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if input_box1.collidepoint(event.pos):
                    active_input_box = 1
                elif input_box2.collidepoint(event.pos):
                    active_input_box = 2
                elif button_rect.collidepoint(event.pos):
                    if input_text1 and input_text2:
                        button_pressed = True
            elif event.type == pygame.KEYDOWN and active_input_box is not None:
                if active_input_box == 1:
                    input_text1 = handle_input(input_text1, event)
                elif active_input_box == 2:
                    input_text2 = handle_input(input_text2, event)

        # Handle cursor blinking
        if current_time - last_cursor_switch > cursor_blink_interval:
            cursor_visible = not cursor_visible
            last_cursor_switch = current_time

        # Clear the screen
        screen.fill(BG)
        screen.blit(LOGIN_PAGE, (188, 70))
        menu = Button(25,25,MENU,0.5)
        GO_TO_MENU = menu.draw()
        if GO_TO_MENU:
            return False
        # Draw input boxes
        pygame.draw.rect(screen, BLUE, input_box1, border_radius=10)
        pygame.draw.rect(screen, BLUE, input_box2, border_radius=10)

        # Render and blit input text
        if input_text1 == '' and active_input_box != 1:
            screen.blit(input_text_rendered1, (input_box1.x + 10, input_box1.y + 10))
        else:
            input_text_rendered1 = font.render(input_text1, True, BLACK)
            screen.blit(input_text_rendered1, (input_box1.x + 10, input_box1.y + 10))

        if input_text2 == '' and active_input_box != 2:
            screen.blit(input_text_rendered2, (input_box2.x + 10, input_box2.y + 10))
        else:
            input_text_rendered2 = font.render(input_text2, True, BLACK)
            screen.blit(input_text_rendered2, (input_box2.x + 10, input_box2.y + 10))

        # Draw cursor in active input box
        if cursor_visible and active_input_box is not None:
            if active_input_box == 1:
                cursor_pos = font.size(input_text1)[0] + 15
                pygame.draw.line(screen, BLACK, (input_box1.x + cursor_pos, input_box1.y + 10),
                                 (input_box1.x + cursor_pos, input_box1.y + input_box_height - 10), 2)
            elif active_input_box == 2:
                cursor_pos = font.size(input_text2)[0] + 15
                pygame.draw.line(screen, BLACK, (input_box2.x + cursor_pos, input_box2.y + 10),
                                 (input_box2.x + cursor_pos, input_box2.y + input_box_height - 10), 2)
        if try_again:
            msg = to_send.decode()
            font2 = pygame.font.Font(None, 28)
            try_again = font2.render(msg, True, RED)
            screen.blit(try_again, (375, 870))
            msg = "Please Try Again"
            try_again = font2.render(msg, True, RED)
            screen.blit(try_again, (430, 900))

        # Update active input box
        if previous_input_box != active_input_box:
            if previous_input_box == 1:
                input_text1 = '' if input_text1 == 'Username' else input_text1
            elif previous_input_box == 2:
                input_text2 = '' if input_text2 == 'Password' else input_text2
            previous_input_box = active_input_box

        # Draw button
        if button_pressed:
            pygame.draw.rect(screen, button_pressed_color, button_rect, border_radius=10)
            to_send = f'{code_to_send}~{input_text1}~{input_text2}'
            to_send.encode()
            send_data(sock, to_send)
            data = recv_data(sock)
            to_send, leave = handle_request(data, sock)
            if to_send == b'':
                running = False
                exit_game = True
            else:
                if to_send == b'SIGS' or to_send == b'LOGS':
                    running = False
                else:
                    button_pressed = False
                    try_again = True



        else:
            pygame.draw.rect(screen, button_color, button_rect, border_radius=10)
        button_text_rendered = font.render(button_text, True, WHITE)
        screen.blit(button_text_rendered, (button_x + 15, button_y + 10))

        # Change button color based on input boxes' status
        if input_text1 and input_text2:
            button_color = GREEN
        else:
            button_color = GRAY

        # Update the display
        pygame.display.flip()
    if exit_game:
        return True
    return False



def rooms_page(sock):
    global screen
    global BG
    global ROOMS_PAGE
    global SCREEN_WIDTH
    global SCREEN_HEIGHT
    global GO_TO_MENU
    # Font
    font = pygame.font.Font(None, 40)

    # Input box dimensions and position
    input_box_width = 400
    input_box_height = 50
    input_box_spacing = 20

    # For choosing sign up/login

    # Join Button
    join_button_width = 170
    join_button_height = 50
    join_button_x = (SCREEN_WIDTH - join_button_width) // 2 - 130
    join_button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 100
    join_button_rect = pygame.Rect(join_button_x, join_button_y, join_button_width, join_button_height)
    join_button_text = 'Join Room'
    join_button_color = GREEN
    join_button_pressed_color = (100, 100, 100)

    # Create Button
    create_button_width = 200
    create_button_height = 50
    create_button_x = (SCREEN_WIDTH - create_button_width) // 2 + + 170
    create_button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 100
    create_button_rect = pygame.Rect(create_button_x, create_button_y, create_button_width, create_button_height)
    create_button_text = 'Create Room'
    create_button_color = GREEN
    create_button_pressed_color = (100, 100, 100)

    running = True
    join_button_pressed = False
    create_button_pressed = False
    code_to_send = ''
    exit_game = False
    while running:
        current_time = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                exit_game = True
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if join_button_rect.collidepoint(event.pos):
                    join_button_pressed = True
                elif create_button_rect.collidepoint(event.pos):
                    create_button_pressed = True

        # Clear the screen
        screen.fill(BG)
        screen.blit(ROOMS_PAGE, (188, 70))
        # Draw input boxes

        # Draw button
        if join_button_pressed:
            pygame.draw.rect(screen, join_button_pressed_color, join_button_rect, border_radius=10)
            code_to_send = 'JOIR'
            running = False

        elif create_button_pressed:
            pygame.draw.rect(screen, create_button_pressed_color, create_button_rect, border_radius=10)
            code_to_send = 'CRER'
            running = False

        else:
            pygame.draw.rect(screen, join_button_color, join_button_rect, border_radius=10)
            pygame.draw.rect(screen, create_button_color, create_button_rect, border_radius=10)
        button_text_rendered = font.render(join_button_text, True, WHITE)
        screen.blit(button_text_rendered, (join_button_x + 15, join_button_y + 10))
        button_text_rendered = font.render(create_button_text, True, WHITE)
        screen.blit(button_text_rendered, (create_button_x + 15, create_button_y + 10))

        # Update the display
        pygame.display.flip()
        time.sleep(0.1)
    # If pressed exit
    if exit_game:
        return True,b''

    # Room
    input_box1_x = (SCREEN_WIDTH - input_box_width) // 2
    input_box1_y = (SCREEN_HEIGHT - input_box_height) // 2 - input_box_height - input_box_spacing + 200
    input_box1 = pygame.Rect(input_box1_x, input_box1_y, input_box_width, input_box_height)
    input_text1 = ''
    input_text_rendered1 = font.render('Room Code', True, GRAY)


    # Submitting Button
    button_width = 130
    button_height = 50
    button_x = (SCREEN_WIDTH - button_width) // 2
    button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 120
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
    button_text = 'Submit'
    button_color = GRAY
    button_pressed_color = (100, 100, 100)

    # Cursor variables
    cursor_visible = True
    last_cursor_switch = 0
    cursor_blink_interval = 0.5  # in seconds
    running = True
    active_input_box = None
    previous_input_box = None
    button_pressed = False
    exit_game = False
    try_again = False
    to_send = ''
    # submitting login/sign up data
    while running:
        current_time = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                exit_game = True
                break
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if input_box1.collidepoint(event.pos):
                    active_input_box = 1
                elif button_rect.collidepoint(event.pos):
                    if input_text1:
                        button_pressed = True
            elif event.type == pygame.KEYDOWN and active_input_box is not None:
                if active_input_box == 1:
                    input_text1 = handle_input(input_text1, event)

        # Handle cursor blinking
        if current_time - last_cursor_switch > cursor_blink_interval:
            cursor_visible = not cursor_visible
            last_cursor_switch = current_time

        # Clear the screen
        screen.fill(BG)
        screen.blit(ROOMS_PAGE, (188, 70))
        menu = Button(25, 25, MENU, 0.5)
        GO_TO_MENU = menu.draw()
        if GO_TO_MENU:
            return False,b''
        # Draw input boxes
        pygame.draw.rect(screen, BLUE, input_box1, border_radius=10)

        # Render and blit input text
        if input_text1 == '' and active_input_box != 1:
            screen.blit(input_text_rendered1, (input_box1.x + 10, input_box1.y + 10))
        else:
            input_text_rendered1 = font.render(input_text1, True, BLACK)
            screen.blit(input_text_rendered1, (input_box1.x + 10, input_box1.y + 10))


        # Draw cursor in active input box
        if cursor_visible and active_input_box is not None:
            if active_input_box == 1:
                cursor_pos = font.size(input_text1)[0] + 15
                pygame.draw.line(screen, BLACK, (input_box1.x + cursor_pos, input_box1.y + 10),
                                 (input_box1.x + cursor_pos, input_box1.y + input_box_height - 10), 2)
        if try_again:
            msg = to_send.decode()
            font2 = pygame.font.Font(None, 28)
            try_again = font2.render(msg, True, RED)
            if len(msg) <= 10:
                screen.blit(try_again, (450, 870))
            else:
                screen.blit(try_again, (390, 870))
            msg = "Please Try Another Room"
            try_again = font2.render(msg, True, RED)
            screen.blit(try_again, (375, 900))

        # Update active input box
        if previous_input_box != active_input_box:
            if previous_input_box == 1:
                input_text1 = '' if input_text1 == 'Room Code' else input_text1
            previous_input_box = active_input_box

        # Draw button
        if button_pressed:
            pygame.draw.rect(screen, button_pressed_color, button_rect, border_radius=10)
            to_send = f'{code_to_send}~{input_text1}'
            to_send.encode()

            send_data(sock, to_send)
            data = recv_data(sock)
            to_send, leave = handle_request(data, sock)
            if to_send == b'':
                running = False
                exit_game = True
            else:
                if to_send == b'CRES' or to_send == b'JOIS':
                    running = False
                else:
                    button_pressed = False
                    try_again = True



        else:
            pygame.draw.rect(screen, button_color, button_rect, border_radius=10)
        button_text_rendered = font.render(button_text, True, WHITE)
        screen.blit(button_text_rendered, (button_x + 15, button_y + 10))

        # Change button color based on input boxes' status
        if input_text1:
            button_color = GREEN
        else:
            button_color = GRAY

        # Update the display
        pygame.display.flip()
    if exit_game:
        return True,b''
    return False,to_send
def format_time(seconds):
    return f"{seconds:.1f}" #making the time show only one after the decimal point


def random_choice():
    option = [P1_PAPER, P1_SCISSORS, P1_ROCK]
    return random.choice(option)

# Function to draw the timer
def draw_timer():
    global screen
    global SCREEN_WIDTH
    global SCREEN_HEIGHT
    global FONT
    global TIME
    timer_text = FONT.render(format_time(TIME), True, (255,0,0))

    screen.blit(timer_text, (900,100))

class Button():
    def __init__(self, x, y, image, scale):
        width = image.get_width()
        height = image.get_height()
        self.image = pygame.transform.scale(image, (int(width * scale), int(height * scale)))
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.clicked = False

    def draw(self):
        action = False
        # mouse position
        pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(pos):
            if pygame.mouse.get_pressed()[0] == 1 and self.clicked == False:
                self.clicked = True
                action = True
            if pygame.mouse.get_pressed()[0] == 0:
                self.clicked = False
                action = False

        screen.blit(self.image, (self.rect.x, self.rect.y))
        return action
def Game(sock):
    global screen
    # call for global variant for Player 1
    global P1_ROCK
    global P1_SCISSORS
    global P1_PAPER
    global P1
    global P1_Y_ROCK
    global P1_X_ROCK

    # call for global variant for Player 2
    global P2_ROCK
    global P2_SCISSORS
    global P2_PAPER
    global P2
    global P2_Y_ROCK
    global P2_X_ROCK
    # if game over(somebody won)
    global FINISH
    global GAME_OVER
    global PLAY_AGAIN
    global EXIT_GAME
    global YOU_ARROW

    global TIME
    global CONTINUE_RECIVING_DATA
    clock = pygame.time.Clock()

    rock_button = Button(250,500,pygame.image.load('rock_button.png'),0.5)
    paper_button = Button(450,500,pygame.image.load('paper_button.png'),0.5)
    scissors_button = Button(650, 500, pygame.image.load('scissors_button.png'), 0.5)
    run = True
    rotate_down = 0 # every 7 times switch to down
    rotate_up = 0 # every 7 times switch to down
    if_rotate_up = True
    how_many_times = 0 # number of times he will move his hand
    if_pressed = False
    choice = None
    show_winner = False
    got_other_player_choice = False
    data_queue = queue.Queue()
    # Start the receiving data thread
    CONTINUE_RECIVING_DATA = True
    print('Creating Thread')
    receive_thread = threading.Thread(target=receive_data_thread, args=(sock, data_queue))
    receive_thread.start()
    while run:
        screen.fill(BG)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print('ERRR~010~Exit While Playing')
                CONTINUE_RECIVING_DATA = False
                print('Waiting For Thread To Die')
                receive_thread.join()
                return True

        screen.blit(P1,(P1_X_ROCK,P1_Y_ROCK))
        screen.blit(P2, (P2_X_ROCK, P2_Y_ROCK))
        screen.blit(YOU_ARROW,(P1_X_ROCK+60,P1_Y_ROCK-100))


        if not FINISH:
            if not if_pressed and data_queue.empty():
                dt = clock.tick(60) / 1000  # Convert milliseconds to seconds
                TIME-=dt
                draw_timer()
                if_pressed = rock_button.draw()
                to_send = 'RSPR~'
                if if_pressed:
                    choice = P1_ROCK
                    to_send += 'ROCK'
                else:
                    if_pressed = paper_button.draw()
                    if if_pressed:
                        choice = P1_PAPER
                        to_send += 'PAPER'
                    else:
                        if_pressed = scissors_button.draw()
                        if if_pressed:
                            choice = P1_SCISSORS
                            to_send += 'SCISSORS'
                if if_pressed:
                    send_data(sock,to_send)
                    time.sleep(0.1)

            if TIME < 0.1 and data_queue.empty() and not if_pressed:
                if_pressed = True
                choice = random_choice()
                to_send = 'RSPR~'
                if choice == P1_ROCK:
                    to_send += 'ROCK'
                elif choice == P1_PAPER:
                    to_send += 'PAPER'
                elif choice == P1_SCISSORS:
                    to_send += 'SCISSORS'
                send_data(sock, to_send)

            if not data_queue.empty():
                data = data_queue.get()
                request = data[0]
                code = request[:4]
                l = data[1]
                if l:
                    CONTINUE_RECIVING_DATA = False
                    print('Waiting For Thread To Die')
                    receive_thread.join()
                    return True
                if code == b'RSPS':
                    p2_c = request[5:]
                    p2_choice = None
                    if p2_c == b'ROCK':
                        p2_choice = P2_ROCK
                    elif p2_c == b'PAPER':
                        p2_choice = P2_PAPER
                    elif p2_c == b'SCISSORS':
                        p2_choice = P2_SCISSORS
                    got_other_player_choice = True
                elif code == b'MAIN':
                    print('Waiting For Thread To Die')
                    receive_thread.join()
                    return False
                elif code == b'WINS':
                    winner = request[5:]
                    winner = winner.decode()
                    show_winner = True
            if how_many_times<3 and if_pressed and got_other_player_choice: # every 10 the hand returns to the point she started moving
                rotate_down -= 1
                rotate_up += 1

                if rotate_down == -5:
                    if_rotate_up = False
                    rotate_down = 4
                if rotate_up % 10 == 0:
                    how_many_times += 1
                    rotate_up = 1
                    if_rotate_up = True

                if if_rotate_up:
                    if rotate_up == 1 and how_many_times >= 1:
                        P1_X_ROCK = 20
                        P1_Y_ROCK = 950
                        P2_X_ROCK = 736
                        P2_Y_ROCK = 950
                    elif rotate_up == 1:
                        pass
                    else:
                        P1_X_ROCK -= 7
                        P1_Y_ROCK -= 7
                        P2_X_ROCK -= 7
                        P2_Y_ROCK -= 7
                    P1 = pygame.transform.rotate(P1_ROCK,5*rotate_up)
                    P2 = pygame.transform.rotate(P2_ROCK,-5*rotate_up)
                else:
                    if rotate_down % 4 != 0:
                        P1_X_ROCK += 7
                        P1_Y_ROCK += 7
                        P2_X_ROCK += 7
                        P2_Y_ROCK += 7
                    P1 = pygame.transform.rotate(P1_ROCK, 5*rotate_down)
                    P2 = pygame.transform.rotate(P2_ROCK, -5 * rotate_down)
                time.sleep(0.05)
            elif how_many_times >= 3 and if_pressed and got_other_player_choice:
                P1 = choice
                if P1 == P1_PAPER:
                    P1_X_ROCK = 23
                    P1_Y_ROCK = 900
                P2 = p2_choice
                if P2 == P2_PAPER:
                    P2_X_ROCK = 610
                    P2_Y_ROCK = 900
                if P2 == P2_SCISSORS:
                    P2_X_ROCK = 627
                FINISH = True
        else:
            screen.blit(GAME_OVER, (188, 70))
            play_again_button = Button(270, 630, PLAY_AGAIN, 1)
            exit_game_button = Button(580, 630, EXIT_GAME, 1)
            exit_game = exit_game_button.draw()
            play_again = play_again_button.draw()
            if not data_queue.empty():
                data = data_queue.get()
                request = data[0]
                code = request[:4]
                l = data[1]
                if l:
                    CONTINUE_RECIVING_DATA = False
                    print('Waiting For Thread To Die')
                    receive_thread.join()
                    return True
                elif code == b'MAIN':
                    print('Waiting For Thread To Die')
                    receive_thread.join()
                    return False
                elif code == b'PLYR':
                    l,play = play_again_request()
                    if l:
                        CONTINUE_RECIVING_DATA = False
                        print('Waiting For Thread To Die')
                        receive_thread.join()
                        return True
                    to_send = 'PLYO~'+str(play)
                    send_data(sock,to_send)
                    if not play:
                        main_request()
                        print('Waiting For Thread To Die')
                        receive_thread.join()
                        return False
                    rotate_down = 0  # every 7 times switch to down
                    rotate_up = 0  # every 7 times switch to down
                    if_rotate_up = True
                    how_many_times = 0  # number of times he will move his hand
                    if_pressed = False
                    P1 = P1_ROCK
                    P1_X_ROCK = 20
                    P1_Y_ROCK = 950
                    P2 = P2_ROCK
                    P2_X_ROCK = 736
                    P2_Y_ROCK = 950
                    FINISH = False
                    TIME = 10
                    got_other_player_choice = False
                    clock = pygame.time.Clock()
                elif code == b'WINS':
                    winner = request[5:]
                    winner = winner.decode()
                    show_winner = True
            if show_winner:
                # return 1 for player 1 win
                # return 2 for player 2 win
                # return 0 for tie
                if winner == '1':
                    you_won = pygame.image.load('you_won.png')
                    screen.blit(you_won,(330,519))
                elif winner == '2':
                    you_lost = pygame.image.load('you_lost.png')
                    screen.blit(you_lost, (330, 519))
                else:
                    tie = pygame.image.load('draw.png')
                    screen.blit(tie,(400,519))
            if exit_game:
                CONTINUE_RECIVING_DATA = False
                print('Waiting For Thread To Die')
                receive_thread.join()
                return True
            if play_again:
                to_send = 'PLYG'
                send_data(sock,to_send)
                leave,play = wait_for_play_again(data_queue)
                if leave:
                    CONTINUE_RECIVING_DATA = False
                    print('Waiting For Thread To Die')
                    receive_thread.join()
                    return True
                if not play:
                    main_request()
                    print('Waiting For Thread To Die')
                    receive_thread.join()

                    return False
                rotate_down = 0  # every 7 times switch to down
                rotate_up = 0  # every 7 times switch to down
                if_rotate_up = True
                how_many_times = 0  # number of times he will move his hand
                if_pressed = False
                P1 = P1_ROCK
                P1_X_ROCK = 20
                P1_Y_ROCK = 950
                P2 = P2_ROCK
                P2_X_ROCK = 736
                P2_Y_ROCK = 950
                FINISH = False
                TIME = 10
                got_other_player_choice = False
                show_winner = False
                clock = pygame.time.Clock()
        pygame.display.update()

    if receive_thread.is_alive():
        print('Waiting For Thread To Die')
        receive_thread.join()
    return True



def play_again_request():
    global screen
    global BG
    global PLAY_AGAIN_PAGE
    global SCREEN_WIDTH
    global SCREEN_HEIGHT
    # Font
    font = pygame.font.Font(None, 40)

    input_box_height = 50
    input_box_spacing = 20

    # Accept Button
    accept_button_width = 130
    accept_button_height = 50
    accept_button_x = (SCREEN_WIDTH - accept_button_width) // 2 - 130
    accept_button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 30
    accept_button_rect = pygame.Rect(accept_button_x, accept_button_y, accept_button_width, accept_button_height)
    accept_button_text = 'Accept'
    accept_button_color = GREEN
    accept_button_pressed_color = (100, 100, 100)

    # Decline Button
    decline_button_width = 130
    decline_button_height = 50
    decline_button_x = (SCREEN_WIDTH - decline_button_width) // 2 + +130
    decline_button_y = (SCREEN_HEIGHT + input_box_height) // 2 + 2 * input_box_spacing + 30
    decline_button_rect = pygame.Rect(decline_button_x, decline_button_y, decline_button_width, decline_button_height)
    decline_button_text = 'Decline'
    decline_button_color = GREEN
    decline_button_pressed_color = (100, 100, 100)

    accept_button_pressed = False
    decline_button_pressed = False
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True, True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if accept_button_rect.collidepoint(event.pos):
                    accept_button_pressed = True
                elif decline_button_rect.collidepoint(event.pos):
                    decline_button_pressed = True

        # Clear the screen
        screen.fill(BG)
        screen.blit(PLAY_AGAIN_PAGE, (188, 300))

        # Draw button
        if accept_button_pressed:
            pygame.draw.rect(screen, accept_button_pressed_color, accept_button_rect, border_radius=10)
            return False, True
        elif decline_button_pressed:
            pygame.draw.rect(screen, decline_button_pressed_color, decline_button_rect, border_radius=10)
            return False, False
        else:
            pygame.draw.rect(screen, accept_button_color, accept_button_rect, border_radius=10)
            pygame.draw.rect(screen, decline_button_color, decline_button_rect, border_radius=10)

        button_text_rendered = font.render(accept_button_text, True, WHITE)
        screen.blit(button_text_rendered, (accept_button_x + 15, accept_button_y + 10))
        button_text_rendered = font.render(decline_button_text, True, WHITE)
        screen.blit(button_text_rendered, (decline_button_x + 15, decline_button_y + 10))

        # Update the display
        pygame.display.flip()
def wait_for_play_again(data_queue):
    global screen
    global BG
    global WAIT_FOR_PAGE

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print('ERRR~011~Exit While Waiting For Play Again')
                return True,False
        screen.fill(BG)
        screen.blit(WAIT_FOR_PLAY_AGAIN_PAGE, (188, 300))
        pygame.display.update()
        if not data_queue.empty():
            data,l = data_queue.get()
            data = data.decode().split('~')
            if l:
                return True
            if data[0] == 'PLYS':
                if data[1] == 'True':
                    return False,True
                else:
                    return False,False



def receive_data_thread(sock, data_queue):
    global CONTINUE_RECIVING_DATA
    while CONTINUE_RECIVING_DATA:
        try:
            data = recv_data(sock)
            if data is not None:
                to_send, leave = handle_request(data, sock)
                send = (to_send,leave)
                data_queue.put(send)
                if to_send == b'EXTR' or leave:
                    break
        except socket.timeout:
            pass  # Timeout occurred, continue the loop
        except BlockingIOError:
            pass  # No data available, continue the loop
        except Exception as e:
            print("Error:", e)
            break


def wait_for_page(sock):
    global screen
    global BG
    global WAIT_FOR_PAGE
    global CONTINUE_RECIVING_DATA
    data_queue = queue.Queue()
    # Start the receiving data thread
    CONTINUE_RECIVING_DATA = True
    print('Creating Thread')
    receive_thread = threading.Thread(target=receive_data_thread, args=(sock,data_queue))
    receive_thread.start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print('ERRR~009~Exit While Waiting')
                CONTINUE_RECIVING_DATA = False
                print('Waiting For Thread To Die')
                receive_thread.join()
                return True
        screen.fill(BG)
        screen.blit(WAIT_FOR_PAGE, (188, 300))
        pygame.display.update()
        if not data_queue.empty():
            data = data_queue.get()
            if data[0] == b'STRT':
                CONTINUE_RECIVING_DATA = False
                break
        if not receive_thread.is_alive():
            running = False
    # wait till the thread dead
    if receive_thread.is_alive():
        print('Waiting For Thread To Die')
        receive_thread.join()
    return False

def joined_page():
    global screen
    global BG
    global JOINED_PAGE
    screen.fill(BG)
    screen.blit(JOINED_PAGE, (188, 300))
    pygame.display.update()
    time.sleep(2.2)

def player_left_page():
    global screen
    global BG
    global JOINED_PAGE
    screen.fill(BG)
    screen.blit(PLAYER_LEFT, (188, 300))
    pygame.display.update()
    time.sleep(3)

def everything(sock):
    global GO_TO_MENU
    while True:
        exit_game,code = rooms_page(sock)
        if exit_game:
            return True
        if not GO_TO_MENU:
            break
        GO_TO_MENU = False
    if code == b'CRES':
        exit_game = wait_for_page(sock)
    if code == b'JOIS':
        joined_page()
    if exit_game:
        return True
    exit_game = Game(sock)
    if exit_game:
        return True
    player_left_page()
    return False
def main(ip):
    global connected
    global RSA_KEY
    global GO_TO_MENU
    sock = socket.socket()

    port = 1233
    try:
        sock.connect((ip, port))
        print(f'Connect succeeded {ip}: {port}\n\n')
        connected = True
    except:
        print(f'Error while trying to connect.  Check ip or port -- {ip}: {port}')
    if connected:
        RSA_KEY = handle_rsa(sock)
        while True:
            exit_game = login_page(sock)
            if exit_game:
                break
            if not GO_TO_MENU:
                break
            GO_TO_MENU = False
        if not exit_game:
            while True:
                exit_game = everything(sock)
                if exit_game:
                    break
        send_data(sock, 'EXIT')
        data = recv_data(sock)
        to_send, leave = handle_request(data, sock)
        if leave:
            pygame.quit()
        print(f'Disconnect from {ip}: {port}\n\n')


if __name__ == "__main__":
    main('10.68.121.81')