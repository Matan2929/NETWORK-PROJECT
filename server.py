# Author: Matan Shapira
import time
import hashlib
import threading
import socket
import traceback
from tcp_by_size import send_with_size, recv_by_size
import os.path
import pickle
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

lock = threading.Lock()
all_to_die = False
MAX_CLIENTS = 100
sock_room = {}
users_sock = {}
sock_key = {}
rooms = {}
connected = []
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

def send_key_rsa(serialized_key):
    key = get_random_bytes(16)
    public_key = RSA.importKey(serialized_key)
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_key = cipher.encrypt(key)
    return encrypted_key, key

def send_data(sock,data):
    key = sock_key[sock]
    send_encryped(sock,data,key)


def recv_data(sock):
    key = sock_key[sock]
    data = receive_decrypted(sock,key)
    return data

def sign_up(sock,username,password):
    global users_sock
    hash_pass = hashlib.sha256(password.encode()).digest()
    if os.path.exists('users.pkl'):
        lock.acquire()
        with open('users.pkl','rb') as file:
            user_dic = pickle.load(file)
        lock.release()
        for user in user_dic:
            if user == username:
                return 'ERRR~003~Username Already Exist'
        lock.acquire()
        users_sock[username] = sock
        user_dic[username] = hash_pass
        with open('users.pkl','wb') as file:
            pickle.dump(user_dic,file)
        lock.release()
        return 'SIGS'
    else:
        lock.acquire()
        users_sock[username] = sock
        user_dic = {}
        user_dic[username] = hash_pass
        with open('users.pkl', 'wb') as file:
            pickle.dump(user_dic, file)
        lock.release()
        return 'SIGS'

def sign_in(sock,username,password):
    global users_sock
    hash_pass = hashlib.sha256(password.encode()).digest()
    if os.path.exists('users.pkl'):
        lock.acquire()
        with open('users.pkl','rb') as file:
            user_dic = pickle.load(file)
        lock.release()
        for user in user_dic:
            if user == username:
                if hash_pass == user_dic[user]:
                    if not user in users_sock.keys():
                        users_sock[user] = sock
                        return 'LOGS'
                    else:
                        return 'ERRR~006~This User Currently Connect'
                return 'ERRR~005~Wrong Password Or Username'
    return 'ERRR~004~Username Dose Not Exist'

def create_room(sock,code):
    global rooms
    global sock_room
    for k in rooms:
        if k == code:
            return 'ERRR~008~ Room Already Exist'
    l = [[sock,'']]
    rooms[code] = l
    sock_room[sock] = code
    return 'CRES'
def join_room(sock,code):
    global rooms
    global sock_room
    for k in rooms:
        if k == code:
            l = rooms[code]
            if len(l) != 1:
                return 'ERRR~007~Room Full'
            other_player = l[0]
            other_player = other_player[0]
            l.append([sock,''])
            rooms[code] = l
            sock_room[sock] = code
            send_data(other_player,'STRT')
            return 'JOIS'
    return 'ERRR~002~  Room Dose Not Exits'

def client_exit(sock):
    global sock_room
    global rooms
    global users_sock
    for k,v in users_sock.items():
        if v == sock:
            del users_sock[k]
            break
    if sock in sock_room.keys():
        l = rooms[sock_room[sock]]
        s = sock_room[sock]
        if len(l)>1:
            if l[0][0] == sock:
                send_data(l[1][0], 'MAIN')
            else:
                send_data(l[0][0], 'MAIN')
            del sock_room[l[0][0]]
            del sock_room[l[1][0]]
        else:
            del sock_room[sock]
        del rooms[s]

def send_play_again_request(sock):
    global sock_room
    global rooms
    room = sock_room[sock]
    socks = rooms[room]
    to_send = 'PLYR'
    if len(socks)>1:
        if socks[0][0] == sock:
            send_data(socks[1][0], to_send)
        else:
            send_data(socks[0][0], to_send)
    return ''

def play_again_answer(sock,play_again):
    global sock_room
    global rooms
    room = sock_room[sock]
    socks = rooms[room]
    to_send = f'PLYS~{play_again}'
    if len(socks) > 1:
        if socks[0][0] == sock:
            send_data(socks[1][0], to_send)
        else:
            send_data(socks[0][0], to_send)
        if play_again == 'False':
            del sock_room[socks[0][0]]
            del sock_room[socks[1][0]]
            del rooms[room]
    return ''

def Game(sock,choice):
    global sock_room
    global rooms
    room = sock_room[sock]
    socks = rooms[room]
    if len(socks)>1:
        if socks[0][0] == sock:
            socks[0][1] = choice
        else:
            socks[1][1] = choice
        if socks[0][1] != '' and socks[1][1] != '':
            send_choice(socks)
    return ''
