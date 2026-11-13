// Real ReactionExecuteOpcode_Spatial, not hand-supplied source healing.
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <set>
#include "default_config.h"
#include "alignment.h"
#include "rules.h"
#include "agent.h"
#include "SMspp.h"
#include "opcodes.h"
#include "stringPM.h"
#include "sm_conservation.h"
#include "sm_scheduling.h"
#include "sm_retirement.h"
#ifndef SM_ADMISSION_LEGACY
#include "admission_adapter.h"
#endif
#include "sm_spatial.h"
#include "mt19937-2.h"
#include "randutil.h"
#include "setupSM.h"

static const unsigned SIZE=2001;
static std::string rng() {
    FILE *f=tmpfile(); assert(f); MersenneTwisterPrintStatusToFile(f); assert(!fflush(f));
    rewind(f); std::string text; int c; while((c=fgetc(f))!=EOF) text+=static_cast<char>(c);
    assert(!ferror(f) && !fclose(f)); return text;
}
#ifndef SM_ADMISSION_LEGACY
#include "stringmol_admission_fault_witness.h"
#endif
static void env(const char *name,const char *value) { assert(!setenv(name,value,1)); }
int main(int argc,char **argv) {
    if(argc==5 && !strcmp(argv[1],"numeric")) {
        SMspp species;
        {
            Stringmol_Spatial sim(&species);
            assert(sim.load_table_matrix(argv[4])==0);
            printf("\n");
            SetRNGSeed(std::strtoul(argv[2],nullptr,10));
            const unsigned count=static_cast<unsigned>(std::strtoul(argv[3],nullptr,10));
            for(unsigned i=0;i<count;++i) printf("DRAW %.17g\n",RandomBetween0And1());
            FILE *out=fopen("numeric-rng.txt","wx"); assert(out);
            const std::string state=rng(); assert(fputs(state.c_str(),out)>=0 && !fclose(out));
            char a[2001],b[2001];
            while(scanf("%2000s %2000s",a,b)==2) {
                align result={};
                SmithWatermanAlignment(a,b,&result,sim.blosum,0);
                printf("ALIGN %d %d %d %d %.9g %d %.9g\n",result.s1,result.e1,result.s2,result.e2,
                       result.score,result.match,ReactionCalculateBindProbability(&result));
            }
        }
        species.SpeciesListClear();
        return 0;
    }
    if(argc==4 && !strcmp(argv[1],"loader")) {
        SMspp species;
        { Stringmol_Spatial sim(&species); assert(sim.load_table(argv[2])==atoi(argv[3])); }
        species.SpeciesListClear();
        return 0;
    }
    assert(argc==10 || argc==11);
    const char *empty=argc==11?argv[10]:"none";
    assert(!strcmp(empty,"none") || !strcmp(empty,"active") || !strcmp(empty,"passive"));
    const char *policy=argv[1], *schedule=argv[2], *layout=argv[7];
    const int target=std::atoi(argv[3]), offset=std::atoi(argv[4]), hidden=std::atoi(argv[5]), future=std::atoi(argv[6]);
    const unsigned seed=static_cast<unsigned>(std::atoi(argv[8]));
    assert((target==0 || target==1) && offset>=0 && offset<=4 && seed>=1 && seed<=64);
#ifndef SM_ADMISSION_LEGACY
    const char *fault=std::getenv("STRINGMOL_ADMISSION_FAULT"), *io=std::getenv("SM_TEST_NATIVE_FLUSH");
    assert(!fault || !io);
    if(fault || io) {
        witness_enabled=true;
        if(fault) witness_phase=fault;
        else { witness_io=io; witness_phase="io:"+witness_io; }
        assert(hidden && offset==1 && seed==2 && !strcmp(layout,"sparse") && !strcmp(policy,"STRATIFIED_REPLACE"));
        assert(!atexit(witness_exit));
    }
#else
    assert(!strcmp(policy,"NATIVE_VACANCY"));
#endif
    SMspp species;
    {
        Stringmol_Spatial sim(&species);
#ifndef SM_ADMISSION_LEGACY
        witness_sim=&sim;
#endif
        sim.maxl0=SIZE; sim.maxl=SIZE-1; sim.domut=false;
        assert(!sim.load_table_matrix(argv[9])); sim.grid=sim.init_smprun(3,3);
        sim.placement_radius=0; sim.biomass=19; sim.energy=30; sim.timestep=0;
        auto agent=[&](const char *sequence,int id,int x,int y) {
            auto p=AgentMakeWithSequence(const_cast<char *>(sequence),'Q',id,SIZE); assert(p);
            species.SpeciesListUpdate(p,'I',1,nullptr,nullptr,0,0,SIZE);
            AgentPlaceOnGrid(p,sim.grid,x,y); sim.grid->status[x][y]=G_NOW;
            AgentAppend(&sim.nowhead,p); return p;
        };
        auto a=agent(!strcmp(empty,"active")?"":"%ABC",0,0,0);
        auto b=agent(!strcmp(empty,"passive")?"":!strcmp(empty,"active")?"%ABC":"BCDA",1,1,0);
        assert(!strcmp(empty,"none") || target==int(!strcmp(empty,"passive")));
        a->status=B_ACTIVE; b->status=B_PASSIVE; a->pass=b; b->exec=a;
        for(int t=0;t<2;++t) a->i[t]=a->r[t]=a->w[t]=a->f[t]=t?a->S:b->S;
        a->it=a->rt=strcmp(empty,"active")?1:0; a->wt=0; a->ft=target;
        a->f[target]=(target?a->S:b->S)+offset;
        a->biomass=7; b->biomass=3; a->ect=11; b->ect=5;
        if(hidden) { a->S[10]='Z'; b->S[11]='Y'; }
        int id=2; std::vector<s_ag *> extra;
        for(int x=0;x<3;++x) for(int y=0;y<3;++y) if(!sim.grid->grid[x][y]) {
            if(!std::strcmp(layout,"sparse") && !extra.empty()) continue;
            auto p=agent("A",id++,x,y); extra.push_back(p);
            p->eligible_tick=999; if(hidden) p->S[10]=p->S[11]='B';
        }
        if(!std::strcmp(layout,"protected")) {
            for(size_t i=0;i+1<extra.size();i+=2) {
                auto x=extra[i],y=extra[i+1];
                x->status=B_ACTIVE; y->status=B_PASSIVE; x->pass=y; y->exec=x;
                x->eligible_tick=y->eligible_tick=0;
                x->it=x->rt=1; x->wt=x->ft=0;
                for(int t=0;t<2;++t) x->i[t]=x->r[t]=x->w[t]=x->f[t]=t?x->S:y->S;
            }
            extra.back()->S[0]=0; extra.back()->len=0;
        } else assert(!std::strcmp(layout,"sparse") || !std::strcmp(layout,"full"));
        sim.agct=id;
        env("STRINGMOL_CONSERVATION","1"); env("STRINGMOL_POOL_MODE","uniform"); env("STRINGMOL_POOL_AMOUNT","0");
        env("STRINGMOL_CONSERVATION_LOG","1"); env("STRINGMOL_DECAY_DESTINATION","recycle");
        sim.conservation.init(sim.nowhead,SIZE,sim.blosum->key);
        env("STRINGMOL_SCHEDULING","1"); env("STRINGMOL_SCHEDULING_POLICY",schedule); env("STRINGMOL_SCHEDULING_LOG","1");
        sim.scheduling.init(sim.nowhead,1,true);
        // Synthetic late-eligibility incumbents: init resets initial agents to 0.
        // This directed fixture is not a full population scheduling history.
        for(auto p:extra) if(p->status==B_UNBOUND) p->eligible_tick=999;
        env("STRINGMOL_SOURCE_RETENTION","1"); env("STRINGMOL_SOURCE_DISPOSITION","RETAIN"); env("STRINGMOL_RETIREMENT_LOG","1");
        sim.retirement.init(sim.conservation);
#ifndef SM_ADMISSION_LEGACY
        const char *mode=getenv("SM_TEST_ADMISSION_MODE");
        assert(!mode || !strcmp(mode,"disabled") || !strcmp(mode,"unobserved") || !strcmp(mode,"observed"));
        const bool disabled=mode && !strcmp(mode,"disabled");
        assert(!disabled || !strcmp(policy,"NATIVE_VACANCY"));
        env("STRINGMOL_ADMISSION",disabled?"0":"1"); env("STRINGMOL_ADMISSION_POLICY",policy);
        env("STRINGMOL_ADMISSION_LOG",mode && !strcmp(mode,"unobserved")?"0":"1");
        sim.admission.init(sim.conservation,sim.scheduling,sim.retirement,*sim.grid,sim.nowhead,sim.nexthead,1,0,false);
#endif
        sim.conservation.observe(0,"START",sim.nowhead);
        AgentExtract(&sim.nowhead,a); AgentExtract(&sim.nowhead,b);
        if(future) for(auto p:extra) {
            AgentExtract(&sim.nowhead,p); AgentAppend(&sim.nexthead,p);
            // Actual bound dispatch need not change this flag to G_NEXT.
            sim.grid->status[p->x][p->y]=p->status==B_UNBOUND?G_NEXT:G_NOW;
        }
        SetRNGSeed(seed);
        assert(sim.ReactionExecuteOpcode_Spatial(a,b)==1);
        const std::string actual=rng();
        SetRNGSeed(seed);
        bool occupied=std::strcmp(policy,"NATIVE_VACANCY") && RandomBetween0And1()<0.5;
        bool candidates=occupied?std::strcmp(layout,"protected")!=0:!std::strcmp(layout,"sparse");
        // No staged nonempty child at offset == visible length.
        if(offset==4) SetRNGSeed(seed); else if(candidates) RandomBetween0And1();
        assert(actual==rng());
        FILE *r=fopen("final-rng.txt","wx"); assert(r);
        assert(fwrite(actual.data(),1,actual.size(),r)==actual.size() && !fclose(r));
        std::set<s_ag *> live;
        for(int x=0;x<3;++x) for(int y=0;y<3;++y) if(auto p=sim.grid->grid[x][y]) assert(live.insert(p).second);
        assert(sim.agct==static_cast<unsigned long>(id+(offset<4)) && sim.energy==29);
        const bool replacement=offset<4 && occupied && candidates && !std::strcmp(policy,"STRATIFIED_REPLACE");
        int64_t refund=0;
#ifndef SM_ADMISSION_LEGACY
        for(auto n:sim.conservation.eviction_returns) refund+=n;
#endif
        assert(refund==(replacement?(hidden?3:1):0));
        assert(sim.conservation.retirement_returns==SpatialConservation::Counts{});
        assert(sim.conservation.decay==SpatialConservation::Counts{});
        assert(sim.conservation.event_index==1+replacement);
        const bool admitted=offset<4 && candidates && (!occupied || replacement);
        const bool cleanup=offset<4 && (offset==0 || strcmp(empty,"none"));
        assert(live.size()==static_cast<size_t>(id+admitted-replacement-cleanup));
        // Turn the two disjoint owned queues into a final stable inventory without
        // running another VM opcode. This is a directed interpreter fixture.
        while(sim.nexthead) { auto p=sim.nexthead; AgentExtract(&sim.nexthead,p); AgentAppend(&sim.nowhead,p); }
        sim.conservation.observe(1,"END",sim.nowhead);
        sim.scheduling.end(1,sim.nowhead,sim.conservation.event_index);
#ifndef SM_ADMISSION_LEGACY
        try { sim.admission.end(sim.conservation,sim.scheduling,*sim.grid,sim.nowhead,sim.nexthead,1); }
        catch(const std::exception &e) { sm_b003::AdmissionAdapter::fail(e.what()); }
#endif
        if(sim.retirement.journal) { assert(!fclose(sim.retirement.journal)); sim.retirement.journal=nullptr; }
        for(FILE **f:{&sim.conservation.journal,&sim.conservation.aggregate,&sim.conservation.buffers})
            if(*f) { assert(!fclose(*f)); *f=nullptr; }
        // Native bucket destructor owns each remaining actor and grid exactly once.
    }
    species.SpeciesListClear();
    return 0;
}
