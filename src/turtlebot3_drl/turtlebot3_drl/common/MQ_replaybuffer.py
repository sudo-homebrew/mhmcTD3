import numpy as np
import random
from collections import deque
import itertools


class ReplayBuffer:
    def __init__(self, size):
        self.buffer = deque(maxlen=size)
        self.max_size = size

    def sample(self, batchsize):
        batch = []
        batchsize = min(batchsize, self.get_length())
        batch = random.sample(self.buffer, batchsize)
        s_array = np.float32([array[0] for array in batch])
        a_array = np.float32([array[1] for array in batch])
        r_array = np.float32([array[2] for array in batch])
        new_s_array = np.float32([array[3] for array in batch])
        done_array = np.float32([array[4] for array in batch])
        m_array = np.float32([array[5] for array in batch])
        new_m_array = np.float32([array[6] for array in batch])

        return s_array, a_array, r_array, new_s_array, done_array, m_array, new_m_array

    def get_length(self):
        return len(self.buffer)

    def add_sample(self, m, s, a, r, new_s, new_m, done):
        transition = (s, a, r, new_s, done, m, new_m)
        self.buffer.append(transition)
