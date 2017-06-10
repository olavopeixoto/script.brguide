# -*- coding: utf-8 -*-

import threading


class Thread(threading.Thread):
    def __init__(self, target, list, *args):
        self._target = target
        self._args = args
        self.list = list
        threading.Thread.__init__(self)
    def run(self):
        self.list += self._target(*self._args)