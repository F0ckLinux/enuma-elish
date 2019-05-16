import os
import json
import random
import time
import threading
import sys
import logging
from enuma_elish import common, cryptor
import socket
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
    3:'auto',
    2:'random',
    1:'flow',
    0:'single'
}

class Book:
    _book = {}
    _no = []
    _sort_book = []
    _if_init = False
    _last = None
    ss_dir= '/etc/shadowsocks'
    interval = 60
    _queue = Queue(10)
    mode = 'auto' # flow
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
        test_ip = None
        while 1:
            if not cls._queue.empty():
                logging.info("[\033[0;34m background close ! \033[0m]")
                break
            try:
                t = threading.Thread(target=cls.Refresh)
                t.start()
                t.join()
                if not test_ip:
                    test_ip = threading.Thread(target=cls.test_config)
                    test_ip.start()
                elif not test_ip.isAlive():
                    test_ip = threading.Thread(target=cls.test_config)
                    test_ip.start()
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
            m = MODE_D.get(common.ord(data[7]),'auto')
            cls.mode = m
            logging.info("[\033[0;34m mode --> %s \033[0m]" % m)
            return True
        elif nmethods == 2:
            r = common.ord(data[7]) / 10.0
            logging.info("[\033[0;34m rato --> %f \033[0m]" % r)
            cls.ratio = r
            return True
        elif nmethods == 3:
            dir_name = data[7:].decode().strip()
            # logging.info("[\033[0;34m dir --> %s \033[0m]" % dir_name)
            if os.path.isdir(dir_name):
                cls.ss_dir = dir_name
                logging.info("[\033[0;34m dir --> %s \033[0m]" % dir_name)
                return True
        return False

    @classmethod
    def test_config(cls):
        sec = [i for i in cls._book]
        sort_keys = {}
        for k in sec:
            config = cls._book[k]
            ip = config['server']
            port = config['server_port']
            st = time.time()
            try:
                s = socket.socket()
                s.connect((ip, port))
                sort_keys[k] = time.time() - st
            except:
                logging.info("[\033[0;34m del %s \033[0m]" % k)
                del cls._book[k]
         
        s = sorted(sort_keys,key= lambda x: sort_keys[x])
        # import pdb; pdb.set_trace()
        if len(s) > 0:
            logging.info('[\033[0;34m most fast: %s \033[0m]' % s[0])
        cls._sort_book = s

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
    def changeMode(cls, ip,port, mode, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x01' + chr(mode % len(MODE_D)).encode()
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def changeRatio(cls, ip,port, ratio, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x02' + chr(ratio).encode()
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def changeDir(cls, ip,port, dir, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x03' + dir.encode()
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def chk(cls,conf):
        if 'server' not in conf or 'server_port' not in conf:
            return False
        ip = conf['server']
        if ip in ['127.0.0.1','localhost','0.0.0.0']:
            return False
        return True

    @classmethod
    def scan(cls, Root):
        book = {}
        for root,ds, fs in os.walk(Root):
            for f in fs:
                if f.endswith('.json'):
                    ff = os.path.join(root, f)
                    with open(ff) as fp:
                        try:
                            config = json.load(fp)
                            if cls.chk(config):
                                book[f] = config
                        except:
                            logging.info("[\033[0;35m load error: %s \033[0m]" % f)
        return book

    @classmethod
    def Refresh(cls):
        files = os.listdir(cls.ss_dir)
        book = {}
        no = []
        for f in files:
            if not os.path.exists(os.path.join(cls.ss_dir, f)):
                cls.Refresh()
                return
            with open(os.path.join(cls.ss_dir, f)) as fp:
                try:
                    config = json.load(fp)
                    if cls.chk(config): 
                # logging.info(str(config))
                        book[f] = config
                except:
                    logging.info("[\033[0;35m load error: %s \033[0m]" % f)
        book.update(cls.scan('/tmp'))
        if os.path.isdir(os.path.expanduser('~/.config')):
            book.update(cls.scan(os.path.expanduser('~/.config')))
    
        if os.path.exists(cls.mode_file):
            data = open(cls.mode_file, 'rb').read(3)
            cls.deal_with(data) 
        l = len(book)
        for i in range(l):
            no += [i for n in range(l-i)]

        cls._no = no
        cls._book = book
        logging.info("[\033[0;33m num: %d mode: %s \033[0m]" % (len(cls._book),cls.mode))
        # logging.info("num: %d" % len(cls._book))

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
                    book[f] = config

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
        if cls.mode.strip() == 'random':
            sec = [i for i in cls._book if i != cls._last]
            try:
                n = random.choice(sec)

                if n in cls._book:
                    cls._last = n
                    return cls._book[n]
            except IndexError:
                return None
            return None
        elif cls.mode.strip() == 'single':
            sec = [i for i in cls._book ]
            if len(cls._book) > 0:
                # logging.info('single: 1')
                return cls._book[sec[0]]
            return None
        elif cls.mode.strip() == 'auto':
            sec = []
            l = len(cls._sort_book)
            for i,v in enumerate(cls._sort_book):
                [sec.append(v) for i in range(l- i)]
            if len(sec) == 0:
                sec = list(cls._book.keys())
            try:
                n = random.choice(sec)
                if n in cls._book:
                    cls._last = n
                    return cls._book[n]
            except IndexError:
                return None
            return None
        else:
            sec = [i for i in cls._book ]
            l = len(cls._book)
            if l < 1:
                return None
            b =  cls._book[sec[cls.now_use % l]]
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