def send_choice(socks):
    to_send1 = f'RSPS~'
    to_send2 = f'RSPS~'
    if len(socks) > 1:
        choice1 = socks[0][1]
        choice2 = socks[1][1]
        to_send1+=choice1
        to_send2+=choice2
        send_data(socks[1][0],to_send1)
        send_data(socks[0][0], to_send2)
        check_winner(socks)
    socks[0][1] = ''
    socks[1][1] = ''
    return ''

def check_winner(socks):
    choice1 = socks[0][1]
    choice2 = socks[1][1]
    to_send1 = 'WINS~'
    to_send2 = 'WINS~'
    if choice1 == 'ROCK':
        if choice2 == 'SCISSORS':
            to_send1 += '1'
            to_send2 += '2'
        elif choice2 == 'PAPER':
            to_send1 += '2'
            to_send2 += '1'
        else:
            to_send1 += '0'
            to_send2 += '0'
    elif choice1 == 'PAPER':
        if choice2 == 'ROCK':
            to_send1 += '1'
            to_send2 += '2'
        elif choice2 == 'SCISSORS':
            to_send1 += '2'
            to_send2 += '1'
        else:
            to_send1 += '0'
            to_send2 += '0'
    else:
        if choice2 == 'PAPER':
            to_send1 += '1'
            to_send2 += '2'
        elif choice2 == 'ROCK':
            to_send1 += '2'
            to_send2 += '1'
        else:
            to_send1 += '0'
            to_send2 += '0'
    send_data(socks[0][0], to_send1)
    send_data(socks[1][0], to_send2)
def protocol_build_reply(request,sock):
    request = request.decode()
    fields = request.split('~')
    request_code = request[:4]
    to_send = ''
    if request_code == 'EXIT':
        client_exit(sock)
        to_send = 'EXTR'
    elif request_code == 'SIGR':
        to_send = sign_up(sock,fields[1],fields[2])
    elif request_code == 'LOGR':
        to_send = sign_in(sock,fields[1],fields[2])
    elif request_code == 'CRER':
        to_send = create_room(sock, fields[1])
    elif request_code == 'JOIR':
        to_send = join_room(sock, fields[1])
    elif request_code == 'RSPR':
        to_send = Game(sock, fields[1])
    elif request_code == 'PLYG':
        to_send = send_play_again_request(sock)
    elif request_code == 'PLYO':
        to_send = play_again_answer(sock, fields[1])
    return to_send.encode()

def handle_request(request,sock):
    try:
        request_code = request[:4]
        to_send = protocol_build_reply(request, sock)
        if request_code == b'EXIT':
            return to_send, True
    except Exception as err:
        print(traceback.format_exc())
        to_send = b'ERRR~001~General error'
    return to_send, False



def handle_client(sock,index):
    global all_to_die
    global RSA_KEY
    print("Client number " + index + " connected")
    serialized_key = sock.recv(4096)  # get the public key from the client
    to_send, key = send_key_rsa(serialized_key)  # send the common AES key to the client using the RSA public cipher
    sock.send(to_send)
    sock_key[sock] = key
    finish = False
    while not finish:
        if all_to_die:
            print('will close due to main server issue')
            break
        try:
            byte_data = recv_data(sock)
            to_send, finish = handle_request(byte_data, sock)
            if to_send != b'':
                send_data(sock,to_send)
            if finish:
                time.sleep(1)
                break
        except socket.error as err:
            print(f'Socket Error exit client loop: err:  {err}')
            client_exit(sock)
            break
        except Exception as err:
            print(f'General Error %s exit client loop: {err}')
            print(traceback.format_exc())
            client_exit(sock)
            break
    print(f'Waiting For Client {index} Thread To Die')
    print(f'Client {index} Exit')
    sock.close()


def main():
    global all_to_die
    threads = []
    srv_sock = socket.socket()
    srv_sock.bind(('0.0.0.0', 1233))
    srv_sock.listen(50)

    i = 1
    while True:
        print("\nMain Thread: before accepting ...")
        cli_sock, addr = srv_sock.accept()
        t = threading.Thread(target=handle_client, args=(cli_sock,str(i)))
        t.start()
        threads.append(t)
        print(f"\nThread For Client {i} Started")
        i += 1
        threads.append(t)
        if i > MAX_CLIENTS:
            print("Main Thread: going down -> too much clients")
            break
    i = 1
    all_to_die = True
    print("Main Thread: waiting to all clients to die...")
    for t in threads:
        print(f"\nWaiting For Client {i} To Die")
        t.join()
    srv_sock.close()
    print('Bye...')


if __name__ == '__main__':
    main()