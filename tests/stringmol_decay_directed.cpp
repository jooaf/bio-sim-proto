// Retain every frozen SM-C001 source fixture against the new release objects.
#define main sm_c001_main
#include "stringmol_conservation_directed.cpp"
#undef main

static void routed_decay() {
    for (const char *route : {"recycle", "sequester"}) for(int status : {B_UNBOUND,B_ACTIVE,B_PASSIVE}) {
        setenv("STRINGMOL_DECAY_DESTINATION",route,1);
        Fixture f; f.a->S[20]='Z'; f.b->S[21]='A'; f.enable(0);
        auto &c=f.sim.conservation; auto expected=c.count(f.a);
        if(status==B_UNBOUND) { f.a->status=B_UNBOUND; f.a->pass=NULL; }
        else expected=SpatialConservation::sum(expected,c.count(f.b));
        long biomass=f.sim.biomass; int energy=f.sim.energy;
        f.sim.decayrate=1; s_ag *p=status==B_PASSIVE?f.b:f.a;
        SetRNGSeed(3); assert(f.sim.AgentAttemptDecaySpatial(&p)==1 && !p);
        assert(rng()==after_draws(3,1));
        assert(c.decay==expected);
        assert(c.sequester ? c.waste==expected && c.pool==SpatialConservation::Counts{} : c.pool==expected && c.waste==SpatialConservation::Counts{});
        assert(c.decay==SpatialConservation::sum(c.decay_pool,c.decay_waste));
        assert(c.event_index==(status==B_UNBOUND?1:2));
        assert(f.sim.biomass==biomass && f.sim.energy==energy);
        assert(!f.sim.grid->grid[0][0]);
        if(status!=B_UNBOUND) assert(!f.sim.grid->grid[1][0]);
    }
}
static void downstream() {
    for(const char *route : {"recycle","sequester"}) {
        setenv("STRINGMOL_DECAY_DESTINATION",route,1);
        Fixture f;
        s_ag *donor=AgentMakeWithSequence(const_cast<char *>("A"),'Q',2,SIZE);
        donor->status=B_UNBOUND; donor->S[20]='Z';
        AgentPlaceOnGrid(donor,f.sim.grid,2,0);
        f.b->next=donor; f.enable(0); f.b->next=NULL;
        auto &c=f.sim.conservation;
        f.sim.decayrate=1; SetRNGSeed(77);
        assert(f.sim.AgentAttemptDecaySpatial(&donor)==1 && !donor);
        std::string after=rng(); assert(after==after_draws(77,1));
        f.sim.domut=false;
        SetRNGSeed(9); f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        assert(rng()==after_draws(9,1));
        assert(f.b->S[2]==(c.sequester?'\0':'A'));
        assert(c.categories[c.sequester?SpatialConservation::BLOCKED:SpatialConservation::ACCEPTED]==1);
        assert(c.waste[SpatialConservation::symbol('A')]==(c.sequester?1:0));
        assert(f.a->biomass==8 && f.sim.biomass==20 && f.sim.energy==29);
        assert(f.a->i[1]==f.a->S+1 && f.a->w[0]==f.b->S+3 && f.a->r[1]==f.a->S+2);
        assert(f.b->len==(c.sequester?2:3) && f.a->status==B_ACTIVE && f.b->status==B_PASSIVE);
    }
}
int main() {
    unsetenv("STRINGMOL_DECAY_DESTINATION");
    for(int branch=0;branch<6;++branch) for(int dest=0;dest<2;++dest) for(int granular=0;granular<2;++granular)
        for(bool alias:{false,true}) for(bool blocked:{false,true}) parity_case(branch,dest,granular,alias,blocked);
    bounds(); transactions_and_gaps(); atomic_insertion_and_minima(); cleavage(); decay(); initialization();
    substitution_endpoints(); dispatch_and_cleavage_faults(); nul_insertion_contraction();
    setenv("STRINGMOL_CONSERVATION_LOG","0",1);
    routed_decay(); downstream();
    for(const char *route:{"recycle","sequester"}) {
        setenv("STRINGMOL_DECAY_DESTINATION",route,1);
        cleavage();
    }
    for(const char *route:{"", "unknown", "RECYCLE"}) must_fail([route]{setenv("STRINGMOL_DECAY_DESTINATION",route,1); Fixture f; f.enable(0);});
    setenv("STRINGMOL_DECAY_DESTINATION","sequester",1);
    must_fail([]{setenv("STRINGMOL_CONSERVATION","bad",1); SpatialConservation c; c.init(NULL,0,NULL);});
    must_fail([]{Fixture f; f.enable(0); f.sim.conservation.waste[0]=INT64_MAX; f.sim.conservation.decay_release(f.a);});
    must_fail([]{Fixture f; f.enable(0); f.sim.conservation.decay_waste[0]=INT64_MAX; f.sim.conservation.decay_release(f.a);});
    for(const char *flag:{"0"}) {setenv("STRINGMOL_CONSERVATION",flag,1); setenv("STRINGMOL_DECAY_DESTINATION","unknown",1); SpatialConservation c; c.init(NULL,0,NULL); assert(!c.enabled);}
    unsetenv("STRINGMOL_CONSERVATION"); SpatialConservation c; c.init(NULL,0,NULL); assert(!c.enabled);
    puts("SM-C002 directed gates passed");
    return 0;
}
