"""Independent numeric kernels for the pinned Stringmol VM replay.

MT uses the upstream 69069 seeding recurrence, NOT Python's random seeding.
Alignment retains binary32 stores, strict comparisons and first-maximum ties.
"""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import struct

from experiments.stringmol.analyze_conservation import ALPHABET
from experiments.stringmol.analyze_lineage import require

_FLOAT = struct.Struct('=f')


def f32(value: float) -> float:
    return float(_FLOAT.unpack(_FLOAT.pack(value))[0])


class MT:
    def __init__(self, seed: int):
        require(type(seed) is int and 0 <= seed < 2**32, 'MT seed bounds')
        self.words = [seed]
        for _ in range(623):
            self.words.append((69069 * self.words[-1]) & 0xffffffff)
        self.cursor = 624
        self.draws = 0

    def uniform(self) -> float:
        if self.cursor == 624:
            for i in range(624):
                y = (self.words[i] & 0x80000000) | (self.words[(i+1) % 624] & 0x7fffffff)
                self.words[i] = self.words[(i+397) % 624] ^ (y >> 1) ^ (0x9908b0df if y & 1 else 0)
            self.cursor = 0
        y = self.words[self.cursor]
        self.cursor += 1
        self.draws += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9d2c5680
        y ^= (y << 15) & 0xefc60000
        y ^= y >> 18
        return y * 2**-32

    def rank(self, count: int) -> int:
        require(count > 0, 'sampling empty set')
        return int(count * self.uniform())

    def encoded(self) -> str:
        return f'MTI {self.cursor}\n' + ''.join(f'{word}\n' for word in self.words)


def complement(value: bytes) -> bytes:
    return bytes(65 + (x - 65 + 13) % 26 if 65 <= x <= 90 else x for x in value)


@dataclass(frozen=True)
class Alignment:
    s1: int
    e1: int
    s2: int
    e2: int
    score: float
    match: int

    @property
    def length(self) -> int:
        return min(self.e1-self.s1, self.e2-self.s2)

    def probability(self, binding: bool) -> float:
        length = self.length
        if binding and length <= 2:
            return 0.0
        bound = length - 1.124
        score = self.score if self.score < bound else f32(bound)
        return f32(score / bound)


class Matrix:
    def __init__(self, path: Path):
        lines = path.read_text(encoding='ascii').splitlines()
        require(lines[0] == ALPHABET and len(lines) == 2 * len(ALPHABET) + 2, 'alignment matrix dimensions/alphabet')
        self.index = {value: i for i, value in enumerate(ALPHABET.encode())}
        self.weights = tuple(tuple(f32(float(x)) for x in line.split()) for line in lines[1:35])
        require(all(len(row) == 33 for row in self.weights), 'alignment row dimensions')

    @lru_cache(maxsize=4096)
    def align(self, left: bytes, right: bytes) -> Alignment:
        # Upstream leaves its output indeterminate on empty input. Do not invent
        # a successful alignment for an execution that cannot be reconstructed.
        require(bool(left) and bool(right) and b'\0' not in left+right, 'empty/nonvisible alignment input')
        a = [self.index[x] for x in left]
        b = [self.index[x] for x in right]
        trace = [bytearray(len(b)+1) for _ in range(len(a)+1)]
        previous = [0.0] * (len(b)+1)
        maximum = 0.0
        end_i = end_j = 0
        gaps = self.weights[33]
        for i, x in enumerate(a, 1):
            current = [0.0] * (len(b)+1)
            for j, y in enumerate(b, 1):
                best = 0.0
                direction = 0
                for choice, candidate in enumerate((f32(previous[j-1]+self.weights[x][y]),
                                                     f32(previous[j]+gaps[x]), f32(current[j-1]+gaps[y])), 1):
                    if candidate > best:
                        best, direction = candidate, choice
                current[j] = best
                trace[i][j] = direction
                if best > maximum:
                    maximum, end_i, end_j = best, i, j
            previous = current
        i, j, matches = end_i, end_j, 0
        while trace[i][j]:
            direction = trace[i][j]
            if direction == 1:
                matches += 1
            if direction != 3:
                i -= 1
            if direction != 2:
                j -= 1
        return Alignment(i, end_i, j, end_j, maximum, matches)
