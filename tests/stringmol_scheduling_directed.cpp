// The complete conservation/recycling fixtures also run against patch 0005.
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

static void policy(Fixture &f, const char *name) {
    setenv("STRINGMOL_SCHEDULING","1",1);
    setenv("STRINGMOL_SCHEDULING_POLICY",name,1);
    unsetenv("STRINGMOL_SCHEDULING_LOG");
    f.a->next=f.b;
    f.sim.scheduling.init(f.a,5000,false);
    f.a->next=NULL;
}
static void policy_cleavages() {
    for(const char *name:{"IMMEDIATE","DELAY500","LOCKED"})
    for(int target:{0,1}) for(int offset:{0,1,3,4})
    for(bool full:{false,true}) for(bool hidden:{false,true}) {
        Fixture f("%ABC","BCDA");
        policy(f,name); f.sim.timestep=2500;
        if(hidden) { f.a->S[10]='Z'; f.b->S[11]='Y'; }
        f.a->ft=target; f.a->f[target]=(target?f.a->S:f.b->S)+offset;
        if(full) for(int x=0;x<3;++x) for(int y=0;y<3;++y) if(!f.sim.grid->grid[x][y]) f.sim.grid->grid[x][y]=f.a;
        f.enable(0); auto &c=f.sim.conservation;
        auto before=SpatialConservation::sum(c.count(f.a),c.count(f.b));
        SetRNGSeed(7); int destroyed=f.sim.OpcodeCleaveSpatial(f.a);
        s_ag *child=NULL;
        for(s_ag *p=f.sim.nexthead;p;p=p->next) if(p->idx==2) child=p;
        assert(bool(child)==(offset<4 && !full));
        assert(destroyed==(offset==0?(target?1:2):0));
        auto after=SpatialConservation::Counts{};
        if(!(destroyed&1)) after=SpatialConservation::sum(after,c.count(f.a));
        if(!(destroyed&2)) after=SpatialConservation::sum(after,c.count(f.b));
        after=SpatialConservation::sum(after,c.count(child));
        assert(before==SpatialConservation::sum(after,c.pool));
        if(child) {
            assert(child->eligible_tick==(!strcmp(name,"LOCKED")?5001:!strcmp(name,"DELAY500")?3001:2501));
            assert(child->status==B_UNBOUND && child->len==4-offset);
            assert(f.sim.grid->grid[child->x][child->y]==child);
            for(unsigned j=child->len;j<SIZE;++j) assert(child->S[j]==0);
        }
        assert(rng()==after_draws(7,offset<4 && !full?1:0));
    }
}
static void partner_filter() {
    for(bool reverse:{false,true}) for(int radius:{0,1}) for(unsigned tick:{500,501}) {
        Fixture f("ABC","ABC"); policy(f,"DELAY500");
        f.a->status=f.b->status=B_UNBOUND; f.a->pass=NULL; f.b->exec=NULL;
        f.a->eligible_tick=501; f.sim.scheduling.children[0]=501;
        f.sim.interaction_radius=radius; f.sim.timestep=tick;
        s_ag *first=reverse?f.b:f.a, *second=reverse?f.a:f.b;
        first->next=second; second->next=NULL; first->prev=NULL; second->prev=first;
        f.sim.nowhead=first;
        f.sim.grid->status[0][0]=f.sim.grid->status[1][0]=G_NOW;
        SetRNGSeed(7);
        s_ag *p=f.sim.ReactionSeekRandomSpatialPartner(2,1);
        assert(p && (tick==501 || p==f.b));
        assert(f.sim.scheduling.candidates==(tick==501?2:1));
        assert(rng()==after_draws(7,1));
    }
    Fixture f; policy(f,"LOCKED"); f.a->status=B_UNBOUND; f.a->pass=NULL;
    f.a->eligible_tick=5001; f.sim.nowhead=f.a; f.sim.interaction_radius=0;
    SetRNGSeed(7); assert(!f.sim.ReactionSeekRandomSpatialPartner(0,0)); assert(rng()==after_draws(7,0));
}
static void delayed_processing() {
    for(const char *name:{"DELAY500","LOCKED"}) for(bool dies:{false,true}) {
        Fixture f; policy(f,name); f.enable(0);
        // Detach the other initial molecule from both population and material ledger.
        f.sim.decayrate=1; s_ag *other=f.b; f.b->status=B_UNBOUND; f.b->exec=NULL;
        f.sim.AgentAttemptDecaySpatial(&other);
        f.a->status=B_UNBOUND; f.a->pass=NULL; f.a->S[20]='Z';
        // Hidden bytes are tested via fresh initialization in inherited decay tests.
        f.a->S[20]=0;
        f.a->eligible_tick=!strcmp(name,"LOCKED")?5001:501;
        f.sim.scheduling.children[0]=f.a->eligible_tick;
        f.sim.nowhead=f.a; f.sim.timestep=500; f.sim.decayrate=dies?1:0;
        f.sim.interaction_radius=0; f.sim.nexthead=NULL;
        SetRNGSeed(77); f.sim.TimestepIncrementSpatial();
        assert(rng()==after_draws(77,2)); // Native top-level selection and native decay only.
        assert(f.sim.nowhead==(dies?NULL:f.a));
        assert(f.sim.scheduling.released.empty());
        if(!dies && !strcmp(name,"DELAY500")) {
            f.sim.timestep=501; SetRNGSeed(77); f.sim.TimestepIncrementSpatial();
            assert(f.sim.scheduling.released.count(0)==1 && f.sim.nowhead==f.a);
            assert(rng()==after_draws(77,2));
        }
    }
}
static void recursive_child() {
    Fixture f("%ABC","BCDA"); policy(f,"DELAY500"); f.enable(0); f.sim.timestep=100;
    f.a->ft=0; f.a->f[0]=f.b->S+1; f.sim.OpcodeCleaveSpatial(f.a);
    s_ag *child=f.sim.nexthead; assert(child->idx==2 && child->eligible_tick==601);
    // The released first child supplies the next placed suffix.
    f.sim.nexthead=NULL; child->next=child->prev=NULL;
    f.a->pass=child; child->exec=f.a; child->status=B_PASSIVE;
    f.b->status=B_UNBOUND; f.b->exec=NULL;
    f.a->ft=0; f.a->f[0]=child->S+1;
    f.sim.timestep=601; f.sim.OpcodeCleaveSpatial(f.a);
    assert(f.sim.nexthead->idx==3 && f.sim.nexthead->eligible_tick==1102);
}
static void placed_child_decay() {
    for(const char *name:{"DELAY500","LOCKED"}) {
        Fixture f("%ABC","BCDA"); policy(f,name); f.enable(0);
        f.a->ft=0; f.a->f[0]=f.b->S+1; f.sim.timestep=0;
        f.sim.OpcodeCleaveSpatial(f.a);
        s_ag *child=f.sim.nexthead; assert(child && child->idx==2);
        auto &c=f.sim.conservation;
        auto units=c.count(child), pool=c.pool;
        int x=child->x,y=child->y,energy=f.sim.energy;
        uint64_t eligible=child->eligible_tick;
        f.sim.timestep=100; f.sim.decayrate=1; SetRNGSeed(81);
        assert(f.sim.AgentAttemptDecaySpatial(&child)==1 && !child);
        assert(eligible>100 && f.sim.scheduling.released.empty());
        assert(c.pool==SpatialConservation::sum(pool,units) && c.decay_pool==units);
        assert(c.event_index==2 && f.sim.energy==energy && !f.sim.grid->grid[x][y]);
        assert(rng()==after_draws(81,1));
    }
}
static void fatal_and_disabled() {
    must_fail([]{SpatialScheduling::add(UINT64_MAX,1);});
    for(const char *name:{"", "500", "delay500"}) must_fail([name]{Fixture f; policy(f,name);});
    for(bool passive:{false,true}) must_fail([passive]{Fixture f; policy(f,"DELAY500"); (passive?f.b:f.a)->eligible_tick=1; f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);});
    must_fail([]{Fixture f; policy(f,"LOCKED"); f.a->eligible_tick=5001; f.sim.nowhead=f.a; f.a->next=f.b; f.sim.TimestepIncrementSpatial();});
    must_fail([]{Fixture f; policy(f,"DELAY500"); f.sim.scheduling.birth(f.a,0,0,0,1,1);});
    for(const char *flag:{"0",""}) {
        if(*flag) setenv("STRINGMOL_SCHEDULING",flag,1); else unsetenv("STRINGMOL_SCHEDULING");
        setenv("STRINGMOL_SCHEDULING_POLICY","garbage-ignored",1);
        Fixture f; f.sim.scheduling.init(f.a,5000,false); assert(!f.sim.scheduling.enabled);
        assert(f.a->eligible_tick==0 && f.b->eligible_tick==0);
    }
}
int main() {
    unsetenv("STRINGMOL_SCHEDULING"); unsetenv("STRINGMOL_SCHEDULING_LOG");
    for(int branch=0;branch<6;++branch) for(int dest=0;dest<2;++dest) for(int granular=0;granular<2;++granular)
        for(bool alias:{false,true}) for(bool blocked:{false,true}) parity_case(branch,dest,granular,alias,blocked);
    bounds(); transactions_and_gaps(); atomic_insertion_and_minima(); cleavage(); decay(); initialization();
    substitution_endpoints(); dispatch_and_cleavage_faults(); nul_insertion_contraction();
    setenv("STRINGMOL_DECAY_DESTINATION","recycle",1);
    setenv("STRINGMOL_CONSERVATION_LOG","0",1);
    routed_decay(); downstream();
    setenv("STRINGMOL_DECAY_DESTINATION","recycle",1);
    policy_cleavages(); partner_filter(); delayed_processing(); recursive_child(); placed_child_decay(); fatal_and_disabled();
    puts("SM-B001 directed gates passed");
    return 0;
}
