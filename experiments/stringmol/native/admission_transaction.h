// SM-B003 reversible replacement primitive. Requires native agent/grid/conservation
// types and the eviction-ledger component patch. No selector, RNG or assay launcher.
#ifndef SM_B003_ADMISSION_TRANSACTION_H
#define SM_B003_ADMISSION_TRANSACTION_H
#include <functional>
#include <set>
#include <stdexcept>

namespace sm_b003 {
class ReplacementTransaction {
public:
    enum class Phase { Prepared, Staged, Aborted, Publishing, Published, FailedAfterPublication, Freed };
    enum class Checkpoint { Validated, Unlinked, Grid, Refund, Ready };
    using Fault = std::function<void(Checkpoint)>;
    using Counts = SpatialConservation::Counts;
private:
    smsprun &grid;
    s_ag *&now, *&next;
    SpatialConservation &material;
    s_ag *victim, *child;
    s_ag *old_now=nullptr, *old_next=nullptr, *previous=nullptr, *following=nullptr;
    bool in_now=false, old_set=false;
    int x=0, y=0, child_x=0, child_y=0;
    s_gstatus old_status=G_EMPTY;
    Counts old_pool{}, old_minimum{}, old_returns{}, new_pool{}, new_returns{}, refund{};
    SpatialConservation::State removed_state;
    Phase phase=Phase::Prepared;
    static void require(bool ok, const char *why) { if (!ok) throw std::runtime_error(why); }
    static bool overlaps(const char *a, const char *b, unsigned size) {
        const uintptr_t left=reinterpret_cast<uintptr_t>(a), right=reinterpret_cast<uintptr_t>(b);
        return left <= right ? right-left < size : left-right < size;
    }
    static std::set<s_ag *> list(s_ag *head, const std::set<s_ag *> &live) {
        std::set<s_ag *> seen;
        s_ag *prev=nullptr;
        for (s_ag *p=head; p; p=p->next) {
            require(live.count(p) && seen.insert(p).second, "unknown/cyclic list member");
            require(p->prev == prev, "list backlink"); prev=p;
        }
        return seen;
    }
    void rollback() noexcept {
        now=old_now; next=old_next;
        victim->prev=previous; victim->next=following;
        if (previous) previous->next=victim;
        if (following) following->prev=victim;
        grid.grid[x][y]=victim; grid.status[x][y]=old_status;
        child->x=child_x; child->y=child_y; child->set=old_set;
        material.pool=old_pool; material.minimum=old_minimum; material.eviction_returns=old_returns;
        phase=Phase::Aborted;
    }
public:
    ReplacementTransaction(smsprun &g, s_ag *&current, s_ag *&future, SpatialConservation &m,
                           s_ag *active, s_ag *passive, s_ag *proposed, s_ag *incumbent):
        grid(g), now(current), next(future), material(m), victim(incumbent), child(proposed) {
        require(m.enabled && m.initialized && m.routed && !m.sequester && m.size >= 2, "replacement requires recycling");
        require(g.gridx > 0 && g.gridx <= 40 && g.gridy > 0 && g.gridy <= 40 && g.grid && g.status, "grid dimensions");
        require(active && passive && active != passive && child && victim && child != victim &&
                child != active && child != passive && victim != active && victim != passive, "participant/victim identities");
        require(active->status == B_ACTIVE && passive->status == B_PASSIVE && active->pass == passive && passive->exec == active, "bound participants");
        require(victim->status == B_UNBOUND && !victim->pass && !victim->exec && victim->S && victim->S[0], "eligible unbound incumbent");
        require(child->status == B_UNBOUND && !child->pass && !child->exec && !child->prev && !child->next && !child->set && child->S && child->S[0], "unpublished child");
        std::set<s_ag *> live;
        std::set<int> identities;
        for (int xx=0; xx<g.gridx; ++xx) {
            require(g.grid[xx] && g.status[xx], "grid column");
            for (int yy=0; yy<g.gridy; ++yy) {
                s_ag *p=g.grid[xx][yy];
                if (!p) { require(g.status[xx][yy] == G_EMPTY, "empty cell status"); continue; }
                require(p != child && live.insert(p).second && p->idx >= 0 && identities.insert(p->idx).second, "duplicate grid identity");
                require(p->set && p->x == xx && p->y == yy && p->S, "grid coordinate/ownership");
                require(!overlaps(p->S, child->S, m.size), "child buffer aliases live material");
                if (p != victim) {
                    require(!overlaps(p->S, victim->S, m.size) && p->pass != victim && p->exec != victim, "incoming incumbent reference");
                    const uintptr_t base=reinterpret_cast<uintptr_t>(victim->S);
                    for (int t=0; t<2; ++t) for (const char *head: {p->i[t], p->r[t], p->w[t], p->f[t]}) {
                        const uintptr_t address=reinterpret_cast<uintptr_t>(head);
                        require(!head || address < base || address-base > m.size, "incoming incumbent head");
                    }
                }
            }
        }
        require(live.count(active) && live.count(passive) && live.count(victim) && child->idx >= 0 && !identities.count(child->idx), "missing/reused identity");
        const auto current_nodes=list(now,live), future_nodes=list(next,live);
        for (auto p: live) {
            const int owners=current_nodes.count(p)+future_nodes.count(p);
            require(owners <= 1 && (p == active || p == passive || owners == 1), "unique list ownership");
            if (p != active && p != passive)
                require(g.status[p->x][p->y] == (current_nodes.count(p)?G_NOW:G_NEXT), "queue/grid status mismatch");
        }
        in_now=current_nodes.count(victim);
        x=victim->x; y=victim->y; old_status=g.status[x][y];
        old_now=now; old_next=next; previous=victim->prev; following=victim->next;
        child_x=child->x; child_y=child->y; old_set=child->set;
        old_pool=m.pool; old_minimum=m.minimum; old_returns=m.eviction_returns;
        refund=m.count(victim); m.count(child);
        for (int s=0; s<33; ++s) {
            require(old_pool[s] >= 0 && old_returns[s] >= 0 && old_minimum[s] >= 0 && old_minimum[s] <= old_pool[s], "invalid ledger baseline");
            require(refund[s] <= INT64_MAX-old_pool[s] && refund[s] <= INT64_MAX-old_returns[s], "eviction overflow");
            new_pool[s]=old_pool[s]+refund[s]; new_returns[s]=old_returns[s]+refund[s];
        }
        removed_state=m.state(victim); // allocation occurs before reversible mutations
    }
    ReplacementTransaction(const ReplacementTransaction &)=delete;
    ReplacementTransaction &operator=(const ReplacementTransaction &)=delete;
    ~ReplacementTransaction() { if (phase == Phase::Staged) rollback(); }
    Phase state() const { return phase; }
    const Counts &units() const { return refund; }
    const SpatialConservation::State &before() const { return removed_state; }
    void stage(const Fault &fault=Fault{}) {
        require(phase == Phase::Prepared, "replacement stage reuse");
        phase=Phase::Staged;
        auto checkpoint=[&](Checkpoint c) { if (fault) fault(c); };
        try {
            checkpoint(Checkpoint::Validated);
            AgentExtract(in_now?&now:&next,victim);
            checkpoint(Checkpoint::Unlinked);
            grid.grid[x][y]=child; grid.status[x][y]=G_NEXT;
            child->x=x; child->y=y; child->set=true;
            checkpoint(Checkpoint::Grid);
            material.pool=new_pool; material.eviction_returns=new_returns;
            checkpoint(Checkpoint::Refund);
            checkpoint(Checkpoint::Ready);
        } catch (...) { rollback(); throw; }
    }
    // Caller must publish exact EVICT material, scheduling death and lineage links.
    // Any exception here is fatal to the run, including before the first write.
    void publish(const std::function<void()> &emit) {
        require(phase == Phase::Staged && bool(emit), "replacement publication order");
        phase=Phase::Publishing;
        try { emit(); phase=Phase::Published; }
        catch (...) { phase=Phase::FailedAfterPublication; throw; }
    }
    // Preserve allocation through publication. The child remains staged until the
    // caller performs inherited source healing/CLEAVE/scheduling completion.
    void release_victim() {
        require(phase == Phase::Published, "victim free order/reuse");
        AgentFreeAndNull(&victim);
        phase=Phase::Freed;
    }
};
} // namespace sm_b003
#endif
