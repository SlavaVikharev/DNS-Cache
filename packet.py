import time
import struct
from itertools import takewhile


TYPES = {
    1: 'A',
    2: 'NS',
    3: 'MD',
    4: 'MF',
    5: 'CNAME',
    6: 'SOA',
    7: 'MB',
    8: 'MG',
    9: 'MR',
    10: 'NULL',
    11: 'WKS',
    12: 'PTR',
    13: 'HINFO',
    14: 'MINFO',
    15: 'MX',
    16: 'TXT'
}

CLASSES = {
    1: 'IN',
    2: 'CS',
    3: 'CH',
    4: 'HS',
}


def get_part(lst, idx, length):
    left = idx
    right = left + length
    return lst[left:right]


class Packet:
    def __init__(self, data):
        self.data = data
        self.header = self.get_header()
        self.name_len = self.get_name_len()
        self.name = self.get_name()
        self.type = self.get_type()
        self.class_ = self.get_class()

    @property
    def header_data(self):
        return self.data[:12]

    @property
    def body_data(self):
        return self.data[12:]

    def get_header(self):
        return struct.unpack('!HHHHHH', self.header_data)

    def get_name_len(self):
        non_zero = takewhile(lambda x: x != 0, self.body_data)
        return len(list(non_zero)) + 1

    def get_name(self):
        name = self.body_data[:self.name_len]
        return struct.unpack('%ds' % self.name_len, name)[0]

    def get_type(self):
        data_part = self._get_body_part(self.name_len, 2)
        query_type = struct.unpack('!H', data_part)[0]
        return TYPES.get(query_type, 'A')

    def get_class(self):
        data_part = self._get_body_part(self.name_len + 2, 2)
        query_class = struct.unpack('!H', data_part)[0]
        return CLASSES.get(query_class, 'IN')

    def set_id(self, id_):
        reply_id = struct.pack("!H", id_)
        self.data = reply_id + self.data[2:]

    def _get_body_part(self, idx, length):
        return get_part(self.body_data, idx, length)


class AnswerInfo:
    def __init__(self, data):
        self._data = data
        self.type_offset = self._get_name_len()
        self.class_offset = self.type_offset + 2
        self.ttl_offset = self.class_offset + 2
        self.rdlen_offset = self.ttl_offset + 4
        self.rdata_offset = self.rdlen_offset + 2
        self.rdata_len = self._get_rlen()

    @property
    def total_len(self):
        return self.rdata_offset + self.rdata_len

    @property
    def ttl(self):
        data_part = self._data[self.ttl_offset:self.rdlen_offset]
        return struct.unpack('!I', data_part)[0]

    def _get_name_len(self):
        if self._data[0] == b'\xc0':
            return 2
        return len(list(takewhile(lambda x: x != 0, self._data)))

    def _get_rlen(self):
        data_part = self._data[self.rdlen_offset:self.rdata_offset]
        return struct.unpack('!H', data_part)[0]


class AnswerPacket(Packet):
    def __init__(self, data):
        super().__init__(data)
        self.answers_info = self.get_answers_info()
        self.ttl = self.get_min_ttl()

    @property
    def answers_data(self):
        return self.body_data[self.name_len + 2 + 2:]

    def get_answers_info(self):
        answers = []
        idx = 0
        for i in range(self.header[3]):
            ans = AnswerInfo(self.answers_data[idx:])
            answers.append(ans)
            idx += ans.total_len
        return answers

    def get_min_ttl(self):
        if not self.answers_info:
            return -1
        return min(ans.ttl for ans in self.answers_info)

    def set_ttl(self, cache_time):
        idx = 0
        for ans in self.answers_info:
            new_ttl = int(ans.ttl - time.time() + cache_time)
            new_ttl = struct.pack('!I', new_ttl)

            left = ans.ttl_offset
            right = ans.rdlen_offset
            self.data = self.data[:left] + new_ttl + self.data[right:]

            idx += ans.total_len

    def _get_ans_part(self, idx, length):
        return get_part(self.answers_data, idx, length)
