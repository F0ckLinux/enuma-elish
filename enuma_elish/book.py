import os
import json
import random
import time
import threading
import sys
import logging
from enuma_elish import common, cryptor
import socket
from base64 import b64decode, b64encode
from time import strftime, gmtime
PY=3
if sys.version[0] == '3':
    from queue import Queue
else:
    PY=2
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

def L_info(msg):
    logging.info("[\033[0;35m %s \033[0m]" % msg)

def byteify(input, encoding='utf-8'):
    if isinstance(input, dict):
        return {byteify(key): byteify(value) for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode(encoding)
    else:
        return input

class Responde:
    E = b'HTTP/1.1 404 Not Found\r\nConnection: keep-alive\r\nContent-Length: 0\r\nDate: %s\r\nServer: nginx/1.8.1\r\nSet-Cookie: SESSION=1b845adb-2405-42f5-9dd3-4030d767b593; Path=/; HttpOnly'
    H = b'HTTP/1.1 200 ok\r\nConnection: keep-alive\r\nContent-Length: %d\r\nDate: %s\r\nServer: nginx/1.8.1\r\nSet-Cookie: SESSION=1b845adb-2405-42f5-9dd3-4030d767b593%s; Path=/; HttpOnly\r\n\r\n'


    @classmethod
    def base(cls, content='',en=False):
        e_tag = b''
        if en:
            e_tag = b'SecD'

        T = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
        if isinstance(content, str):
            content = content.encode()
        if en:
            content = en.encrypt(content)
        return cls.H % (len(content), T.encode(), e_tag) + content 


    @classmethod
    def no(cls):
        return cls.E % strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) 

    @classmethod
    def ok(cls):
        return cls.base('Ich liebe dich!')

    @classmethod
    def json(cls, kargs, encryptor):
        if isinstance(kargs, dict):
            return cls.base(json.dumps(kargs), en=encryptor)
        return cls.ok()

