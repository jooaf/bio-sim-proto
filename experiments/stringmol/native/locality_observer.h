// SM-XL001 terminal observation only. Never sample RNG or modify simulator state.
#ifndef SM_XL001_OBSERVER_H
#define SM_XL001_OBSERVER_H
#include <map>
#include "mt19937-2.h"
static void xl_terminal(const Stringmol_Spatial &sim, unsigned tick) {
    if (!sim.scheduling.observing()) return;
    FILE *out=fopen("xl_vm_end.csv","wx");
    if(!out) SpatialScheduling::fail("XL terminal open");
    fprintf(out,"tick,id,role,partner,eligible_tick,x,y,it,rt,wt,ft,i0,i1,r0,r1,w0,w1,f0,f1\n");
    std::map<int,const s_ag *> agents;
    for(const s_ag *a=sim.nowhead;a;a=a->next) agents.emplace(a->idx,a);
    for(const auto &entry:agents) {
        const s_ag *a=entry.second;
        bool active=a->status==B_ACTIVE,passive=a->status==B_PASSIVE;
        int partner=active?a->pass->idx:passive?a->exec->idx:-1;
        fprintf(out,"%u,%d,%s,%d,%llu,%d,%d",tick,a->idx,active?"ACTIVE":passive?"PASSIVE":"UNBOUND",partner,
                (unsigned long long)a->eligible_tick,a->x,a->y);
        if(active) {
            fprintf(out,",%d,%d,%d,%d",a->it,a->rt,a->wt,a->ft);
            char *const *heads[]={a->i,a->r,a->w,a->f};
            for(auto head:heads) for(int side=0;side<2;++side)
                fprintf(out,",%lld",(long long)SpatialConservation::allocated_offset(head[side],side?a->S:a->pass->S,sim.conservation.size));
        } else fputs(",,,,,,,,,,,,",out);
        fputc('\n',out);
    }
    if(fflush(out) || ferror(out) || fclose(out)) SpatialScheduling::fail("XL terminal close");
    out=fopen("xl_rng_end.txt","wx");
    if(!out) SpatialScheduling::fail("XL RNG open");
    MersenneTwisterPrintStatusToFile(out);
    if(fflush(out) || ferror(out) || fclose(out)) SpatialScheduling::fail("XL RNG close");
}
#endif
