import socket
import argparse
from select import select
from server import Server

HOST = '127.0.0.1'
PORT = 53

parser = argparse.ArgumentParser()
parser.add_argument("fhost", type=str, help="Forwarder host")
parser.add_argument("fport", type=int, help="Forwarder port")
parser.add_argument("--port", type=int, help="Listening port", default=PORT)
args = parser.parse_args()

s_addr = HOST, args.port
f_addr = args.fhost, args.fport

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(s_addr)
    while True:
        if not select([sock], [], [])[0]:
            continue
        data, cl_addr = sock.recvfrom(4096)
        Server(data, cl_addr, f_addr, sock).start()
