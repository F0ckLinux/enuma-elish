import os
import json
import random
import time

DEBUG = False


DEBUG_BASE = {"server": "localhost", "server_port": 12000, "password": "123", "method": "aes-256-cfb", "local_port": "12020"}
DEBUG_BASE2 = {"server": "localhost", "server_port": 12001, "password": "123", "method": "aes-256-cfb", "local_port": "12021"}


class Book:
    _book = {}
    _no = []
    _if_init = False

    def __init__(self, ss_dir= '/etc/shadowsocks', interval=30):
        self.ss_dir = ss_dir
        self.last_time = time.time()
        self.interval = interval
        
        if not os.path.exists(ss_dir):
            os.mkdir(ss_dir)

        if not self._if_init:
            self.refresh()
            Book._if_init = True
    
    def refresh(self):
        if DEBUG:
            book = {
                0:DEBUG_BASE,
                1:DEBUG_BASE2,
            }
            no = []

        else:
            files = os.listdir(self.ss_dir)
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

    def if_jump(self, res):
        i = 1
        try:
            i = float(res)    
        except Exception as e:
            i = 0
        
        if random.random() > i:
            return True
        return False

        

    def get_server(self):
        now_time = time.time()
        if  now_time - self.last_time > self.interval:
            self.refresh()
            self.last_time = time.time()
        n = random.choice(Book._no)
        if n in Book._book:
           return Book._book[n]
        return None


