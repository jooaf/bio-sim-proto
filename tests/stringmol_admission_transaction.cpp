// Native heap/grid/list/material component tests. NOT a population assay.
#include <array>
#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <vector>
#include "default_config.h"
#include "alignment.h"
#include "rules.h"
#include "agent.h"
#include "SMspp.h"
#include "opcodes.h"
#include "stringPM.h"
#include "sm_conservation.h"
#include "experiments/stringmol/native/admission_transaction.h"
using Tx=sm_b003::ReplacementTransaction;
static s_ag *tracked=nullptr;
static int victim_frees=0;
extern "C" int __real__Z16AgentFreeAndNullPP4s_ag(s_ag **);
extern "C" int __wrap__Z16AgentFreeAndNullPP4s_ag(s_ag **p) {
    if (*p == tracked) ++victim_frees;
    return __real__Z16AgentFreeAndNullPP4s_ag(p);
}
struct World {
    std::array<s_ag *,6> owned{};
    std::array<std::array<s_ag *,2>,3> cells{};
    std::array<std::array<s_gstatus,2>,3> statuses{};
    std::array<s_ag **,3> columns{};
    std::array<s_gstatus *,3> status_columns{};
    smsprun grid{};
    s_ag *now=nullptr, *next=nullptr;
    SpatialConservation m;
    World(bool future, int position, bool hidden) {
        const char *text[]={"ABC","DEF","A","X","Y","BC"};
        for (int i=0; i<6; ++i) {
            owned[i]=static_cast<s_ag *>(std::calloc(1,sizeof(s_ag))); assert(owned[i]);
            auto p=owned[i]; p->S=static_cast<char *>(std::calloc(2001,1)); assert(p->S);
            std::strcpy(p->S,text[i]); p->len=std::strlen(p->S); p->idx=i; p->status=B_UNBOUND;
            p->x=p->y=-1;
        }
        if (hidden) { owned[2]->S[2]='B'; owned[2]->S[3]='B'; }
        owned[2]->eligible_tick=999; // young unbound children are NOT protected
        owned[0]->status=B_ACTIVE; owned[1]->status=B_PASSIVE;
        owned[0]->pass=owned[1]; owned[1]->exec=owned[0];
        grid.gridx=3; grid.gridy=2;
        for(int x=0;x<3;++x) { columns[x]=cells[x].data(); status_columns[x]=statuses[x].data(); }
        grid.grid=columns.data(); grid.status=status_columns.data();
        for(int i=0;i<5;++i) {
            auto p=owned[i]; p->x=i/2; p->y=i%2; p->set=true;
            cells[p->x][p->y]=p; statuses[p->x][p->y]=i<2?G_DOING:future?G_NEXT:G_NOW;
        }
        std::vector<s_ag *> queue={owned[3],owned[4]}; queue.insert(queue.begin()+position,owned[2]);
        for(auto p:queue) AgentAppend(future?&next:&now,p);
        m.enabled=m.initialized=m.routed=m.logging=true; m.size=2001;
        for(int i=0;i<5;++i) m.stable_molecular=SpatialConservation::sum(m.stable_molecular,m.count(owned[i]));
        m.initial=m.stable_molecular;
        tracked=owned[2];
    }
    ~World() {
        for(FILE *f:{m.journal,m.aggregate,m.buffers}) if(f) assert(std::fclose(f)==0);
        for(auto p:owned) if(p) { std::free(p->S); std::free(p); }
    }
    std::string snapshot() const {
        std::ostringstream s; s << now << ',' << next << ',' << m.event_index << ';';
        s << m.enabled << m.initialized << m.routed << m.sequester << m.logging << ',' << m.size << ','
          << m.attempts << ',' << m.growth << ',' << m.positive_bytes << ',' << m.contraction_bytes << ';';
        s << m.journal << ',' << m.aggregate << ',' << m.buffers << ';';
        for(auto n:m.categories) s << n << ',';
        for(const auto *counts:{&m.pool,&m.minimum,&m.eviction_returns,&m.stable_molecular,&m.initial,&m.initial_pool,
                               &m.retirement_returns,&m.decay,&m.failed,&m.discard,&m.missing,&m.waste,
                               &m.decay_pool,&m.decay_waste,&m.withdrawals,&m.returns}) for(auto n:*counts) s << n << ',';
        for(const auto &entry:m.proposal) s << static_cast<void *>(entry.first) << ':' << int(entry.second) << ';';
        for(auto p:owned) {
            s << p << ';'; if(!p) continue;
            s << static_cast<void *>(p->S) << ',' << p->label << ',' << p->len << ',' << p->ect << ',' << p->nbind << ','
              << p->it << ',' << p->rt << ',' << p->wt << ',' << p->ft << ',' << p->spp << ',' << p->pp << ',';
            s << p->idx << ',' << p->prev << ',' << p->next << ',' << p->pass << ',' << p->exec << ','
              << p->x << ',' << p->y << ',' << p->set << ',' << p->status << ',' << p->biomass << ',' << p->eligible_tick;
            for(int t=0;t<2;++t) for(char *h:{p->i[t],p->r[t],p->w[t],p->f[t]}) s << ':' << static_cast<void *>(h);
            s.write(p->S,2001);
        }
        for(int x=0;x<3;++x) for(int y=0;y<2;++y) s << cells[x][y] << ',' << statuses[x][y] << ';';
        return s.str();
    }
    void reconcile_completed_cleave() {
        auto before=m.state(owned[0],owned[1]);
        auto mass=SpatialConservation::sum(m.count(owned[0]),m.count(owned[1]));
        // The interpreter integration remains pending. Here only its known
        // partial-source healing is supplied to exercise real accounting code.
        owned[0]->S[1]=owned[0]->S[2]=0; owned[0]->len=1;
        m.cleave(mass,owned[0],owned[1],owned[5]);
        m.material(10,"CLEAVE","PLACED",before,m.state(owned[0],owned[1],owned[5]));
        for(int id:{5,0,1}) { AgentAppend(&next,owned[id]); statuses[owned[id]->x][owned[id]->y]=G_NEXT; }
        // A read-only concatenated view; do not change the two native queues.
        std::vector<s_ag> view;
        for(auto p:owned) if(p) view.push_back(*p);
        for(size_t i=0;i<view.size();++i) view[i].next=i+1<view.size()?&view[i+1]:nullptr;
        m.observe(10,"TEST_COMPLETE",view.data());
        assert(m.event_index==2 && m.retirement_returns==Tx::Counts{} && m.decay==Tx::Counts{} &&
               m.failed==Tx::Counts{} && m.discard==Tx::Counts{} && m.waste==Tx::Counts{});
    }
};
static void rejects(const std::function<void()> &fn) {
    bool rejected=false; try { fn(); } catch(const std::runtime_error &) { rejected=true; }
    assert(rejected);
}
int main(int argc,char **argv) {
    assert(argc==5);
    const std::string mode=argv[1];
    World w(std::atoi(argv[2]),std::atoi(argv[3]),std::atoi(argv[4]));
    if(mode.find("-bound")!=std::string::npos) {
        assert(w.next);
        auto a=w.owned[3], p=w.owned[4];
        a->status=B_ACTIVE; p->status=B_PASSIVE; a->pass=p; p->exec=a;
        for(int t=0;t<2;++t) a->i[t]=a->r[t]=a->w[t]=a->f[t]=t?a->S:p->S;
        w.statuses[a->x][a->y]=w.statuses[p->x][p->y]=G_NOW;
    }
    s_ag *victim=w.owned[2];
    char *original_child_buffer=w.owned[5]->S;
    if(mode=="protected") victim=w.owned[0];
    if(mode=="bound") victim->status=B_ACTIVE;
    if(mode=="empty") victim->S[0]=0;
    if(mode=="inbound") w.owned[3]->exec=victim;
    if(mode=="head") w.owned[0]->r[0]=victim->S+1;
    if(mode=="dual") { if(w.now) w.next=w.now; else w.now=w.next; }
    if(mode=="unowned") AgentExtract(w.now?&w.now:&w.next,victim);
    if(mode=="reuse") w.owned[5]->idx=victim->idx;
    if(mode=="overflow") w.m.pool[0]=INT64_MAX;
    if(mode=="ledger-overflow") w.m.eviction_returns[0]=INT64_MAX;
    if(mode=="negative-pool") w.m.pool[0]=-1;
    if(mode=="invalid-min") w.m.minimum[0]=1;
    if(mode=="invalid-grid-status") w.grid.status[1][0]=G_EMPTY;
    if(mode=="grid-duplicate") w.grid.grid[2][1]=victim;
    if(mode=="duplicate-id") w.owned[3]->idx=victim->idx;
    if(mode=="backlink") victim->prev=nullptr;
    if(mode=="child-owned") w.owned[5]->set=true;
    if(mode=="child-alias") w.owned[5]->S=victim->S;
    if(mode=="cycle") { auto p=w.now?w.now:w.next; while(p->next) p=p->next; p->next=w.now?w.now:w.next; }
    const auto baseline=w.snapshot();
    if(mode=="protected" || mode=="bound" || mode=="empty" || mode=="inbound" || mode=="head" ||
       mode=="dual" || mode=="unowned" || mode=="reuse" || mode=="overflow" || mode=="ledger-overflow" || mode=="cycle" ||
       mode=="negative-pool" || mode=="invalid-min" || mode=="grid-duplicate" || mode=="duplicate-id" ||
       mode=="backlink" || mode=="child-owned" || mode=="child-alias" || mode=="invalid-grid-status") {
        rejects([&]{ Tx t(w.grid,w.now,w.next,w.m,w.owned[0],w.owned[1],w.owned[5],victim); });
        assert(w.snapshot()==baseline && victim_frees==0);
        w.owned[5]->S=original_child_buffer;
        return 0;
    }
    {
        Tx t(w.grid,w.now,w.next,w.m,w.owned[0],w.owned[1],w.owned[5],victim);
        if(mode=="free-early") { rejects([&]{t.release_victim();}); assert(w.snapshot()==baseline); return 0; }
        if(mode.compare(0,6,"fault-")==0) {
            int point=std::atoi(mode.c_str()+6), reached=0;
            rejects([&]{t.stage([&](Tx::Checkpoint c){
                if(static_cast<int>(c)==point) {
                    ++reached;
                    if(point>=1) assert(!victim->next && !victim->prev);
                    if(point>=2) assert(w.grid.grid[1][0]==w.owned[5]);
                    if(point>=3) assert(w.m.pool==t.units() && w.m.eviction_returns==t.units());
                    throw std::runtime_error("injected prepublication fault");
                }
            });});
            assert(reached==1 && t.state()==Tx::Phase::Aborted && w.snapshot()==baseline);
            rejects([&]{t.stage();}); assert(victim_frees==0); return 0;
        }
        t.stage();
        assert(w.grid.grid[1][0]==w.owned[5] && w.owned[5]->set && w.m.pool==t.units() && w.m.eviction_returns==t.units());
        assert(t.units()[0]==1 && t.units()[1]==(std::atoi(argv[4])?2:0));
        if(mode=="abandon" || mode=="free-staged") {
            if(mode=="free-staged") rejects([&]{t.release_victim();});
            // destructor must restore, without freeing
        }
        else if(mode=="publish-before" || mode=="publish-after") {
            rejects([&]{ t.publish([&]{
                if(mode=="publish-after") w.m.material(10,"EVICT","REMOVED",t.before(),{});
                throw std::runtime_error("injected publication fault");
            }); });
            assert(t.state()==Tx::Phase::FailedAfterPublication && w.m.pool==t.units() && w.grid.grid[1][0]==w.owned[5]);
            rejects([&]{t.stage();}); rejects([&]{t.release_victim();});
            assert(victim_frees==0); std::fputs("POST_PUBLICATION_FATAL\n",stderr); return 23;
        } else {
            assert(mode=="success" || mode=="success-bound");
            t.publish([&]{w.m.material(10,"EVICT","REMOVED",t.before(),{});});
            t.release_victim(); w.owned[2]=nullptr;
            assert(victim_frees==1 && t.state()==Tx::Phase::Freed);
            rejects([&]{t.release_victim();}); rejects([&]{t.stage();});
            w.reconcile_completed_cleave();
            std::puts("EVICT/CLEAVE and both reconciliation sites passed");
        }
    }
    if(mode=="abandon" || mode=="free-staged") assert(w.snapshot()==baseline && victim_frees==0);
    return 0;
}
