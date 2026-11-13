"""Joined SM-B003 history reconstruction from sealed inputs, not BEGIN claims.

Independent Python MT, alignment and VM heads drive selection and proposal
bijections. Frozen B002 code is imported only for historical schema/helpers.
"""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.stringmol import admission_design as design, admission_journal as journal
from experiments.stringmol import admission_material as material, analyze_conservation as c
from experiments.stringmol import retirement_material as old_material
from experiments.stringmol.admission_boundary import BoundaryReplay
from experiments.stringmol.admission_numeric import MT, Matrix, complement, f32
from experiments.stringmol.admission_vm import VM, Effect
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS, require
from experiments.stringmol.analyze_retirement import SOURCE_COLUMNS
from experiments.stringmol.analyze_scheduling import COLUMNS as BOUNDARY_COLUMNS


VM_COLUMNS = ['tick', 'id', 'role', 'partner', 'eligible_tick', 'x', 'y',
              'it', 'rt', 'wt', 'ft', 'i0', 'i1', 'r0', 'r1', 'w0', 'w1', 'f0', 'f1']


@dataclass
class Pending:
    effect: Effect
    start: int
    active: int
    passive: int
    before: material.Replay | None = None
    state: journal.SelectionState | None = None
    begin: journal.Row | None = None
    resolved: journal.Row | None = None
    plan: design.Plan | None = None


