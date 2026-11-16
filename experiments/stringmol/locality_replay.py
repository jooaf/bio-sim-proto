"""SM-XL001 native-vacancy reconstruction: independent MT, VM, geometry/material.

No admission BEGIN claims or global-only admission verifier are used. Geometry
is reconstructed before every partner/placement draw. All full buffers, ledgers,
lineage, source journals, terminal heads and complete RNG state must agree.
"""
from pathlib import Path
from experiments.stringmol import analyze_conservation as c, retirement_material as material
from experiments.stringmol import analyze_retirement as retirement
from experiments.stringmol.admission_numeric import MT, Matrix, complement, f32
from experiments.stringmol.admission_vm import VM
from experiments.stringmol.admission_replay import VM_COLUMNS
from experiments.stringmol.locality_geometry import Boundary, candidates, vacancies
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS, require
from experiments.stringmol.analyze_scheduling import COLUMNS


def replay(directory, initial, coordinates, seed, matrix_path, interaction, placement, horizon=5000):
    directory = Path(directory)
    rng, matrix = MT(seed), Matrix(Path(matrix_path))
    loaded, order = list(map(int, initial['buffers'])), []
    while loaded:
        order.append(loaded.pop(rng.rank(len(loaded))))
    events = c.canonical_rows(directory/'material_events002.csv', material.JOURNAL_COLUMNS)
    grid = coordinates.copy()
    boundary = Boundary(initial, events, 'IMMEDIATE', horizon, initial_order=order,
                        grid=grid, interaction=interaction)
    registry, species = {}, {}
    def species_for(buffer):
        seq = buffer.split(b'\0', 1)[0]
        if seq not in registry:
            registry[seq] = len(registry)+1
        return registry[seq]
    for idx, buffer in boundary.source.material.buffers.items():
        species[idx] = species_for(buffer)
    lineage, snapshots, sources = [], [], []
    def life(event, tick, idx, buffer, cell, active=-1, passive=-1, parents=None):
        row = dict.fromkeys(EVENT_COLUMNS, '-1')
        row.update(event=event, timestep=str(tick), child_id=str(idx), active_id=str(active), passive_id=str(passive),
                   child_species=str(species[idx]), child_label='81', x=str(cell[0]), y=str(cell[1]),
                   child_sequence_hex=buffer.split(b'\0',1)[0].hex().upper(), active_sequence_hex='', passive_sequence_hex='')
        if parents is not None:
            for role, parent in (('active',active),('passive',passive)):
                row[role+'_species'] = str(species[parent]); row[role+'_label'] = '81'
                row[role+'_sequence_hex'] = parents[parent].split(b'\0',1)[0].hex().upper()
        lineage.append(row)
    for idx in order:
        life('INIT', 0, idx, boundary.source.material.buffers[idx], grid[idx])
    aggregates = c.canonical_rows(directory/'conservation002.csv', material.COLUMNS)
    buffer_rows = c.canonical_rows(directory/'conservation_buffers002.csv', c.BUFFER_COLUMNS)
    checkpoint_index = buffer_index = 0
    clustering = []
    def checkpoint(tick, event):
        nonlocal checkpoint_index, buffer_index
        require(checkpoint_index < len(aggregates), 'missing checkpoint')
        row = aggregates[checkpoint_index]; checkpoint_index += 1
        require(row['tick'] == str(tick) and row['event'] == event, 'checkpoint time')
        boundary.source.material.checkpoint(row)
        for idx, buffer in sorted(boundary.source.material.buffers.items()):
            observed = buffer_rows[buffer_index]; buffer_index += 1
            require(observed['tick'] == str(tick) and observed['event'] == event and observed['id'] == str(idx)
                    and c.full_buffer(observed['full_buffer_hex'],c.MAXL0) == buffer, 'checkpoint full buffer')
            if event == 'CHECKPOINT':
                x,y = grid[idx]
                snapshots.append(dict(tick=str(tick),id=str(idx),species=str(species[idx]),label='81',x=str(x),y=str(y),sequence_hex=buffer.split(b'\0',1)[0].hex().upper()))
        occupied = set(grid.values())
        adjacent = sum(((x+dx)%40,(y+dy)%40) in occupied for x,y in occupied for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
        clustering.append({'tick':tick,'event':event,'population':len(grid),'occupied_neighbor_slots':adjacent,'neighbor_slots':8*len(grid)})
    vms, pending = {}, None
    expected_decay, next_identity, source_eligible = None, max(grid)+1, 0
    searches = empty = encounters = bindings = proposals = failed = placed = vacancy_sum = 0
    rows = c.canonical_rows(directory/'scheduling_events001.csv', COLUMNS)
    for row in rows:
        event, tick = row['event'], int(row['tick'])
        if event == 'TICK' and tick % 100 == 0:
            checkpoint(tick,'CHECKPOINT')
        if event == 'SELECT':
            boundary.finish_selection()
            require(int(row['id']) == boundary.now[rng.rank(len(boundary.now))], 'independent top-level RNG')
            expected_decay = f32(rng.uniform()) < f32(.0005)
        elif event in ('SURVIVE','DECAY'):
            require(expected_decay is not None and (event == 'DECAY') == expected_decay, 'independent decay RNG')
            expected_decay = None
        elif event == 'DEATH' and row['outcome'] == 'DECAY':
            require(expected_decay is True, 'unproposed death')
        elif event == 'SEARCH':
            searches += 1
            choices = candidates(boundary.now,boundary.pairs,grid,int(row['id']),interaction,tick,boundary.eligible_tick)
            rank = rng.rank(len(choices)) if choices else -1
            require(int(row['count']) == len(choices) and int(row['selected']) == rank and
                    int(row['other']) == (choices[rank] if choices else -1), 'independent local/global candidate order/RNG')
            empty += not choices
        elif event == 'ENCOUNTER':
            encounters += 1
            first, second = int(row['id']), int(row['other'])
            buffers = boundary.source.material.buffers
            match = matrix.align(complement(buffers[first].split(b'\0',1)[0]),buffers[second].split(b'\0',1)[0])
            bound = f32(rng.uniform()) < match.probability(binding=True)
            require(row['outcome'] == ('BOUND' if bound else 'UNBOUND'), 'independent binding')
            bindings += bound
            if bound:
                vm = VM(first,second,match)
                require((int(row['active']),int(row['passive'])) == (vm.active,vm.passive), 'independent alignment roles')
                vms[vm.active] = vm
        elif event == 'DISPATCH':
            active, passive = int(row['active']),int(row['passive'])
            require(pending is None and active in vms, 'overlapping/missing VM')
            vm = vms[active]
            require(vm.passive == passive and vm.address('i') == (int(row['owner']),int(row['offset'])), 'independent instruction head')
            before = boundary.source.material
            effect = vm.instruction(before.buffers,before.arrays['pool'],rng,matrix)
            require(effect.opcode == int(row['opcode']), 'independent opcode')
            child, target = -1, None
            if effect.proposal:
                proposals += 1
                child = next_identity; next_identity += 1
                choices = vacancies(grid,active,placement)
                vacancy_sum += len(choices)
                target = choices[rng.rank(len(choices))] if choices else None
                source,offset = effect.flow
                species[child] = species_for(effect.buffers[source].split(b'\0',1)[0][offset:].ljust(c.MAXL0,b'\0'))
                if target is not None:
                    placed += 1
                    life('BIRTH',tick,child,effect.buffers[source].split(b'\0',1)[0][offset:].ljust(c.MAXL0,b'\0'),target,active,passive,effect.buffers)
                else:
                    failed += 1
            pending = dict(effect=effect,start=boundary.cursor,active=active,passive=passive,child=child,target=target)
        previous = set(boundary.source.material.buffers)
        boundary.step(row)
        current = boundary.source.material.buffers
        removed, added = previous-current.keys(), current.keys()-previous
        for idx in removed:
            del grid[idx]
            for active, vm in list(vms.items()):
                if idx in (vm.active,vm.passive):
                    del vms[active]
        for idx in added:
            require(pending is not None and idx == pending['child'] and pending['target'] is not None and pending['target'] not in grid.values(), 'independent vacancy/child identity')
            grid[idx] = pending['target']
        if removed and pending is not None and event == 'DEATH' and row['outcome'] == 'CLEAVE':
            for idx in (pending['active'],pending['passive']):
                if idx in current:
                    species[idx] = species_for(current[idx])
        if event == 'COMPLETE':
            require(pending is not None, 'missing dispatch')
            effect, start = pending['effect'],pending['start']
            if effect.opcode == ord('='):
                require(events[start]['outcome'] == effect.copy_outcome and {i:current[i] for i in effect.buffers} == effect.buffers, 'independent copy')
            elif effect.opcode == ord('%'):
                child = pending['child'] if pending['target'] is not None else -1
                flow_source,flow_offset = effect.flow
                require(events[start]['outcome'] == ('PLACED' if child >= 0 else 'FAILED' if effect.proposal else 'NO_CHANGE'), 'independent cleavage disposition')
                expected = effect.buffers.copy()
                if effect.proposal:
                    raw = expected[flow_source]; length = len(raw.split(b'\0',1)[0])
                    expected[flow_source] = raw[:flow_offset] + bytes(length-flow_offset) + raw[length:]
                    if child >= 0:
                        require(current[child] == raw.split(b'\0',1)[0][flow_offset:].ljust(c.MAXL0,b'\0'), 'independent suffix child')
                for idx,buf in expected.items():
                    require(current.get(idx) == buf if buf[0] else idx not in current, 'independent source healing')
                source, offset = (flow_source,flow_offset) if child >= 0 else (-1,-1)
                eligible = child >= 0 and offset > 0 and source in current and current[source][0] != 0
                source_eligible += eligible
                sx,sy = grid[source] if source in current else (-1,-1)
                cx,cy = grid[child] if child >= 0 else (-1,-1)
                values = dict(tick=tick,material_index=boundary.cursor,active=pending['active'],passive=pending['passive'],flow_source=flow_source,flow_offset=flow_offset,
                    source=source,offset=offset,child=child,eligible_tick=boundary.eligible_tick(child) if child >= 0 else 0,decision='RETAIN' if eligible else 'INELIGIBLE',
                    remnant_hex=current[source].hex().upper() if source in current else '',source_x=sx,source_y=sy,child_x=cx,child_y=cy,survivor=-1,proposals=len(sources)+1,eligible=source_eligible,committed=0)
                sources.append({**{k:str(v) for k,v in values.items()},**{k:';'.join(map(str,v)) for k,v in boundary.list_transactions[boundary.cursor].items()}})
            if effect.unbind:
                vms.pop(pending['active'],None)
                for idx in (pending['active'],pending['passive']):
                    species[idx] = species_for(current[idx])
            pending = None
    require(boundary.ended and pending is None, 'incomplete history')
    end = int(rows[-1]['tick']); checkpoint(end,'END')
    require(checkpoint_index == len(aggregates) and buffer_index == len(buffer_rows), 'extra checkpoints')
    require(set(grid) == set(boundary.next) and len(set(grid.values())) == len(grid), 'terminal grid collision/roster')
    row = dict.fromkeys(EVENT_COLUMNS,'-1')
    row.update(event='END',timestep=str(end),population=str(len(grid)),child_sequence_hex='',active_sequence_hex='',passive_sequence_hex='')
    lineage.append(row)
    require(c.canonical_rows(directory/'lineage_events001.csv',EVENT_COLUMNS) == lineage, 'independent lineage')
    require(c.canonical_rows(directory/'lineage_snapshots001.csv',SNAPSHOT_COLUMNS) == snapshots, 'independent snapshots')
    require(c.canonical_rows(directory/'source_events006.csv',retirement.SOURCE_COLUMNS) == sources, 'independent source journal')
    terminal = []
    for idx in sorted(grid):
        role = 'ACTIVE' if idx in boundary.active else 'PASSIVE' if idx in boundary.pairs else 'UNBOUND'
        row = dict.fromkeys(VM_COLUMNS,'')
        row.update(tick=str(end),id=str(idx),role=role,partner=str(boundary.pairs.get(idx,-1)),eligible_tick=str(boundary.eligible_tick(idx)),x=str(grid[idx][0]),y=str(grid[idx][1]))
        if role == 'ACTIVE':
            for kind in 'irwf':
                row[kind+'t'] = str(vms[idx].toggles[kind])
                for side in (0,1):
                    row[kind+str(side)] = str(vms[idx].heads[kind][side])
        terminal.append(row)
    require(c.canonical_rows(directory/'xl_vm_end.csv',VM_COLUMNS) == terminal, 'independent terminal heads/grid')
    require((directory/'xl_rng_end.txt').read_text() == rng.encoded(), 'independent complete terminal RNG')
    return dict(end_tick=end,end_population=len(grid),rng_draws=rng.draws,searches=searches,empty_searches=empty,encounters=encounters,bindings=bindings,
                proposals=proposals,placed=placed,failed_placement=failed,vacancy_sum=vacancy_sum,checkpoints=clustering,renewal=boundary.source.transfer_summary())
