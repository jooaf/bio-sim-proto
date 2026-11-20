// Mechanical logger calls only: NO Run(), timestep loop, or population execution.
#define main inherited_conservation_main
#include "stringmol_conservation_directed.cpp"
#undef main
// Include the copied implementation to reach its anonymous-namespace lineage hooks.
// Link all release objects EXCEPT sm_spatial.o and stringmol.o.
#include "sm_spatial.cpp"
#include <fstream>

static std::string ordinary(Fixture &f) {
    std::ostringstream out; out << f.state();
    auto &c=f.sim.conservation;
    for(const auto *ledger:{&c.pool,&c.initial,&c.initial_pool,&c.minimum,&c.withdrawals,&c.returns,
            &c.decay,&c.failed,&c.discard,&c.missing,&c.retirement_returns,&c.waste,&c.decay_pool,
            &c.decay_waste,&c.stable_molecular}) for(auto value:*ledger) out << value << ',';
    out << c.attempts << ',' << c.growth << ',' << c.positive_bytes << ',' << c.contraction_bytes;
    for(auto value:c.categories) out << ',' << value;
    for(s_ag *a:{f.a,f.b}) out << ';' << a->x << ',' << a->y << ',' << a->eligible_tick;
    for(int x=0;x<3;++x) for(int y=0;y<3;++y)
        out << ';' << (f.sim.grid->grid[x][y] ? f.sim.grid->grid[x][y]->idx : -1) << ',' << f.sim.grid->status[x][y];
    return out.str();
}

int main() {
    Fixture f;
    f.enable(1000);
    f.a->next=f.b; f.b->prev=f.a; f.sim.nowhead=f.a;
    SetRNGSeed(42);
    auto before=ordinary(f); auto full_rng=rng();
    lineage_begin(0,f.sim.nowhead);
    f.sim.conservation.observe(0,"CHECKPOINT",f.sim.nowhead);
    f.sim.conservation.open_journal();
    f.sim.scheduling.init(f.sim.nowhead,5000,f.sim.conservation.routed && f.sim.conservation.logging);
    f.sim.retirement.init(f.sim.conservation);
    lineage_snapshot(0,f.sim.nowhead);
    xl_terminal(f.sim,5000);
    lineage_end(5000,2);
    f.sim.scheduling.end(5000,f.sim.nowhead,f.sim.conservation.event_index);
    if(f.sim.retirement.journal) {
        if(fclose(f.sim.retirement.journal)) return 3;
        f.sim.retirement.journal=NULL;
    }
    if(before!=ordinary(f) || full_rng!=rng()) return 4;
    // Ordinary state/full RNG outputs must have exact byte parity across switches.
    std::ofstream("ordinary-state.bin",std::ios::binary) << ordinary(f);
    std::ofstream("ordinary-rng.txt") << rng();
    puts("SM-XL001 directed logger mechanics; no population loop");
    return 0;
}
