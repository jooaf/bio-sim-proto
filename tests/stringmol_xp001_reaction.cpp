// SM-XP001: bounded isolated native two-participant reaction, not a population run.
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
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
#include "sm_spatial.h"
#include "mt19937-2.h"
#include "randutil.h"
#include "setupSM.h"

static void env(const char *k,const char *v) { assert(!setenv(k,v,1)); }
static void hex(FILE *f,const char *p,unsigned n) {
    for(unsigned i=0;i<n;++i) fprintf(f,"%02X",static_cast<unsigned char>(p[i]));
}
int main(int argc,char **argv) {
    assert(argc==9); // sequenceA sequenceB seed matrix observe output-summary pool-mode amount
    const bool observing=atoi(argv[5]);
    env("STRINGMOL_CONSERVATION","1"); env("STRINGMOL_POOL_MODE",argv[7]);
    env("STRINGMOL_POOL_AMOUNT",argv[8]); env("STRINGMOL_DECAY_DESTINATION","recycle");
    env("STRINGMOL_CONSERVATION_LOG",observing?"1":"0");
    env("STRINGMOL_SCHEDULING","1"); env("STRINGMOL_SCHEDULING_POLICY","IMMEDIATE");
    env("STRINGMOL_SCHEDULING_LOG",observing?"1":"0");
    env("STRINGMOL_SOURCE_RETENTION","1"); env("STRINGMOL_SOURCE_DISPOSITION","RETAIN");
    env("STRINGMOL_RETIREMENT_LOG",observing?"1":"0");
    env("STRINGMOL_LINEAGE_LOG","0");
    SMspp species;
    {
        Stringmol_Spatial sim(&species);
        sim.maxl0=2001; sim.maxl=2000; sim.domut=false;
        assert(!sim.load_table_matrix(argv[4])); sim.grid=sim.init_smprun(3,3);
        sim.placement_radius=0; sim.energy=10000; sim.timestep=0; sim.agct=2;
        auto make=[&](char *s,int id) {
            auto p=AgentMakeWithSequence(s,'Q',id,sim.maxl0); assert(p);
            species.SpeciesListUpdate(p,'I',1,nullptr,nullptr,0,0,sim.maxl0);
            AgentPlaceOnGrid(p,sim.grid,id,0); sim.grid->status[id][0]=G_NOW;
            AgentAppend(&sim.nowhead,p); return p;
        };
        auto a=make(argv[1],0),b=make(argv[2],1);
        sim.conservation.init(sim.nowhead,sim.maxl0,sim.blosum->key);
        sim.scheduling.init(sim.nowhead,5000,observing); sim.retirement.init(sim.conservation);
        sim.conservation.observe(0,"START",sim.nowhead);
        SetRNGSeed(strtoul(argv[3],nullptr,10));
        align sw={}; float probability=AgentsAlign(a,b,&sw,sim.blosum,sim.swlist);
        sim.ReactionSetupExecution(a,b,&sw);
        auto active=a->status==B_ACTIVE?a:b; auto passive=active==a?b:a;
        const int active_id=active->idx;
        unsigned steps=0; std::string stop="CAP";
        for(;steps<5000;) {
            if(active->status!=B_ACTIVE) { stop="UNBOUND"; break; }
            const bool cleavage=*(active->i[active->it])=='%';
            AgentExtract(&sim.nowhead,active); AgentExtract(&sim.nowhead,passive);
            sim.timestep=steps; sim.ReactionExecuteOpcode_Spatial(active,passive); ++steps;
            while(sim.nexthead) { auto p=sim.nexthead; AgentExtract(&sim.nexthead,p); AgentAppend(&sim.nowhead,p); }
            if(cleavage) { stop="FIRST_CLEAVAGE"; break; } // may have freed participants
        }
        sim.conservation.observe(steps,"END",sim.nowhead);
        sim.scheduling.end(steps,sim.nowhead,sim.conservation.event_index);
        FILE *f=fopen(argv[6],"wx"); assert(f);
        fprintf(f,"{\"active_id\":%d,\"probability\":%.9g,\"s1\":%d,\"s2\":%d,\"steps\":%u,\"stop\":\"%s\",\"buffers\":{",active_id,probability,sw.s1,sw.s2,steps,stop.c_str());
        bool first=true;
        for(auto p=sim.nowhead;p;p=p->next) {
            fprintf(f,"%s\"%d\":\"",first?"":",",p->idx); first=false;
            hex(f,p->S,sim.maxl0); fprintf(f,"\"");
        }
        fprintf(f,"}}\n"); assert(!fclose(f));
        FILE *rng=fopen("final-rng.txt","wx"); assert(rng);
        MersenneTwisterPrintStatusToFile(rng); assert(!fclose(rng));
        for(FILE **out:{&sim.conservation.journal,&sim.conservation.aggregate,&sim.conservation.buffers,&sim.scheduling.journal,&sim.retirement.journal})
            if(*out) { assert(!fclose(*out)); *out=nullptr; }
    }
    species.SpeciesListClear();
}
