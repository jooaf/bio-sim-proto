"""Independent zero-mutation Stringmol head-state interpreter.

No native VM snapshots or claimed flow heads initialize this model. Binding
alignment initializes all heads; subsequent instructions reconstruct them.
"""
from dataclasses import dataclass
import math

from experiments.stringmol.admission_numeric import Alignment, Matrix, MT, complement, f32
from experiments.stringmol.analyze_conservation import ALPHABET, MAXL0
from experiments.stringmol.analyze_lineage import require


@dataclass(frozen=True)
class Effect:
    opcode: int
    buffers: dict[int, bytes]
    copy_outcome: str | None = None
    flow: tuple[int, int] | None = None
    proposal: bool = False
    unbind: bool = False


class VM:
    def __init__(self, first: int, second: int, alignment: Alignment):
        if alignment.s1 >= alignment.s2:
            self.active, self.passive = first, second
            active_offset, passive_offset = alignment.s1, alignment.s2
        else:
            self.active, self.passive = second, first
            active_offset, passive_offset = alignment.s2, alignment.s1
        self.heads = {kind: [passive_offset, active_offset] for kind in 'irwf'}
        self.toggles = dict.fromkeys('irwf', 1)

    def address(self, kind: str) -> tuple[int, int]:
        toggle = self.toggles[kind]
        return (self.active if toggle else self.passive), self.heads[kind][toggle]

    def increment(self, kind: str) -> None:
        self.heads[kind][self.toggles[kind]] += 1

    def instruction(self, buffers: dict[int, bytes], pool: list[int], rng: MT, matrix: Matrix,
                    *, granular: bool = False) -> Effect:
        pair = {idx: buffers[idx] for idx in (self.active, self.passive)}
        owner, ip = self.address('i')
        require(0 <= ip < MAXL0, 'VM instruction bounds')
        opcode = pair[owner][ip]
        if opcode in (0, ord('}')):
            return Effect(opcode, pair, unbind=True)
        require(ip+1 < MAXL0, 'VM instruction argument bounds')
        argument = pair[owner][ip+1]
        if opcode == ord('>'):
            target = {ord('B'): 'r', ord('C'): 'w'}.get(argument, 'i')
            self.toggles[target] = self.toggles['f']
            self.heads[target][self.toggles[target]] = self.heads['f'][self.toggles['f']]
        elif opcode == ord('^'):
            target = {ord('A'): 'i', ord('B'): 'r', ord('C'): 'w'}.get(argument, 'f')
            self.toggles[target] = 1-self.toggles[target]
        elif opcode == ord('+'):
            if granular:
                self.increment({ord('A'): 'i', ord('B'): 'r', ord('C'): 'w'}.get(argument, 'f'))
        elif opcode in (ord('$'), ord('?')):
            end = ip+1
            while end < MAXL0 and 65 <= pair[owner][end] <= 90:
                end += 1
            require(end < MAXL0, 'unterminated VM template')
            label = pair[owner][ip+1:end]
            length = len(label)
            if opcode == ord('$'):
                target = 'f'
                if length:
                    flow_owner, _ = self.address('f')
                    match = matrix.align(complement(label), pair[flow_owner].split(b'\0', 1)[0])
                    accepted = f32(rng.uniform()) < match.probability(binding=False)
                else:
                    accepted = False
                if accepted:
                    self.heads[target][self.toggles[target]] = match.e2
                else:
                    self.toggles[target] = self.toggles['i']
                    self.heads[target][self.toggles[target]] = ip+length
            else:
                read_owner, offset = self.address('r')
                require(0 <= offset < MAXL0, 'VM conditional read bounds')
                if length <= 1:
                    skip = pair[read_owner][offset] == 0
                else:
                    # strncpy stops at the reserved NUL and pads; its requested
                    # length need not fit after the read pointer in the source.
                    match = matrix.align(complement(label), pair[read_owner][offset:offset+length].split(b'\0', 1)[0])
                    probability = f32(math.pow(f32(match.score/length), length))
                    skip = f32(rng.uniform()) < probability
                self.heads['i'][self.toggles['i']] = ip+1+length+int(skip)
                return Effect(opcode, pair)
        elif opcode == ord('='):
            read_owner, read = self.address('r')
            write_owner, write = self.address('w')
            if not (0 <= read < MAXL0-1 and 0 <= write < MAXL0-1):
                return Effect(opcode, pair, copy_outcome='BOUNDARY', unbind=True)
            value = pair[read_owner][read]
            if value == 0:
                outcome = 'READ_NULL'
            else:
                rng.uniform()  # Native copy draws even at exactly zero mutation.
                previous = pair[write_owner][write]
                outcome = 'NOOP' if previous == value else 'ACCEPTED' if pool[ALPHABET.index(chr(value))] > 0 else 'BLOCKED'
                if outcome == 'ACCEPTED':
                    changed = bytearray(pair[write_owner]); changed[write] = value
                    pair[write_owner] = bytes(changed)
                if not granular:
                    self.increment('w'); self.increment('r')
            self.increment('i')
            return Effect(opcode, pair, copy_outcome=outcome)
        elif opcode == ord('%'):
            flow = self.address('f')
            source, offset = flow
            require(0 <= offset < MAXL0, 'VM flow bounds')
            proposal = offset < len(pair[source].split(b'\0', 1)[0])
            self.increment('i')
            return Effect(opcode, pair, flow=flow, proposal=proposal)
        self.increment('i')
        return Effect(opcode, pair)