def replay(directory: Path, initial: dict[str, Any], coordinates: dict[int, tuple[int, int]],
           header: journal.Header, seed: int, matrix_path: Path, *, decay: float,
           report_every: int = 100, exit_status: int = 0, label: int = ord('Q')) -> dict[str, Any]:
    require(exit_status == 0, 'unsuccessful native execution')
    require(0 < header.horizon <= 5000 and report_every > 0, 'supported replay horizon/checkpoints')
    require(0 <= decay <= 1, 'replay decay probability')
    rng, matrix = MT(seed), Matrix(matrix_path)
    loaded = list(map(int, initial['buffers']))
    order = []
    while loaded:
        order.append(loaded.pop(rng.rank(len(loaded))))
    events = c.canonical_rows(directory / 'material_events002.csv', old_material.JOURNAL_COLUMNS)
    boundary = BoundaryReplay(initial, events, header.schedule.value, header.horizon, initial_order=order)
    admission = list(journal.read(directory / journal.NAME))
    structure = journal.audit_structure(admission, header)
    begins = {journal.number(row['boundary_index']): row for row in admission if row.event is journal.Event.BEGIN}
    resolves = {journal.number(row['transaction']): row for row in admission if row.event is journal.Event.RESOLVE}
    require(len(begins) == len(resolves) == structure.proposals, 'admission proposal bijection')
    grid = coordinates.copy()
    require(set(grid) == set(boundary.source.material.buffers) and len(set(grid.values())) == len(grid), 'initial grid identity/collision')
    require(all(0 <= x < header.width and 0 <= y < header.height for x, y in grid.values()), 'initial grid bounds')
    require(journal.ids(admission[0]['now_ids']) == tuple(order), 'admission initial RNG/list order')
    next_identity = max(grid, default=-1)+1
    registry: dict[bytes, int] = {}
    species: dict[int, int] = {}
    def species_for(buffer: bytes) -> int:
        sequence = buffer.split(b'\0', 1)[0]
        if sequence not in registry:
            registry[sequence] = len(registry)+1
        return registry[sequence]
    for idx, buffer in boundary.source.material.buffers.items():
        species[idx] = species_for(buffer)
    expected_lineage: list[dict[str, str]] = []
    expected_snapshots: list[dict[str, str]] = []
    expected_sources: list[dict[str, str]] = []
    def life(event: str, tick: int, idx: int, buffer: bytes, cell: tuple[int, int],
             active: int = -1, passive: int = -1, parents: dict[int, bytes] | None = None) -> None:
        row = dict.fromkeys(EVENT_COLUMNS, '-1')
        row.update(event=event, timestep=str(tick), child_id=str(idx), active_id=str(active), passive_id=str(passive),
                   child_species=str(species[idx]), child_label=str(label), x=str(cell[0]), y=str(cell[1]),
                   child_sequence_hex=buffer.split(b'\0', 1)[0].hex().upper(), active_sequence_hex='', passive_sequence_hex='')
        if parents is not None:
            for role, parent in (('active', active), ('passive', passive)):
                row[role+'_species'] = str(species[parent]); row[role+'_label'] = str(label)
                row[role+'_sequence_hex'] = parents[parent].split(b'\0', 1)[0].hex().upper()
        expected_lineage.append(row)
    for idx in order:
        life('INIT', 0, idx, boundary.source.material.buffers[idx], grid[idx])
    vms: dict[int, VM] = {}
    pending: Pending | None = None
    expected_decay: bool | None = None
    seen_begins: set[int] = set()
    source_eligible = 0
    aggregates = c.canonical_rows(directory / 'conservation002.csv', old_material.COLUMNS)
    buffer_rows = c.canonical_rows(directory / 'conservation_buffers002.csv', c.BUFFER_COLUMNS)
    checkpoint_index = buffer_index = 0
    def checkpoint(tick: int, event: str) -> None:
        nonlocal checkpoint_index, buffer_index
        require(checkpoint_index < len(aggregates), 'missing checkpoint')
        row = aggregates[checkpoint_index]; checkpoint_index += 1
        require(row['tick'] == str(tick) and row['event'] == event, 'checkpoint time/order')
        boundary.source.material.checkpoint(row)
        for idx, buffer in sorted(boundary.source.material.buffers.items()):
            require(buffer_index < len(buffer_rows), 'missing full-buffer checkpoint')
            observed = buffer_rows[buffer_index]; buffer_index += 1
            require(observed['tick'] == str(tick) and observed['event'] == event and observed['id'] == str(idx) and
                    c.full_buffer(observed['full_buffer_hex'], c.MAXL0) == buffer, 'checkpoint buffer identity/content')
            if event == 'CHECKPOINT':
                x, y = grid[idx]
                expected_snapshots.append(dict(tick=str(tick), id=str(idx), species=str(species[idx]), label=str(label),
                                               x=str(x), y=str(y), sequence_hex=buffer.split(b'\0', 1)[0].hex().upper()))
    rows = c.canonical_rows(directory / 'scheduling_events001.csv', BOUNDARY_COLUMNS)
    for row in rows:
        event, tick = row['event'], int(row['tick'])
        if event == 'TICK' and tick % report_every == 0:
            checkpoint(tick, 'CHECKPOINT')
        if event == 'SELECT':
            boundary.finish_selection()
            require(int(row['id']) == boundary.now[rng.rank(len(boundary.now))], 'independent top-level RNG selection')
            expected_decay = f32(rng.uniform()) < f32(decay)
        elif event in ('SURVIVE', 'DECAY'):
            require(expected_decay is not None and (event == 'DECAY') == expected_decay, 'independent decay RNG')
            expected_decay = None
        elif event == 'DEATH' and row['outcome'] == 'DECAY':
            require(expected_decay is True, 'death without independent decay')
        elif event == 'SEARCH':
            candidates = [i for i in boundary.now if i not in boundary.pairs and tick >= boundary.eligible_tick(i)]
            rank = rng.rank(len(candidates)) if candidates else -1
            require(int(row['selected']) == rank, 'independent partner RNG rank')
        elif event == 'ENCOUNTER':
            first, second = int(row['id']), int(row['other'])
            buffers = boundary.source.material.buffers
            match = matrix.align(complement(buffers[first].split(b'\0', 1)[0]), buffers[second].split(b'\0', 1)[0])
            bound = f32(rng.uniform()) < match.probability(binding=True)
            require(row['outcome'] == ('BOUND' if bound else 'UNBOUND'), 'independent binding alignment/RNG')
            if bound:
                vm = VM(first, second, match)
                require((int(row['active']), int(row['passive'])) == (vm.active, vm.passive), 'independent alignment roles')
                require(vm.active not in vms, 'VM already bound')
                vms[vm.active] = vm
        elif event == 'DISPATCH':
            active, passive = int(row['active']), int(row['passive'])
            require(pending is None and active in vms, 'missing/overlapping independent VM')
            vm = vms[active]
            require(vm.passive == passive and vm.address('i') == (int(row['owner']), int(row['offset'])), 'independent instruction head')
            before = boundary.source.material
            effect = vm.instruction(before.buffers, before.arrays['pool'], rng, matrix)
            require(effect.opcode == int(row['opcode']), 'independent opcode')
            pending = Pending(effect, boundary.cursor, active, passive)
            dispatch_index = int(row['index'])
            if effect.proposal:
                require(effect.flow is not None and dispatch_index in begins, 'nonempty VM proposal missing BEGIN')
                pending.before = deepcopy(before)
                begin = begins[dispatch_index]; seen_begins.add(dispatch_index)
                assert effect.flow is not None
                source, offset = effect.flow
                by_cell = {cell: idx for idx, cell in grid.items()}
                slots = []
                for x in range(header.width):
                    for y in range(header.height):
                        actor_id = by_cell.get((x, y))
                        actor = None if actor_id is None else design.Actor(actor_id, before.buffers[actor_id],
                            design.Role.ACTIVE if actor_id in boundary.active else design.Role.PASSIVE if actor_id in boundary.pairs else design.Role.UNBOUND,
                            boundary.pairs.get(actor_id), boundary.eligible_tick(actor_id))
                        slots.append(design.Slot(x, y, actor))
                state = journal.SelectionState(tuple(slots), tuple(boundary.now), tuple(boundary.next), active, passive, source,
                                               offset, next_identity, boundary.cursor, dispatch_index, tick)
                next_identity += 1
                channel = None if header.policy is design.Admission.NATIVE else rng.uniform()
                count = sum(s.actor is None for s in slots) if channel is None or channel >= .5 else sum(
                    s.actor is not None and s.actor.role is design.Role.UNBOUND and bool(s.actor.buffer[0]) for s in slots)
                rank_draw = rng.uniform() if count else None
                require(begin['channel_bits'] == (journal.uniform_bits(channel) if channel is not None else '') and
                        begin['rank_bits'] == (journal.uniform_bits(rank_draw) if rank_draw is not None else ''), 'independent admission RNG')
                plan = journal.check_selection(begin, header, state)
                pending.state, pending.begin, pending.plan = state, begin, plan
                pending.resolved = resolves[journal.number(begin['transaction'])]
                child_buffer = before.buffers[source].split(b'\0', 1)[0][offset:].ljust(c.MAXL0, b'\0')
                species[state.child] = species_for(child_buffer)  # allocation/species prefix persists on rejection
                if plan.disposition is design.Disposition.REPLACEMENT:
                    assert plan.incumbent is not None
                    victim = plan.incumbent
                    life('EVICT', tick, victim, before.buffers[victim], grid[victim])
                if plan.disposition in (design.Disposition.REPLACEMENT, design.Disposition.VACANCY):
                    assert plan.target is not None
                    life('BIRTH', tick, state.child, child_buffer, plan.target, active, passive, effect.buffers)
            else:
                require(dispatch_index not in begins, 'spurious BEGIN without nonempty VM proposal')
        previous_ids = set(boundary.source.material.buffers)
        boundary.step(row)
        current = boundary.source.material.buffers
        removed = previous_ids - current.keys()
        added = current.keys() - previous_ids
        for idx in removed:
            require(idx in grid, 'removing absent grid identity')
            del grid[idx]
            for active, vm in list(vms.items()):
                if idx in (vm.active, vm.passive):
                    del vms[active]
        for idx in added:
            require(pending is not None and pending.state is not None and pending.plan is not None and
                    idx == pending.state.child and pending.plan.target is not None, 'unexplained grid birth')
            assert pending is not None and pending.plan is not None and pending.plan.target is not None
            require(pending.plan.target not in grid.values(), 'occupied birth target')
            grid[idx] = pending.plan.target
        if removed and pending is not None and event == 'DEATH' and row['outcome'] == 'CLEAVE':
            for idx in (pending.active, pending.passive):
                if idx in current:
                    species[idx] = species_for(current[idx])
        if event == 'COMPLETE':
            require(pending is not None, 'completion without independent dispatch')
            assert pending is not None
            effect = pending.effect
            start = pending.start
            if effect.opcode == ord('='):
                require(events[start]['outcome'] == effect.copy_outcome and
                        {i: current[i] for i in effect.buffers} == effect.buffers, 'independent copy proposal/outcome')
            elif effect.opcode == ord('%'):
                if effect.proposal:
                    assert pending.state is not None and pending.begin is not None and pending.resolved is not None and pending.before is not None
                    require(journal.number(pending.resolved['boundary_index']) == boundary.index, 'admission completion boundary')
                    joined = material.check_transaction(pending.before, pending.begin, pending.resolved, header, pending.state, events[start:boundary.cursor])
                    require(joined.buffers == current, 'joined whole-history material state')
                else:
                    require(events[start]['outcome'] == 'NO_CHANGE' and {i: current[i] for i in effect.buffers} == effect.buffers, 'independent no-proposal cleavage')
                assert effect.flow is not None
                flow_source, flow_offset = effect.flow
                admitted = pending.plan is not None and pending.plan.disposition in (design.Disposition.VACANCY, design.Disposition.REPLACEMENT)
                child = pending.state.child if admitted and pending.state is not None else -1
                source, offset = (flow_source, flow_offset) if child >= 0 else (-1, -1)
                eligible = child >= 0 and offset > 0 and source in current and current[source][0] != 0
                source_eligible += eligible
                sx, sy = grid[source] if source in current else (-1, -1)
                cx, cy = grid[child] if child >= 0 else (-1, -1)
                lists = boundary.list_transactions[boundary.cursor]
                source_row = dict(tick=tick, material_index=boundary.cursor, active=pending.active, passive=pending.passive,
                    flow_source=flow_source, flow_offset=flow_offset, source=source, offset=offset, child=child,
                    eligible_tick=boundary.eligible_tick(child) if child >= 0 else 0, decision='RETAIN' if eligible else 'INELIGIBLE',
                    remnant_hex=current[source].hex().upper() if source in current else '', source_x=sx, source_y=sy, child_x=cx, child_y=cy,
                    survivor=-1, proposals=len(expected_sources)+1, eligible=source_eligible, committed=0)
                expected_sources.append({**{key: str(value) for key, value in source_row.items()},
                                         **{key: ';'.join(map(str, values)) for key, values in lists.items()}})
            if effect.unbind:
                vms.pop(pending.active, None)
                for idx in (pending.active, pending.passive):
                    species[idx] = species_for(current[idx])
            if pending.active in vms:
                require(0 <= vms[pending.active].address('i')[1] < c.MAXL0, 'post-opcode instruction bounds')
            pending = None
    require(boundary.ended and pending is None and seen_begins == set(begins), 'incomplete whole-history replay')
    end = int(rows[-1]['tick'])
    checkpoint(end, 'END')
    require(checkpoint_index == len(aggregates) and buffer_index == len(buffer_rows), 'extra checkpoint evidence')
    require(journal.number(admission[-1]['boundary_index']) == boundary.index and journal.number(admission[-1]['material_index']) == boundary.cursor and
            journal.ids(admission[-1]['now_ids']) == tuple(boundary.next), 'admission END reconciliation')
    require(set(grid) == set(boundary.next) and len(set(grid.values())) == len(grid), 'END grid roster/collision')
    end_row = dict.fromkeys(EVENT_COLUMNS, '-1')
    end_row.update(event='END', timestep=str(end), population=str(len(grid)), child_sequence_hex='', active_sequence_hex='', passive_sequence_hex='')
    expected_lineage.append(end_row)
    require(c.canonical_rows(directory / 'lineage_events001.csv', EVENT_COLUMNS) == expected_lineage, 'independent lineage event bijection/content')
    require(c.canonical_rows(directory / 'lineage_snapshots001.csv', SNAPSHOT_COLUMNS) == expected_snapshots, 'independent lineage snapshots')
    require(c.canonical_rows(directory / 'source_events006.csv', SOURCE_COLUMNS) == expected_sources, 'independent source/flow transaction bijection')
    terminal = []
    for idx in sorted(grid):
        role = 'ACTIVE' if idx in boundary.active else 'PASSIVE' if idx in boundary.pairs else 'UNBOUND'
        vm_row = dict.fromkeys(VM_COLUMNS, '')
        vm_row.update(tick=str(end), id=str(idx), role=role, partner=str(boundary.pairs.get(idx, -1)),
                      eligible_tick=str(boundary.eligible_tick(idx)), x=str(grid[idx][0]), y=str(grid[idx][1]))
        if role == 'ACTIVE':
            require(idx in vms, 'missing terminal active VM')
            for kind in 'irwf':
                vm_row[kind+'t'] = str(vms[idx].toggles[kind])
                for side in (0, 1): vm_row[kind+str(side)] = str(vms[idx].heads[kind][side])
        terminal.append(vm_row)
    require(c.canonical_rows(directory / 'vm_end007.csv', VM_COLUMNS) == terminal, 'independent terminal VM/grid state')
    require((directory / 'final_rng.txt').read_text(encoding='ascii') == rng.encoded(), 'independent full final RNG state')
    return {'end_tick': end, 'end_population': len(grid), 'rng_draws': rng.draws, 'proposals': structure.proposals,
            'evictions': structure.evictions, 'partial_opportunities': structure.partial_opportunities,
            'partial_commits': structure.partial_commits, 'boundary': boundary.summary(end),
            'all_admission': boundary.source.transfer_summary(), 'replacement_only': boundary.source.replacement_summary()}
