"""Independent SM-B003 material-derived ancestry; never a launch certificate."""
from typing import Any

from experiments.stringmol.admission_material import Replay as MaterialReplay
from experiments.stringmol import analyze_retirement as frozen
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.retirement_material import ids


class SourceReplay(frozen.SourceReplay):
    material: MaterialReplay

    def __init__(self, initial: dict[str, Any]):
        super().__init__(initial)
        self.material = MaterialReplay(initial)
        self.replacement_depth: dict[int, int | None] = dict.fromkeys(self.initial_ids, 0)
        self.replacement_renewals: dict[int, dict[str, Any]] = {}
        self.pending_eviction: int | None = None
        self.invalid = False

    def step(self, row: dict[str, str]) -> None:
        require(not self.invalid, 'source replay already failed')
        try:
            self._step(row)
        except Exception:
            self.invalid = True
            raise

    def _step(self, row: dict[str, str]) -> None:
        event = row['event']
        if self.pending_eviction is not None:
            require(event == 'CLEAVE' and row['outcome'] == 'PLACED', 'eviction without immediately admitted cleavage')
        if event == 'EVICT':
            victims = ids(row['before_ids'])
            require(len(victims) == 1, 'replacement victim cardinality')
            self.pending_eviction = victims[0]
        super().step(row)
        if event != 'CLEAVE':
            return
        victim = self.pending_eviction
        self.pending_eviction = None
        if row['outcome'] != 'PLACED':
            return
        edge = self.edges[-1]
        source, child = edge['source'], edge['child']
        require(victim not in edge['participants'], 'replacement victim is a participant')
        parent = self.replacement_depth[source]
        qualifying = victim is not None and edge['transfer_eligible']
        rooted = qualifying and parent is not None
        self.replacement_depth[child] = parent + 1 if rooted and parent is not None else None
        edge.update(replacement_victim=victim, replacement_eligible=qualifying,
                    replacement_rooted=rooted, replacement_orphan=qualifying and not rooted,
                    replacement_depth=self.replacement_depth[child], replacement_source_depth=parent)
        if rooted and parent and source not in self.replacement_renewals:
            # The inherited record freezes retention at the first qualifying
            # source event across ALL channels, not the later replacement event.
            require(source in self.transfer_renewals, 'replacement renewal missing all-admission ancestor')
            self.replacement_renewals[source] = self.transfer_renewals[source].copy()

    def replacement_summary(self) -> dict[str, Any]:
        require(not self.invalid and self.pending_eviction is None, 'failed/unfinished eviction transaction')
        renewals = list(self.replacement_renewals.values())
        return {
            'qualifying_transfers': sum(e['replacement_rooted'] for e in self.edges),
            'transfer_renewing_descendants': len(renewals),
            'serial_transfers': sum(e['replacement_rooted'] and bool(e['replacement_source_depth']) for e in self.edges),
            'max_nonrelocation_depth': max((d for d in self.replacement_depth.values() if d is not None), default=0),
            'late_transfer_renewing_descendants': sum(r['late'] for r in renewals),
            'retained_late_transfer_renewals': sum(r['retained_late'] for r in renewals),
            'orphan_transfers': sum(e['replacement_orphan'] for e in self.edges),
            'transfer_renewals': renewals,
        }
