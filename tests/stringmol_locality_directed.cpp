// No population loop. Direct native geometry/placement calls plus conservation suite.
#define main inherited_conservation_main
#include "stringmol_conservation_directed.cpp"
#undef main
#include "locality_observer.h"
static void terminal_observation() {
    Fixture f; f.enable(0); f.a->next=f.b; f.b->prev=f.a; f.sim.nowhead=f.a;
    f.sim.scheduling.journal=tmpfile(); assert(f.sim.scheduling.journal);
    SetRNGSeed(42); auto before=rng(); auto state=f.state();
    xl_terminal(f.sim,5000);
    assert(rng()==before && f.state()==state);
    fclose(f.sim.scheduling.journal); f.sim.scheduling.journal=NULL;
}
static void geometry() {
    for(unsigned seed=1;seed<=24;++seed) {
        Fixture f("ABC","ABC");
        // Enlarge to avoid radius-one wrapping alias on 3x3 fixture grid.
        f.sim.grid=f.sim.init_smprun(40,40);
        f.a->status=f.b->status=B_UNBOUND; f.a->pass=NULL; f.b->exec=NULL;
        AgentPlaceOnGrid(f.a,f.sim.grid,39,39); AgentPlaceOnGrid(f.b,f.sim.grid,20,20);
        f.sim.grid->status[39][39]=f.sim.grid->status[20][20]=G_NOW;
        f.a->next=f.b; f.b->prev=f.a; f.sim.nowhead=f.a;
        f.sim.interaction_radius=1;
        SetRNGSeed(seed);
        assert(f.sim.ReactionSeekRandomSpatialPartner(0,0)==f.a); // toroidal diagonal
        assert(rng()==after_draws(seed,1));
        f.sim.grid->status[39][39]=G_NOW; f.sim.grid->status[20][20]=G_NOW;
        f.sim.interaction_radius=0;
        SetRNGSeed(seed); s_ag *chosen=f.sim.ReactionSeekRandomSpatialPartner(20,20);
        assert(chosen==f.a || chosen==f.b); assert(rng()==after_draws(seed,1));
        // Only G_NOW local candidates, not already-processed agents.
        f.sim.interaction_radius=1;
        f.sim.grid->status[39][39]=G_NEXT; f.sim.grid->status[20][20]=G_NEXT;
        SetRNGSeed(seed); assert(!f.sim.ReactionSeekRandomSpatialPartner(0,0));
        assert(rng()==after_draws(seed,0));
    }
    bool saw_first=false,saw_second=false;
    for(unsigned seed=1;seed<=24;++seed) {
        Fixture f("ABC","ABC"); f.a->status=f.b->status=B_UNBOUND;
        f.a->pass=NULL; f.b->exec=NULL; f.sim.nowhead=f.a; f.a->next=f.b; f.b->prev=f.a;
        f.sim.interaction_radius=1;
        f.sim.grid->status[0][0]=f.sim.grid->status[1][0]=G_NOW;
        SetRNGSeed(seed); auto chosen=f.sim.ReactionSeekRandomSpatialPartner(2,1);
        saw_first |= chosen==f.a; saw_second |= chosen==f.b;
    }
    assert(saw_first && saw_second);
}
static void placement() {
    for(int radius:{0,1}) {
        Fixture f; f.sim.grid=f.sim.init_smprun(40,40);
        AgentPlaceOnGrid(f.a,f.sim.grid,0,0); AgentPlaceOnGrid(f.b,f.sim.grid,20,20);
        s_ag *child=AgentMakeWithSequence(const_cast<char *>("ABC"),'Q',2,SIZE);
        f.sim.placement_radius=radius;
        for(int x:{39,0,1}) for(int y:{39,0,1}) f.sim.grid->grid[x][y]=f.a;
        SetRNGSeed(7);
        auto placed=f.sim.AgentPlaceInMooreNeighbourhood(child,0,0);
        assert(bool(placed)==(radius==0));
        assert(rng()==after_draws(7,radius==0?1:0));
        assert(f.sim.grid->grid[20][20]==f.b); // no overwrite
    }
    Fixture f; f.sim.grid=f.sim.init_smprun(40,40);
    AgentPlaceOnGrid(f.a,f.sim.grid,0,0); AgentPlaceOnGrid(f.b,f.sim.grid,20,20);
    f.sim.placement_radius=1;
    s_ag *child=AgentMakeWithSequence(const_cast<char *>("ABC"),'Q',2,SIZE);
    assert(f.sim.AgentPlaceInMooreNeighbourhood(child,f.a->x,f.a->y)==child);
    assert((child->x==39 || child->x<=1) && (child->y==39 || child->y<=1));
    assert(f.sim.grid->grid[20][20]==f.b);
}
int main() {
    unsetenv("STRINGMOL_SCHEDULING"); unsetenv("STRINGMOL_SOURCE_RETENTION");
    for(int branch=0;branch<6;++branch) for(int dest=0;dest<2;++dest) for(int granular=0;granular<2;++granular)
        for(bool alias:{false,true}) for(bool blocked:{false,true}) parity_case(branch,dest,granular,alias,blocked);
    bounds(); transactions_and_gaps(); atomic_insertion_and_minima(); cleavage(); decay(); initialization();
    substitution_endpoints(); dispatch_and_cleavage_faults(); nul_insertion_contraction();
    geometry(); placement(); terminal_observation();
    puts("SM-XL001 native mechanics passed");
}
