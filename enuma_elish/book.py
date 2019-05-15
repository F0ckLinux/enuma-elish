import os
import json
import random
import time
import threading
import sys
import logging
from enuma_elish import common, cryptor

if sys.version[0] == '3':
    from queue import Queue
else:
    from Queue import Queue
DEBUG = False


DEBUG_BASE = {"server": "localhost", "server_port": 12000, "password": "123", "method": "aes-256-cfb", "local_port": "12020"}
DEBUG_BASE2 = {"server": "localhost", "server_port": 12001, "password": "123", "method": "aes-256-cfb", "local_port": "12021"}

# BOOK PROTOCOL: \x09

# METHOD : 
#   change mode: \x01
#   change random rato: \x02
# MODE single: \x00
#      flow: \x01
#      random: \x02



##  b'\x09\x01\x00'
MODE_D = {
    2:'random',
    1:'flow',
    0:'single'
}

class Book:
    _book = {}
    _no = []
    _if_init = False
    _last = None
    ss_dir= '/etc/shadowsocks'
    interval = 60
    _queue = Queue(10)
    mode = 'single' # flow
    now_use = 0
    is_back = False
    ratio = 0.3
    mode_file = os.path.join('/tmp/', os.urandom(8).hex())

    if not os.path.exists(ss_dir):
        os.mkdir(ss_dir)
    def __init__(self, ss_dir=None, interval=None):
        if ss_dir != self.ss_dir:
            self.ss_dir = ss_dir
            if not os.path.exists(ss_dir):
                os.mkdir(ss_dir)
        self.last_time = time.time()
        
        if interval:
            self.interval = interval
        self._last_use = None
        

        if not self._if_init:
            self.refresh()
            Book._if_init = True
    
    @classmethod
    def schedule_refresh(cls):
        t = None
        while 1:
            if not cls._queue.empty():
                logging.info("[\033[0;34m background close ! \033[0m]")
                break
            try:
                t = threading.Thread(target=cls.Refresh)
                t.start()
                # t.join(10)
            except:
                pass    
            logging.info("[\033[0;34m Refresh Book \033[0m]")
            time.sleep(cls.interval)

    @classmethod
    def Background(cls):
        if not cls.is_back:
            threading.Thread(target=cls.schedule_refresh).start()
            cls.is_back = True
            logging.info("[\033[0;34m background for a scheduler which one ouput config from book!\033[0m]")
    
    @classmethod
    def deal_with(cls, data):
        socks_version = common.ord(data[0])
        nmethods = common.ord(data[6])
        if nmethods == 1:
            m = MODE_D.get(common.ord(data[7]),'single')
            cls.mode = m
            logging.info("[\033[0;34m mode --> %s \033[0m]" % m)
        elif nmethods == 2:
            r = common.ord(data[7]) / 10.0
            logging.info("[\033[0;34m rato --> %f \033[0m]" % r)
            cls.ratio = r

    @classmethod
    def close(cls):
        cls._queue.put("close")

    @classmethod
    def SendCode(cls,ip,port, data, password, method='aes-256-cfb', openssl=None, mbedtls=None, sodium=None):
        crypto_path = {
            'openssl':openssl,
            'mbedtls':mbedtls,
            'sodium':sodium
        }
        c = cryptor.Cryptor(password,method,crypto_path)
        en_data = c.encrypt(data)
        try:
            s = socket.socket()
            s.connect((ip, port))
            s.sendall(en_data)
            data = s.recv(1024)
            return data
        except:
            return b'failed'

    @classmethod
    def Refresh(cls):
        files = os.listdir(cls.ss_dir)
        book = {}
        no = []
        for f in files:
            with open(os.path.join(cls.ss_dir, f)) as fp:
                config = json.load(fp)
                book[int(f.split(".")[0])] = config
        if os.path.exists(cls.mode_file):
            data = open(cls.mode_file, 'rb').read(3)
            cls.deal_with(data) 
        l = len(book)
        for i in range(l):
            no += [i for n in range(l-i)]

        cls._no = no
        cls._book = book

    def refresh(self):
        if DEBUG:
            book = {
                0:DEBUG_BASE,
                1:DEBUG_BASE2,
            }
            no = []

        else:
            files = os.listdir(self.__class__.ss_dir)
            book = {}
            no = []
            for f in files:
                with open(os.path.join(self.ss_dir, f)) as fp:
                    config = json.load(fp)
                    book[int(f.split(".")[0])] = config

        l = len(book)
        for i in range(l):
            no += [i for n in range(l-i)]

        Book._no = no
        Book._book = book

    def if_jump(self, res=0.3):
        i = 1
        try:
            i = float(res)    
        except:
            i = 0
        
        if random.random() > i:
            return True
        return False
    


    @classmethod
    def GetServer(cls, rato=0.3):
        if cls.mode == 'random':
            sec = [i for i in cls._no if i != cls._last]
            try:
                n = random.choice(sec)

                if n in cls._book:
                    cls._last = n
                    return cls._book[n]
            except IndexError:
                return None
            return None
        elif cls.mode == 'single':
            if len(cls._book) > 0:
                return cls._book[0]
            return None
        else:
            l = len(cls._book)
            if l < 1:
                return None
            b =  cls._book[cls.now_use % l]
            cls.now_use = (cls.now_use + 1) % l
            return b


    def get_server(self, rato=0.3):
        # now_time = time.time()
        # if  now_time - self.last_time > self.interval:
        #     self.refresh()
        #     self.last_time = time.time()
        if self.__class__.mode == 'random':
            sec = [i for i in Book._no if i != Book._last]
            try:
                n = random.choice(sec)

                if n in Book._book:
                    Book._last = n
                    return Book._book[n]
            except IndexError:
                return None
            return None
        elif self.__class__.mode == 'single':
            if len(Book._book) > 0:
                return Book._book[0]
            return None
        else:
            l = len(Book._book)
            if l < 1:
                return None
            b =  Book._book[Book.now_use % l]
            Book.now_use = (Book.now_use + 1) % l
            return b




