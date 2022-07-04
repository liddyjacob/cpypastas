from cmath import inf
from lib2to3.pgen2.token import NAME
from statistics import mean
import time
from tkinter import N

class Profiling:
    def __init__(self):
        self.mins = {}
        self.maxs = {}
        self.means = {}
        self.lengths = {}
        self.starttimes = {}
        self.sums = {}
        self.names = set()
        self.is_on = False
        self.time_spent = 0.0

    def on(self):
        self.is_on = True

    def off(self):
        self.is_on = False

    def profileStart(self, name):
        start = time.time()
        if not self.is_on: return
        if name not in self.names:
            self.mins[name] = inf
            self.maxs[name] = 0
            self.means[name] = 0
            self.lengths[name] = 0
            self.sums[name] = 0
            self.names.add(name)

        self.starttimes[name] = time.time()
        self.time_spent += time.time() - start

    def profileEnd(self, name):
        start = time.time()

        if not self.is_on: return
        nt = time.time() - self.starttimes[name]
        if nt < self.mins[name]:
            self.mins[name] = nt
        if nt > self.maxs[name]:
            self.maxs[name] = nt

        self.lengths[name] += 1
        
        if self.means[name] == 0:
            self.means[name] = nt
        else:
            self.means[name] = ((self.lengths[name] - 1) * self.means[name])/self.lengths[name] + nt/self.lengths[name]

        self.sums[name] += nt
        self.time_spent += time.time() - start

    def profilePrint(self, which=None):
        if not self.is_on: return
        print("PROFILING:")
        for name in self.names:
            if which is not None:
                if name not in which:
                    next
            print(f"Name: {name}({self.lengths[name]})")
            print(f"\tTotal/Avg: {self.sums[name]:.3}/{self.means[name]:.3}")
            print(f"\tMin/Max: {self.mins[name]:.3}/{self.maxs[name]:.3}")

        print(f"TIME WASTED IN PROFILER: {self.time_spent:.3}")

    def profileReset(self):
        self.mins = {}
        self.maxs = {}
        self.means = {}
        self.lengths = {}
        self.starttimes = {}
        self.sums = {}
        self.names = set()
        self.is_on = False
        self.time_spent = 0.0


        
        

PROFILER = Profiling()