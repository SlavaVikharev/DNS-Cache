import socket
import threading
import time
from packet import Packet, AnswerPacket

cache = {}


class Server(threading.Thread):
    def __init__(self, data, cl_addr, f_addr, sock):
        super().__init__()
        self.data = data
        self.cl_addr = cl_addr
        self.f_addr = f_addr
        self.sock = sock

    def from_forwarder(self, key):
        print('Forwarder')

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as f_sock:
                f_sock.sendto(self.data, self.f_addr)

                res = f_sock.recv(4096)
                res_packet = AnswerPacket(res)

                self.sock.sendto(res_packet.data, self.cl_addr)

                cache[key] = res_packet, time.time()
        except socket.error as e:
            print(e)

    def from_cache(self, req_id, cached):
        print('Cache')

        cache_packet, cache_time = cached
        reply_packet = AnswerPacket(cache_packet.data)
        reply_packet.set_id(req_id)
        reply_packet.set_ttl(cache_time)
        self.sock.sendto(reply_packet.data, self.cl_addr)

    def run(self):
        req_packet = Packet(self.data)

        key = req_packet.data[2:]

        if key not in cache:
            self.from_forwarder(key)
            return

        cache_packet, cache_time = cache[key]

        if time.time() - cache_time > cache_packet.ttl:
            self.from_forwarder(key)
            return

        self.from_cache(req_packet.header[0], cache[key])
