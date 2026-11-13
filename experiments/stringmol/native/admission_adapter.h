// SM-B003 interpreter adapter. Requires native grid, conservation, scheduling,
// retirement types and RandomBetween0And1(), plus the component ledger patch.
#ifndef SM_B003_ADMISSION_ADAPTER_H
#define SM_B003_ADMISSION_ADAPTER_H
#include <climits>
#include <cstdlib>
#include <vector>
#include "randutil.h"
#include <map>
#include <memory>
#include <set>
#include "admission_journal.h"
#include "admission_transaction.h"

namespace sm_b003 {
class AdmissionAdapter {
    enum class Disposition { Unavailable, Vacancy, Reject, Replacement };
    struct Frame {
        std::map<int,s_ag *> agents;
        std::set<s_ag *> now, next;
    };
    struct Pending {
        bool active=false, irreversible=false, occupied=false, partial=false, admitted=false, cleaved=false;
        int active_id=-1, passive_id=-1, source=-1, offset=-1, child=-1, victim=-1, x=-1, y=-1;
        uint64_t tick=0, transaction=0, before_material=0, dispatch=0, eviction=0, death=0, cleave=0, birth=0, eligibility=0;
        Disposition disposition=Disposition::Unavailable;
    } pending;
    struct FreeAgent { void operator()(s_ag *p) const noexcept { if(p) AgentFreeAndNull(&p); } };
    // Explicit ownership of live prefix allocations outside grid/list inventory.
    // Fatal failures retain these owners; successful transfer clears them before
    // native destruction. No saved pointer is allowed to outlive its allocation.
    std::unique_ptr<s_ag,FreeAgent> proposal_child, detached_victim;
    Policy policy=Policy::Native;
    Schedule schedule=Schedule::Immediate;
    std::unique_ptr<Journal> journal;
    uint64_t proposals=0, evictions=0, partials=0, commits=0;
    int highest_id=-1;
    static void require(bool condition,const char *why) { if(!condition) throw std::runtime_error(why); }
    static const char *disposition_name(Disposition d) {
        switch(d) {
            case Disposition::Unavailable:return "NO_CANDIDATE";
            case Disposition::Vacancy:return "ADMIT_VACANCY";
            case Disposition::Reject:return "REJECT_OCCUPIED";
            case Disposition::Replacement:return "ADMIT_REPLACEMENT";
        }
        throw std::runtime_error("unknown disposition");
    }
    static std::string hex(const s_ag *p,unsigned size) {
        const char *digits="0123456789ABCDEF";
        std::string value; value.reserve(2*size);
        for(unsigned i=0;i<size;++i) { auto c=static_cast<unsigned char>(p->S[i]); value+=digits[c>>4]; value+=digits[c&15]; }
        return value;
    }
    static std::string vector(const SpatialConservation::Counts &counts) {
        std::string out;
        for(size_t i=0;i<counts.size();++i) { if(i) out+=';'; out+=std::to_string(counts[i]); }
        return out;
    }
    static bool flag(const char *name) {
        const char *value=std::getenv(name);
        require(!value || !std::strcmp(value,"0") || !std::strcmp(value,"1"),"invalid admission flag");
        return value && !std::strcmp(value,"1");
    }
    static Frame frame(smsprun &g,s_ag *now,s_ag *next,int active=-1,int passive=-1) {
        Frame f;
        std::set<s_ag *> cells;
        require(g.gridx>0 && g.gridx<=40 && g.gridy>0 && g.gridy<=40 && g.grid && g.status,"admission grid dimensions");
        for(int x=0;x<g.gridx;++x) {
            require(g.grid[x] && g.status[x],"admission grid column");
            for(int y=0;y<g.gridy;++y) {
                auto p=g.grid[x][y];
                if(!p) { require(g.status[x][y]==G_EMPTY,"admission empty status"); continue; }
                require(cells.insert(p).second && p->idx>=0 && f.agents.emplace(p->idx,p).second,"admission duplicate identity");
                require(p->set && p->x==x && p->y==y && p->S,"admission grid ownership");
                require(g.status[x][y]==G_NOW || g.status[x][y]==G_NEXT || g.status[x][y]==G_DOING,"admission occupied status");
            }
        }
        auto list=[&](s_ag *head,std::set<s_ag *> &out) {
            s_ag *previous=nullptr;
            for(auto p=head;p;p=p->next) {
                require(cells.count(p) && out.insert(p).second,"admission list identity/cycle");
                require(p->prev==previous,"admission backlink"); previous=p;
            }
        };
        list(now,f.now); list(next,f.next);
        for(const auto &entry:f.agents) {
            auto p=entry.second;
            auto owners=f.now.count(p)+f.next.count(p);
            require(owners<=1 && (p->idx==active || p->idx==passive || owners==1),"admission list ownership");
            if(p->status==B_UNBOUND) require(!p->pass && !p->exec,"unbound admission relation");
            else if(p->status==B_ACTIVE) require(!p->exec && cells.count(p->pass) && p->pass->status==B_PASSIVE && p->pass->exec==p,"active admission relation");
            else if(p->status==B_PASSIVE) require(!p->pass && cells.count(p->exec) && p->exec->status==B_ACTIVE && p->exec->pass==p,"passive admission relation");
            else require(false,"admission binding state");
        }
        return f;
    }
    static Row state_row(const Frame &f,s_ag *now,s_ag *next,uint64_t material,uint64_t boundary) {
        Row r;
        return r.number(Field::MaterialIndex,material).number(Field::BoundaryIndex,boundary)
            .set(Field::NowIds,SpatialScheduling::ids(now)).set(Field::NextIds,SpatialScheduling::ids(next)).number(Field::Population,f.agents.size());
    }
    void counters(Row &r,const SpatialConservation &m) const {
        r.number(Field::ProposalTotal,proposals).number(Field::EvictionTotal,evictions)
         .number(Field::PartialTotal,partials).number(Field::PartialCommitTotal,commits).set(Field::EvictionReturns,vector(m.eviction_returns));
    }
    static uint64_t increment(uint64_t value) { require(value<INT64_MAX,"admission counter overflow"); return value+1; }
public:
    bool enabled=false;
    bool observing() const { return bool(journal); }
    [[noreturn]] static void fail(const char *why) { std::fprintf(stderr,"SM-B003 fatal admission: %s\n",why); std::exit(EXIT_FAILURE); }
    static void fault(const char *phase) {
        const char *selected=std::getenv("STRINGMOL_ADMISSION_FAULT");
        if(selected && !std::strcmp(selected,phase)) throw std::runtime_error(phase);
    }
    void init(SpatialConservation &m,SpatialScheduling &s,const SpatialRetirement &r,smsprun &g,
              s_ag *now,s_ag *next,uint64_t horizon,unsigned radius,bool mutation) {
        enabled=flag("STRINGMOL_ADMISSION");
        if(!enabled) return;
        require(m.enabled && m.initialized && m.routed && !m.sequester && m.size==2001,"admission conservation background");
        require(r.enabled && !r.retire && s.enabled && !radius && !mutation,"admission RETAIN/global/zero-mutation background");
        if(!std::strcmp(s.policy,"IMMEDIATE")) schedule=Schedule::Immediate;
        else if(!std::strcmp(s.policy,"DELAY500")) schedule=Schedule::Delay500;
        else require(false,"admission scheduling policy");
        const char *p=std::getenv("STRINGMOL_ADMISSION_POLICY");
        require(p,"missing admission policy");
        if(!std::strcmp(p,"NATIVE_VACANCY")) policy=Policy::Native;
        else if(!std::strcmp(p,"STRATIFIED_REJECT")) policy=Policy::Reject;
        else if(!std::strcmp(p,"STRATIFIED_REPLACE")) policy=Policy::Replace;
        else require(false,"unknown admission policy");
        const char *injected=std::getenv("STRINGMOL_ADMISSION_FAULT");
        if(injected) {
            bool known=false;
            for(const char *name:{"validate","unlink","grid","refund","ready","publication","material","death","lineage","free","birth","cleave","complete","journal"}) known|=!std::strcmp(name,injected);
            require(known,"unknown admission fault");
        }
        auto f=frame(g,now,next);
        require(!next,"initial admission next queue");
        for(const auto &entry:f.agents) highest_id=std::max(highest_id,entry.first);
        if(flag("STRINGMOL_ADMISSION_LOG")) {
            require(m.logging && s.observing() && r.logging,"admission requires inherited journals");
            journal.reset(new Journal("admission_events007.csv",policy,schedule,horizon,g.gridx,g.gridy));
            auto row=state_row(f,now,next,m.event_index,s.index); counters(row,m);
            journal->emit(Event::Start,0,0,row);
        }
    }
    void own_proposal(s_ag *child) {
        if(!enabled) return;
        require(child && !pending.active && !proposal_child && !detached_victim,"nested proposal ownership");
        proposal_child.reset(child);
    }
    void release_proposal() { if(enabled) proposal_child.release(); }
    // Returns only a placement decision; native source healing and failed-child
    // destruction remain in the unchanged opcode body. No fallback or resampling.
    bool place(SpatialConservation &m,SpatialScheduling &s,smsprun &g,s_ag *&now,s_ag *&next,
               s_ag *active,s_ag *passive,s_ag *source,int offset,s_ag *child,uint64_t tick,
               const std::function<void(s_ag *)> &lineage_death) {
        require(enabled && !pending.active && proposal_child.get()==child,"nested/unowned admission proposal");
        auto f=frame(g,now,next,active->idx,passive->idx);
        require(f.agents.count(active->idx) && f.agents.at(active->idx)==active &&
                f.agents.count(passive->idx) && f.agents.at(passive->idx)==passive,"missing admission participants");
        require((source==active || source==passive) && offset>=0 && static_cast<size_t>(offset)<std::strlen(source->S),"admission source offset");
        require(child && child->idx>highest_id && !f.agents.count(child->idx) && child->S && child->S[0],"admission proposed identity");
        m.count(source); m.count(child);
        const std::string suffix=source->S+offset;
        std::string padded=suffix; padded.resize(m.size,'\0');
        require(std::string(child->S,m.size)==padded,"admission staged suffix");
        std::vector<std::pair<int,int>> vacant,occupied;
        for(int x=0;x<g.gridx;++x) for(int y=0;y<g.gridy;++y) {
            auto p=g.grid[x][y];
            if(!p) vacant.emplace_back(x,y);
            else if(p!=active && p!=passive && p->status==B_UNBOUND && p->S[0]) occupied.emplace_back(x,y);
        }
        pending=Pending{}; pending.active=true; pending.tick=tick;
        pending.active_id=active->idx; pending.passive_id=passive->idx; pending.source=source->idx;
        pending.offset=offset; pending.child=child->idx; pending.dispatch=s.index; pending.before_material=m.event_index;
        pending.transaction=increment(proposals); highest_id=child->idx;
        double channel=0,rank=0;
        if(policy!=Policy::Native) { channel=RandomBetween0And1(); uniform_bits(channel); pending.occupied=channel<0.5; }
        const auto &candidates=pending.occupied?occupied:vacant;
        if(!candidates.empty()) {
            rank=RandomBetween0And1(); uniform_bits(rank);
            auto target=candidates.at(static_cast<size_t>(rank*candidates.size()));
            pending.x=target.first; pending.y=target.second;
            pending.disposition=!pending.occupied?Disposition::Vacancy:policy==Policy::Replace?Disposition::Replacement:Disposition::Reject;
        }
        auto victim=pending.occupied && pending.x>=0?g.grid[pending.x][pending.y]:nullptr;
        pending.victim=victim?victim->idx:-1; pending.partial=victim && offset>0;
        pending.admitted=pending.disposition==Disposition::Vacancy || pending.disposition==Disposition::Replacement;
        if(journal) {
            auto row=state_row(f,now,next,m.event_index,s.index);
            row.number(Field::Active,active->idx).number(Field::Passive,passive->idx).number(Field::Source,source->idx)
               .number(Field::Offset,offset).number(Field::Child,child->idx).set(Field::Channel,pending.occupied?"OCCUPIED":"VACANT")
               .number(Field::VacantCount,vacant.size()).number(Field::OccupiedCount,occupied.size())
               .set(Field::SourceBuffer,hex(source,m.size)).set(Field::ChildBuffer,hex(child,m.size)).number(Field::PartialOpportunity,pending.partial);
            if(policy!=Policy::Native) row.set(Field::ChannelBits,uniform_bits(channel));
            if(pending.x>=0) row.number(Field::TargetX,pending.x).number(Field::TargetY,pending.y).set(Field::RankBits,uniform_bits(rank));
            if(victim) row.number(Field::Victim,victim->idx).number(Field::VictimEligibleTick,victim->eligible_tick)
                .set(Field::VictimOwner,f.now.count(victim)?"NOW":"NEXT").set(Field::VictimBuffer,hex(victim,m.size));
            journal->emit(Event::Begin,tick,pending.transaction,row);
        }
        if(pending.disposition==Disposition::Replacement) {
            ReplacementTransaction transaction(g,now,next,m,active,passive,child,victim);
            transaction.stage([](ReplacementTransaction::Checkpoint step) {
                const char *names[]={"validate","unlink","grid","refund","ready"};
                fault(names[static_cast<size_t>(step)]);
            });
            detached_victim.reset(victim);
            transaction.publish([&] {
                pending.irreversible=true; fault("publication");
                m.material(tick,"EVICT","REMOVED",transaction.before(),{});
                pending.eviction=m.event_index; fault("material");
                s.death(tick,victim,"EVICT",m.event_index); pending.death=s.index; fault("death");
                lineage_death(victim); fault("lineage");
            });
            detached_victim.release(); // the primitive now owns exactly-once freeing
            transaction.release_victim(); fault("free");
        } else if(pending.disposition==Disposition::Vacancy) {
            const int old_x=child->x,old_y=child->y; const bool old_set=child->set;
            const auto status=g.status[pending.x][pending.y];
            try {
                fault("validate");
                g.grid[pending.x][pending.y]=child; g.status[pending.x][pending.y]=G_NEXT;
                child->x=pending.x; child->y=pending.y; child->set=true;
                fault("grid"); fault("ready");
            } catch(...) {
                g.grid[pending.x][pending.y]=nullptr; g.status[pending.x][pending.y]=status;
                child->x=old_x; child->y=old_y; child->set=old_set;
                throw;
            }
        } else fault("validate");
        return pending.admitted;
    }
    // The original placement/failed-placement completion starts here. This does
    // not grant rollback of inherited child destruction/source/species mutations.
    void native_completion() {
        if(enabled && pending.active) { pending.irreversible=true; release_proposal(); }
    }
    void born() { if(enabled && pending.active) fault("birth"); }
    void cleaved(SpatialConservation &m,SpatialScheduling &s,const s_ag *child) {
        if(!enabled || !pending.active) return;
        require(pending.irreversible && pending.admitted==bool(child),"admission/native placement differs");
        require(m.event_index==static_cast<int64_t>(pending.before_material+1+(pending.disposition==Disposition::Replacement)),"admission material sequence");
        pending.cleave=m.event_index; pending.cleaved=true;
        if(child) {
            require(child->idx==pending.child && child->x==pending.x && child->y==pending.y,"admission child identity/cell differs");
            pending.birth=s.index; pending.eligibility=child->eligible_tick;
        }
        fault("cleave");
    }
    void complete(SpatialConservation &m,SpatialScheduling &s,smsprun &g,s_ag *now,s_ag *next,uint64_t tick) {
        if(!enabled || !pending.active) return;
        require(pending.cleaved && !proposal_child && !detached_victim && pending.tick==tick && m.event_index==static_cast<int64_t>(pending.cleave),"admission completion linkage");
        auto f=frame(g,now,next);
        if(pending.admitted) require(f.agents.count(pending.child) && f.next.count(f.agents.at(pending.child)),"admission child completion ownership");
        else require(!f.agents.count(pending.child),"rejected child survives");
        if(pending.disposition==Disposition::Replacement) require(!f.agents.count(pending.victim),"evicted victim survives");
        proposals=increment(proposals);
        const bool replaced=pending.disposition==Disposition::Replacement;
        if(replaced) evictions=increment(evictions);
        if(pending.partial) partials=increment(partials);
        if(replaced && pending.partial) commits=increment(commits);
        fault("complete");
        if(journal) {
            auto row=state_row(f,now,next,m.event_index,s.index); counters(row,m);
            row.set(Field::Disposition,disposition_name(pending.disposition)).number(Field::CleaveMaterialIndex,pending.cleave)
               .number(Field::SourceAlive,f.agents.count(pending.source));
            if(replaced) row.number(Field::EvictionMaterialIndex,pending.eviction).number(Field::DeathIndex,pending.death);
            if(pending.admitted) row.number(Field::BirthIndex,pending.birth).number(Field::ChildEligibleTick,pending.eligibility);
            journal->emit(Event::Resolve,tick,pending.transaction,row); fault("journal");
        }
        pending=Pending{};
    }
    void end(SpatialConservation &m,SpatialScheduling &s,smsprun &g,s_ag *now,s_ag *next,uint64_t tick) {
        if(!enabled) return;
        require(!pending.active && !next,"unfinished admission at END");
        auto f=frame(g,now,next);
        if(journal) {
            // Terminal witness only: never inspect dormant, possibly uninitialized heads.
            std::unique_ptr<FILE,int(*)(FILE *)> out(fopen("vm_end007.csv","wx"),fclose);
            require(bool(out),"terminal VM journal open");
            require(fputs("tick,id,role,partner,eligible_tick,x,y,it,rt,wt,ft,i0,i1,r0,r1,w0,w1,f0,f1\n",out.get())>=0,"terminal VM header");
            for(const auto &entry:f.agents) {
                s_ag *a=entry.second;
                const bool active=a->status==B_ACTIVE, passive=a->status==B_PASSIVE;
                const int partner=active?a->pass->idx:passive?a->exec->idx:-1;
                require(fprintf(out.get(),"%llu,%d,%s,%d,%llu,%d,%d",static_cast<unsigned long long>(tick),a->idx,
                    active?"ACTIVE":passive?"PASSIVE":"UNBOUND",partner,static_cast<unsigned long long>(a->eligible_tick),a->x,a->y)>=0,"terminal VM identity");
                if(active) {
                    require(fprintf(out.get(),",%d,%d,%d,%d",a->it,a->rt,a->wt,a->ft)>=0,"terminal VM toggles");
                    char **heads[]={a->i,a->r,a->w,a->f};
                    for(auto head:heads) for(int side=0;side<2;++side)
                        require(fprintf(out.get(),",%lld",static_cast<long long>(SpatialConservation::allocated_offset(head[side],side?a->S:a->pass->S,m.size)))>=0,"terminal VM heads");
                } else require(fputs(",,,,,,,,,,,,",out.get())>=0,"terminal VM dormant fields");
                require(fputc('\n',out.get())!=EOF,"terminal VM row");
            }
            require(!fflush(out.get()) && !ferror(out.get()),"terminal VM flush");
            require(!fclose(out.release()),"terminal VM close");
            auto row=state_row(f,now,next,m.event_index,s.index); counters(row,m); journal->emit(Event::End,tick,0,row);
        }
    }
};
} // namespace sm_b003
#endif