class Book:
    _book = {}
    _no = []
    _sort_book = []
    _if_init = False
    _last = None
    _err = []
    ss_dir= '/etc/shadowsocks'
    interval = 60
    _queue = Queue(10)
    mode = 'auto' # flow
    now_use = 0
    is_back = False
    ratio = 0.3
    

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
            t_daemon = threading.Thread(target=cls.schedule_refresh)
            t_daemon.daemon = True
            t_daemon.start()
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
        elif nmethods == 4:
            data = data[7:].decode().strip()
            if data.startswith('ss://'):
                data = data.replace("ss://",'').split("#")[0]
                if PY == 3:
                    data = data.encode()
                c = b64decode(data)
                if PY == 3:
                    c = c.decode()
                method,pwdip,s_port = c.split(":")
                pwd,ip = pwdip.split("@")
                cls._book = {}
                cls._sort_book = []
                cls._book[ip] = {
                    'server': ip,
                    'server_port':s_port,
                    'method': method,
                    'password':pwd
                }

                logging.info("[\033[0;34m ss --> %s \033[0m]" % c)
                return True
        elif nmethods == 5:
            data = data[7:].decode().strip()
            if data.startswith('ss://'):
                data = data.replace("ss://",'').split("#")[0]
                if PY == 3:
                    data = data.encode()
                c = b64decode(data)
                if PY == 3:
                    c = c.decode()
                method,pwdip,s_port = c.split(":")
                pwd,ip = pwdip.split("@")
                # cls._book = {}
                # cls._sort_book = []
                cls._book[ip] = {
                    'server': ip,
                    'server_port':s_port,
                    'method': method,
                    'password':pwd
                }

                logging.info("[\033[0;34m + %s \033[0m]" % c)
                return True
        elif nmethods == 6:
            data = data[7:].decode().strip()
            if data == "check":
                L_info("check routes")
                return {
                    'routes':list(cls._book.values()),
                    'interval':cls.interval,
                    'jump-ratio':cls.ratio,
                    'sort_keys': cls._sort_book,
                    'mode':cls.mode,
                }
            elif data.startswith('set-interval'):
                data = int(data[len('set-interval'):].strip())
                cls.interval = data
                L_info("set-interval : %d " % data)
                return "set-interval : %d" % data
            elif data.startswith('jump-ratio'):
                data = float(data[len('jump-ratio'):].strip())
                cls.ratio = data
                L_info('jump-ratio: %f%%' % ((1-data) * 100))
                return 'jump-ratio: %f%%' % ((1-data) * 100)
                
                
        return False

    @classmethod
    def test_config(cls):
        sec = [i for i in cls._book]
        sort_keys = {}
        slow_t = 0
        for k in sec:
            config = cls._book[k]
            ip = config['server']
            port = config['server_port']
            st = time.time()
            try:
                s = socket.socket()
                s.connect((ip, int(port)))
                et = time.time() - st
                if et > slow_t:
                    slow_t = et
                if ip in cls._err:
                    et += (slow_t//2)
                sort_keys[k] = et
            except Exception as e:
                if k in cls._book:
                    logging.info("[\033[0;34m del %s \033[0m]" % k)
                    del cls._book[k]
         
        s = sorted(sort_keys,key= lambda x: sort_keys[x])
        # import pdb; pdb.set_trace()
        if len(s) > 0:
            logging.info('[\033[0;34m most fast: %s num: %d \033[0m]' % (s[0], len(cls._book)))
        cls._sort_book = s

    @classmethod
    def close(cls):
        cls._queue.put("close")

    @classmethod
    def ss(cls, conf):
        if os.path.exists(conf):
            with open(conf) as fp:
                try:
                    con = json.load(fp)
                    if 'server_port' in con and 'password' in con:
                        return 'ss://' + b64encode(':'.join([con['method'],con['password']+ '@' + con['server'],con['server_port']]).encode()).decode()
                except:
                    return ''

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
            data = s.recv(31024)
            tag = 'SecD'
            if PY == 3:
                tag = b'SecD'

            if tag in data:
                data = data.split(b"\r\n\r\n",1)[1]
                return c.decrypt(data)
            return data
        except Exception as e:
            logging.error(e)
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
    def linkOther(cls, ip,port, ss_str, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x04' + ss_str.encode()
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def addRoute(cls, ip,port, ss_str, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x05' + ss_str.encode()
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def checkRoutes(cls, ip,port, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x06check'
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def refreshTime(cls, ip,port, time, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x06set-interval' + str(time).encode()
        return cls.SendCode(ip, port, data, password, method=method, **opts)

    @classmethod
    def jumpRatio(cls, ip,port, ratio, password, method='aes-256-cfb',**opts):
        data = b'\x09' + 'enuma'.encode('utf-8') + b'\x06jump-ratio' + str(ratio).encode()
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
                            if PY == 2:
                                config = byteify(config)
                            if cls.chk(config):
                                book[f] = config
                        except Exception as e:
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
                    if PY == 2:
                        config = byteify(config)

                    if cls.chk(config): 
                # logging.info(str(config))
                        book[f] = config
                except:
                    logging.info("[\033[0;35m load error: %s \033[0m]" % f)
        book.update(cls.scan('/tmp'))
        if os.path.isdir(os.path.expanduser('~/.config')):
            book.update(cls.scan(os.path.expanduser('~/.config')))
    
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
    def GetServer(cls):
        rato=cls.ratio
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
            sec = [i.decode() if PY ==2 else i for i in cls._book ]
            if len(cls._book) > 0:
                # logging.info('single: 1')
                return cls._book[sec[0]]
            return None
        elif cls.mode.strip() == 'auto':
            sec = []
            l = len(cls._sort_book)
            for i,v in enumerate(cls._sort_book):
                if PY == 2:
                    [sec.append(v.decode()) for i in range(l- i)]
                else:
                    [sec.append(v) for i in range(l- i)]
            if len(sec) == 0:
                sec = [i.decode() if PY ==2 else i for i in cls._book ]
            try:
                n = random.choice(sec)
                if n in cls._book:
                    cls._last = n
                    return cls._book[n]
            except IndexError:
                L_info("may be no book: %d " % len(cls._book))
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




