// Source-level SM-C001 gates. Linked to the freshly patched release objects.
#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <sstream>
#include <functional>
#include <sys/wait.h>
#include <unistd.h>
#include "default_config.h"
#include "alignment.h"
#include "rules.h"
#include "agent.h"
#include "SMspp.h"
#include "opcodes.h"
#include "stringPM.h"
#include "sm_spatial.h"
#include "randutil.h"
#include "mt19937-2.h"
#include "setupSM.h"

static const unsigned SIZE = 33;
static std::string file_bytes(FILE *f) {
    fflush(f); rewind(f); std::string out; int c;
    while ((c = fgetc(f)) != EOF) out.push_back(c);
    fclose(f); return out;
}
static std::string rng() { FILE *f = tmpfile(); assert(f); MersenneTwisterPrintStatusToFile(f); return file_bytes(f); }
static std::string after_draws(unsigned seed, int draws) {
    SetRNGSeed(seed); while (draws--) RandomBetween0And1(); return rng();
}
struct Fixture {
    SMspp sp;
    Stringmol_Spatial sim;
    s_ag *a, *b;
    Fixture(const char *active = "=ABC", const char *passive = "BC") : sim(&sp) {
        sim.maxl0 = SIZE; sim.maxl = SIZE-1;
        free(sim.blosum); sim.blosum = default_table();
        sim.grid = sim.init_smprun(3, 3);
        sim.placement_radius = 0;
        a = AgentMakeWithSequence(const_cast<char *>(active), 'Q', 0, SIZE);
        b = AgentMakeWithSequence(const_cast<char *>(passive), 'Q', 1, SIZE);
        sp.SpeciesListUpdate(a, 'I', 1, NULL, NULL, 0, 0, SIZE);
        sp.SpeciesListUpdate(b, 'I', 1, NULL, NULL, 0, 0, SIZE);
        a->status = B_ACTIVE; b->status = B_PASSIVE; a->pass = b; b->exec = a;
        for (int t=0; t<2; ++t) a->i[t] = a->r[t] = a->w[t] = a->f[t] = t ? a->S : b->S;
        b->it=b->rt=b->wt=b->ft=0;
        for(int t=0;t<2;++t) b->i[t]=b->r[t]=b->w[t]=b->f[t]=NULL;
        a->it=1; a->rt=1; a->wt=0; a->ft=0;
        a->r[1]=a->S+1; a->w[0]=b->S+2;
        a->biomass=7; b->biomass=3; a->ect=11; b->ect=5;
        sim.biomass=19; sim.energy=30; sim.agct=2;
        AgentPlaceOnGrid(a,sim.grid,0,0); AgentPlaceOnGrid(b,sim.grid,1,0);
    }
    void enable(int amount=1000, const char *mode="uniform") {
        setenv("STRINGMOL_CONSERVATION","1",1); setenv("STRINGMOL_POOL_MODE",mode,1);
        std::string text=std::to_string(amount); setenv("STRINGMOL_POOL_AMOUNT",text.c_str(),1);
        a->next=b; b->prev=a; sim.conservation.init(a,SIZE,sim.blosum->key); a->next=NULL; b->prev=NULL;
    }
    std::string state(bool bytes=true) {
        std::ostringstream out;
        out << sim.biomass << ',' << sim.energy << ',' << sim.agct << ';';
        for (s_ag *p : {a,b}) {
            out << p->idx << ',' << p->len << ',' << p->biomass << ',' << p->ect << ',' << p->nbind << ',' << p->status << ',' << p->spp->spp
                << ',' << p->it << ',' << p->rt << ',' << p->wt << ',' << p->ft << ',' << (p->pass ? p->pass->idx : -1) << ',' << (p->exec ? p->exec->idx : -1) << ';';
            if (p==a) for (int t=0;t<2;++t) for(char *q : {p->i[t],p->r[t],p->w[t],p->f[t]})
                out << (q ? q-(t?a->S:b->S) : -999) << ',';
            if(bytes) out.write(p->S,SIZE);
        }
        for(s_ag *p=sim.nexthead;p;p=p->next) out << 'L' << p->idx;
        FILE *f=tmpfile(); sp.SpeciesListPrint(f); out << file_bytes(f);
        return out.str();
    }
    // Fixtures are short-lived in a single process. Detach to avoid upstream's
    // bucket destructor traversing pointers intentionally freed by decay/cleave.
    ~Fixture() { sim.nowhead=sim.nexthead=NULL; }
};

// exit(), unlike an invalid read or abort, runs this child-only verification.
static std::function<void()> failure_check;
static void check_failure_state() { if (failure_check) failure_check(); }
static void must_fail(const std::function<void()> &fn) {
    fflush(NULL); pid_t pid=fork(); assert(pid>=0);
    if(!pid) { failure_check = nullptr; assert(atexit(check_failure_state)==0); fn(); _exit(0); }
    int status=0; assert(waitpid(pid,&status,0)==pid);
    assert(WIFEXITED(status) && WEXITSTATUS(status)!=0);
}
static void parity_case(int branch, int destination, int granular, bool alias, bool blocked) {
    Fixture native, conserved;
    for (Fixture *f : {&native,&conserved}) {
        f->sim.domut=branch!=0;
        f->sim.indelrate=(branch==2 || branch==3) ? 1 : 0;
        f->sim.subrate=branch==1 ? 1 : 0;
        f->sim.granular_1=granular;
        f->a->wt=destination;
        f->a->w[destination]=(destination ? f->a->S : f->b->S)+ (alias?1:2);
        if (alias) { f->a->rt=destination; f->a->r[destination]=f->a->w[destination]; }
        if (branch==4) { f->a->rt=1; f->a->r[1]=f->a->S+4; }
        if (branch==5) { f->a->rt=0; f->a->r[0]=f->b->S; f->a->w[destination]=(destination?f->a->S:f->b->S)+1; }
    }
    // Fixed seeds: seed 1 selects deletion; seed 2 insertion (second float).
    unsigned seed=branch==3 ? 1 : 2;
    conserved.enable(blocked?0:1000);
    std::string beforeA(conserved.a->S,SIZE), beforeB(conserved.b->S,SIZE);
    SetRNGSeed(seed); native.sim.ReactionExecuteOpcode_Spatial(native.a,native.b); std::string native_rng=rng();
    SetRNGSeed(seed); conserved.sim.ReactionExecuteOpcode_Spatial(conserved.a,conserved.b);
    assert(rng()==native_rng);
    auto &c=conserved.sim.conservation;
    assert(c.attempts==1);
    int64_t partition=0; for(auto n:c.categories) partition+=n; assert(partition==1);
    assert(conserved.a->len==static_cast<int>(strlen(conserved.a->S)) && conserved.b->len==static_cast<int>(strlen(conserved.b->S)));
    if(c.categories[SpatialConservation::BLOCKED]) {
        assert(std::string(conserved.a->S,SIZE)==beforeA && std::string(conserved.b->S,SIZE)==beforeB);
        // Lengths alone depend on committed bytes; compare all remaining state.
        native.a->len=conserved.a->len; native.b->len=conserved.b->len;
        if(conserved.state(false)!=native.state(false)) { fprintf(stderr,"CASE %d %d %d %d %d\nN %s\nC %s\n",branch,destination,granular,alias,blocked,native.state(false).c_str(),conserved.state(false).c_str()); abort(); }
        for(auto n:c.pool) assert(n==0);
    } else assert(conserved.state()==native.state());
    assert(conserved.a->biomass==8 && conserved.b->biomass==3 && conserved.sim.biomass==20);
    assert(conserved.a->ect==12 && conserved.b->ect==5 && conserved.sim.energy==29);
    assert(conserved.a->i[1]==conserved.a->S+(branch==3?2:1));
    std::string frozen_rng=rng();
    if(branch==4) assert(c.categories[SpatialConservation::READ_NULL]==1 && frozen_rng==after_draws(seed,0));
    if(branch==3) assert(c.categories[SpatialConservation::DELETION]==1 && frozen_rng==after_draws(seed,2));
    if(branch==0) assert(frozen_rng==after_draws(seed,1));
    if(branch==2) assert(frozen_rng==after_draws(seed,3));
}
static void bounds() {
    for(int target=0;target<2;++target) for(int head=0;head<2;++head) for(int off : {-1,32,33,100}) {
        Fixture f; f.enable();
        if(head) { f.a->wt=target; f.a->w[target]=reinterpret_cast<char *>(reinterpret_cast<uintptr_t>(target?f.a->S:f.b->S)+off); }
        else { f.a->rt=target; f.a->r[target]=reinterpret_cast<char *>(reinterpret_cast<uintptr_t>(target?f.a->S:f.b->S)+off); }
        std::string a(f.a->S,SIZE),b(f.b->S,SIZE); auto pool=f.sim.conservation.pool;
        SetRNGSeed(2); std::string before=rng();
        f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        assert(rng()==before && f.sim.conservation.categories[0]==1);
        assert(a==std::string(f.a->S,SIZE) && b==std::string(f.b->S,SIZE) && pool==f.sim.conservation.pool);
        assert(f.a->status==B_UNBOUND && f.b->status==B_UNBOUND && f.a->ect==1 && f.b->ect==0);
        assert(f.a->biomass==0 && f.b->biomass==3 && f.sim.biomass==19 && f.sim.energy==29);
        for(int t=0;t<2;++t) assert(!f.a->i[t] && !f.a->r[t] && !f.a->w[t] && !f.a->f[t]);
    }
    for(int granular : {0,1}) for(int target : {0,1}) {
        Fixture f; f.enable(); f.sim.indelrate=1; f.sim.granular_1=granular; f.a->wt=target;
        char *base=target?f.a->S:f.b->S; f.a->w[target]=base+31;
        SetRNGSeed(2); f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        std::string actual=rng(); assert(actual==after_draws(2,2));
        assert(f.sim.conservation.categories[0]==1 && !base[31] && !base[32]);
        assert(f.a->w[target]==base+(granular?32:33) && f.a->r[1]==f.a->S+(granular?1:2));
        assert(f.a->i[1]==f.a->S+1 && f.a->biomass==8 && f.a->ect==12 && f.sim.energy==29);
    }
    must_fail([] { Fixture f; f.enable(); f.a->S[SIZE-1]='A'; f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b); });
}
static void transactions_and_gaps() {
    Fixture f; f.enable(0); auto &c=f.sim.conservation;
    char a='A',b='B';
    c.transaction({{&a,'B'},{&b,'A'}}); // zero composition is changing, funded by returns
    assert(a=='B' && b=='A' && c.categories[c.ACCEPTED]==1 && c.returns[0]==1 && c.withdrawals[0]==1);
    c.transaction({{&a,'A'},{&a,'B'}}); assert(c.categories[c.NOOP]==1);
    c.transaction({{&a,'C'},{&a,'A'},{&b,'B'}}); assert(a=='A' && b=='B' && c.categories[c.ACCEPTED]==2);
    char x=0,y=0; c.transaction({{&x,'A'},{&y,'A'}});
    assert(!x && !y && c.categories[c.BLOCKED]==1 && c.missing[0]==2);
    // Blocked append and hidden-gap append must retain actual visible lengths.
    f.a->w[0]=f.b->S+2; f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
    assert(f.b->len==2 && f.b->S[2]==0);
    f.sim.nexthead=NULL; f.a->next=f.b->next=NULL; f.a->prev=f.b->prev=NULL;
    f.a->i[1]=f.a->S; f.a->r[1]=f.a->S+1; f.a->w[0]=f.b->S+5;
    f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b); assert(f.b->len==2 && f.b->S[5]==0);
    c.pool[0]=3; c.transaction({{f.b->S+5,'A'}}); assert(strlen(f.b->S)==2 && c.count(f.b)[0]==1);
    c.transaction({{f.b->S+2,'A'},{f.b->S+3,'A'}}); assert(strlen(f.b->S)==4);
    c.pool[0]=1; c.transaction({{f.b->S+4,'A'}}); assert(strlen(f.b->S)==6 && c.count(f.b)[0]==4);
    c.transaction({{f.b->S+2,0}}); assert(strlen(f.b->S)==2 && c.count(f.b)[0]==3);
}
static void atomic_insertion_and_minima() {
    Fixture native, f;
    native.sim.indelrate=f.sim.indelrate=1;
    f.enable(0);
    SetRNGSeed(2); native.sim.ReactionExecuteOpcode_Spatial(native.a,native.b);
    assert(native.b->S[2]=='A' && native.b->S[3]=='D');
    auto &c=f.sim.conservation;
    c.pool[0]=1; c.minimum[0]=1;
    SetRNGSeed(2); f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
    assert(f.b->S[2]==0 && f.b->S[3]==0 && f.b->len==2);
    assert(c.categories[c.BLOCKED]==1 && c.missing[SpatialConservation::symbol('D')]==1 && c.pool[0]==1);
    assert(c.withdrawals[0]==0 && c.returns[0]==0 && c.growth==0);
    assert(f.a->w[0]==f.b->S+4 && f.a->r[1]==f.a->S+2 && f.a->i[1]==f.a->S+1);
    // A pool low between reports survives subsequent releases.
    char x=0;
    c.transaction({{&x,'A'}}); assert(c.minimum[0]==0 && c.pool[0]==0);
    SpatialConservation::Counts released{}; released[0]=8;
    c.release(released,c.decay); assert(c.pool[0]==8 && c.minimum[0]==0);
    // Hidden-tail writes and subsequent gap filling through the actual opcode.
    Fixture gap; gap.enable(0); gap.sim.domut=false;
    auto step=[&gap](int offset) {
        gap.sim.nexthead=NULL; gap.a->next=gap.b->next=NULL; gap.a->prev=gap.b->prev=NULL;
        gap.a->i[1]=gap.a->S; gap.a->r[1]=gap.a->S+1; gap.a->w[0]=gap.b->S+offset;
        gap.sim.ReactionExecuteOpcode_Spatial(gap.a,gap.b);
        assert(gap.b->len==static_cast<int>(strlen(gap.b->S)));
    };
    step(2); assert(gap.b->len==2 && gap.sim.conservation.categories[c.BLOCKED]==1);
    gap.sim.conservation.pool[0]=4;
    step(5); assert(gap.b->len==2 && gap.b->S[5]=='A');
    step(2); assert(gap.b->len==3);
    step(3); assert(gap.b->len==4);
    step(4); assert(gap.b->len==6 && gap.sim.conservation.pool[0]==0);
    assert(gap.sim.conservation.growth==4);
}
static void cleavage() {
    for(int target : {0,1}) for(int offset : {0,1,3,4}) for(bool full_grid : {false,true}) for(bool hidden : {false,true}) {
        Fixture f("%ABC","BCDA");
        if(hidden) { f.a->S[10]='Z'; f.b->S[11]='Y'; }
        f.a->ft=target; f.a->f[target]=reinterpret_cast<char *>(reinterpret_cast<uintptr_t>(target?f.a->S:f.b->S)+offset);
        f.a->r[0]=f.b->S+20; f.a->w[1]=f.a->S+20; // rewind after successful cut
        if(full_grid) for(int x=0;x<3;++x) for(int y=0;y<3;++y) if(!f.sim.grid->grid[x][y]) f.sim.grid->grid[x][y]=f.a;
        f.enable(0); auto &c=f.sim.conservation; auto before=SpatialConservation::sum(c.count(f.a),c.count(f.b));
        SetRNGSeed(7); int destroyed=f.sim.OpcodeCleaveSpatial(f.a);
        bool valid=offset>=0 && offset<4;
        assert(destroyed==(valid && offset==0 ? (target?1:2):0));
        SpatialConservation::Counts after{};
        if(!(destroyed&1)) after=SpatialConservation::sum(after,c.count(f.a));
        if(!(destroyed&2)) after=SpatialConservation::sum(after,c.count(f.b));
        const s_ag *child=NULL;
        for(s_ag *p=f.sim.nexthead;p;p=p->next) if(p->idx==2) child=p;
        after=SpatialConservation::sum(after,c.count(child));
        assert(bool(child)==(valid && !full_grid));
        for(int s=0;s<33;++s) {
            assert(before[s]==after[s]+c.pool[s]);
            assert(c.pool[s]==c.failed[s]+c.discard[s]);
            if(!valid) assert(c.pool[s]==0);
            if(valid && !full_grid && offset>0) assert(c.pool[s]==0);
        }
        if(valid && !full_grid && offset==0 && hidden) assert(c.discard[SpatialConservation::symbol(target?'Z':'Y')]==1);
        if(valid && offset>0) { assert(f.a->r[0]<=f.b->S+strlen(f.b->S)); assert(f.a->w[1]<=f.a->S+strlen(f.a->S)); }
        if(!valid) assert(f.a->i[1]==f.a->S+1);
        std::string actual=rng(); assert(actual==after_draws(7,valid && !full_grid?1:0));
    }
    // Native's first zero-parent branch wins if both are empty; dac=3 is
    // unreachable in AgentCheckZeroLengthString. Freeze both reachable paths.
    for(int target:{0,1}) {
        Fixture f(target?"%A":"",target?"":"BA"); f.enable(0);
        f.a->ft=target; f.a->f[target]=target?f.a->S:f.b->S;
        assert(f.sim.OpcodeCleaveSpatial(f.a)==1);
    }
}
static void decay() {
    for(int status : {B_UNBOUND,B_ACTIVE,B_PASSIVE}) {
        Fixture f; f.a->S[20]='Z'; f.b->S[21]='A'; f.enable(0);
        auto &c=f.sim.conservation; auto expected=c.count(f.a);
        if(status==B_UNBOUND) { f.a->status=B_UNBOUND; f.a->pass=NULL; }
        else expected=SpatialConservation::sum(expected,c.count(f.b));
        f.sim.decayrate=1; s_ag *p=status==B_PASSIVE?f.b:f.a;
        SetRNGSeed(3); assert(f.sim.AgentAttemptDecaySpatial(&p)==1 && p==NULL);
        std::string actual=rng(); assert(actual==after_draws(3,1));
        assert(c.decay==expected && c.pool==expected);
    }
}
// Load exact MT words rather than replacing the linked RNG or changing native
// chemistry. Un-tempering yields real endpoint outputs from the pinned engine.
static uint32_t untemper(uint32_t word) {
    uint32_t x=word;
    for(int i=0;i<8;++i) x=word^(x>>18);
    word=x;
    for(int i=0;i<8;++i) x=word^((x<<15)&0xefc60000U);
    word=x;
    for(int i=0;i<8;++i) x=word^((x<<7)&0x9d2c5680U);
    word=x;
    for(int i=0;i<8;++i) x=word^(x>>11);
    return x;
}
static std::string controlled_rng(std::initializer_list<uint32_t> words, int consumed=0) {
    char filename[]="directed-mt-XXXXXX";
    int fd=mkstemp(filename); assert(fd>=0);
    FILE *f=fdopen(fd,"w"); assert(f);
    fprintf(f,"MTI %d\n",consumed);
    std::vector<uint32_t> values(words);
    for(unsigned i=0;i<624;++i) fprintf(f,"%lu\n",static_cast<unsigned long>(i<values.size()?untemper(values[i]):0));
    assert(fclose(f)==0);
    assert(MersenneTwisterLoadState(filename)==load_mt_success);
    assert(unlink(filename)==0);
    return rng();
}
static void substitution_endpoints() {
    controlled_rng({0,0xffffffffU});
    assert(RandomBetween0And1()==0.0);
    double upper=RandomBetween0And1(); assert(upper<1.0 && static_cast<float>(upper)==1.0f);
    // Ordinary positive ranks, including the float upper endpoint, exactly
    // match upstream symbol choice and consumption of the second draw.
    for(uint32_t word : {1U,0x40000000U,0xffffffffU}) {
        Fixture native, f; native.sim.subrate=f.sim.subrate=1; f.enable();
        controlled_rng({0x40000000U,word}); native.sim.ReactionExecuteOpcode_Spatial(native.a,native.b);
        std::string expected=rng();
        controlled_rng({0x40000000U,word}); f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        assert(f.state()==native.state() && rng()==expected && MersenneTwisterGetState()==2);
    }
    must_fail([] {
        Fixture f; f.enable(); f.sim.subrate=1;
        std::string before=f.state(); auto pool=f.sim.conservation.pool;
        std::string expected=controlled_rng({0x40000000U,0},2);
        controlled_rng({0x40000000U,0});
        failure_check=[&] {
            assert(f.state()==before && f.sim.conservation.pool==pool);
            assert(rng()==expected && f.sim.conservation.attempts==1);
        };
        f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
    });
}
static void dispatch_and_cleavage_faults() {
    for(int target : {0,1}) {
        // Native deletion completes with i at one-past; that pointer is never
        // safe to dispatch. Completion effects are preserved before failure.
        Fixture native; native.sim.indelrate=1;
        native.a->it=target; char *base=target?native.a->S:native.b->S;
        base[SIZE-2]='='; native.a->i[target]=base+SIZE-2;
        SetRNGSeed(1); native.sim.ReactionExecuteOpcode_Spatial(native.a,native.b);
        assert(native.a->i[target]==base+SIZE);
        std::string expected=native.state(), expected_rng=rng();
        must_fail([&] {
            Fixture f; f.sim.indelrate=1;
            f.a->it=target; char *buffer=target?f.a->S:f.b->S;
            buffer[SIZE-2]='='; f.a->i[target]=buffer+SIZE-2; f.enable();
            auto pool=f.sim.conservation.pool;
            failure_check=[&] {
                assert(f.state()==expected && rng()==expected_rng);
                assert(f.a->i[target]==buffer+SIZE && f.sim.conservation.pool==pool);
                assert(f.sim.conservation.attempts==1 && f.sim.conservation.categories[SpatialConservation::DELETION]==1);
                assert(f.a->ect==12 && f.sim.energy==29 && f.a->biomass==8 && f.sim.biomass==20);
            };
            SetRNGSeed(1); f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        });
        must_fail([&] {
            Fixture f; f.enable(); f.a->it=target;
            f.a->i[target]=(target?f.a->S:f.b->S)+SIZE;
            std::string before=f.state(), before_rng=rng();
            failure_check=[&] { assert(f.state()==before && rng()==before_rng && f.sim.conservation.attempts==0); };
            f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        });
        for(int offset : {-1,static_cast<int>(SIZE),static_cast<int>(SIZE)+1000000}) must_fail([&] {
            Fixture f("%ABC","BCDA"); f.enable(0); f.a->ft=target;
            f.a->f[target]=reinterpret_cast<char *>(reinterpret_cast<uintptr_t>(target?f.a->S:f.b->S)+offset);
            std::string before_a(f.a->S,SIZE), before_b(f.b->S,SIZE), before_rng=rng();
            auto pool=f.sim.conservation.pool;
            failure_check=[&] {
                assert(before_a==std::string(f.a->S,SIZE) && before_b==std::string(f.b->S,SIZE));
                assert(f.sim.conservation.pool==pool && rng()==before_rng && f.sim.agct==2 && !f.sim.nexthead);
            };
            f.sim.OpcodeCleaveSpatial(f.a);
        });
    }
}
static void nul_insertion_contraction() {
    for(int target:{0,1}) for(int granular:{0,1}) {
        Fixture native("=ABC","ABC"), f("=ABC","ABC");
        for(Fixture *p : {&native,&f}) {
            p->sim.indelrate=1; p->sim.granular_1=granular;
            p->a->wt=target; p->a->w[target]=(target?p->a->S+1:p->b->S);
        }
        f.enable(0); auto &c=f.sim.conservation;
        auto before=SpatialConservation::sum(c.count(f.a),c.count(f.b));
        // The third draw rounds to 1.0f; native key[N] is NUL, not key[N-1].
        controlled_rng({0x40000000U,0x40000000U,0xffffffffU});
        native.sim.ReactionExecuteOpcode_Spatial(native.a,native.b); std::string expected=rng();
        controlled_rng({0x40000000U,0x40000000U,0xffffffffU});
        f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        assert(f.state()==native.state() && rng()==expected && MersenneTwisterGetState()==3);
        assert(c.attempts==1 && c.categories[c.ACCEPTED]==1 && c.growth==0);
        assert(c.returns[SpatialConservation::symbol('B')]==1 && c.pool==c.returns);
        for(auto n:c.withdrawals) assert(n==0);
        auto after=SpatialConservation::sum(c.count(f.a),c.count(f.b));
        for(int s=0;s<33;++s) assert(before[s]==after[s]+c.pool[s]);
        s_ag *dest=target?f.a:f.b;
        assert(dest->len==(target?2:1) && dest->S[target?3:2]=='C');
    }
}
static void initialization() {
    for(const char *mode : {"histogram","uniform"}) { Fixture f; f.a->S[20]='Z'; f.enable(16,mode);
        auto &c=f.sim.conservation; auto counts=SpatialConservation::sum(c.count(f.a),c.count(f.b));
        for(int s=0;s<33;++s) assert(c.pool[s]==(!strcmp(mode,"histogram")?counts[s]*16:16));
        must_fail([&f]{f.sim.conservation.init(f.a,SIZE,f.sim.blosum->key);});
    }
    for(const char *bad : {"", "00", "01", "-1", "+1", " 1", "1 ", "1.0", "9223372036854775808"})
        must_fail([bad]{SpatialConservation::amount(bad);});
    must_fail([]{SpatialConservation::amount(NULL);});
    must_fail([]{Fixture f; f.enable(); setenv("STRINGMOL_POOL_MODE","bad",1); SpatialConservation c; c.init(f.a,SIZE,f.sim.blosum->key);});
    must_fail([]{Fixture f; f.enable(); unsetenv("STRINGMOL_POOL_MODE"); SpatialConservation c; c.init(f.a,SIZE,f.sim.blosum->key);});
    must_fail([]{Fixture f; f.enable(); unsetenv("STRINGMOL_POOL_AMOUNT"); SpatialConservation c; c.init(f.a,SIZE,f.sim.blosum->key);});
    must_fail([]{Fixture f; f.enable(); setenv("STRINGMOL_POOL_AMOUNT","9223372036854775807",1); SpatialConservation c; c.init(f.a,SIZE,f.sim.blosum->key);});
    must_fail([]{Fixture f; f.enable(); setenv("STRINGMOL_POOL_MODE","histogram",1); setenv("STRINGMOL_POOL_AMOUNT","9223372036854775807",1); f.a->S[9]='A'; SpatialConservation c; c.init(f.a,SIZE,f.sim.blosum->key);});
    must_fail([]{Fixture f; f.a->S[20]='!'; f.enable();});
    must_fail([]{Fixture f; f.enable(); auto before=f.sim.conservation.count(f.a); f.a->S[20]='Z'; f.sim.conservation.cleave(before,f.a,NULL,NULL);});
    for(const char *flag : {"0","no",""}) { setenv("STRINGMOL_CONSERVATION",flag,1); setenv("STRINGMOL_POOL_AMOUNT","bad",1); SpatialConservation c; c.init(NULL,0,NULL); assert(!c.enabled); }
    unsetenv("STRINGMOL_CONSERVATION"); SpatialConservation c; c.init(NULL,0,NULL); assert(!c.enabled);
}
int main() {
    for(int branch=0;branch<6;++branch) for(int dest=0;dest<2;++dest) for(int granular=0;granular<2;++granular)
        for(bool alias:{false,true}) for(bool blocked:{false,true}) parity_case(branch,dest,granular,alias,blocked);
    bounds(); transactions_and_gaps(); atomic_insertion_and_minima(); cleavage(); decay(); initialization();
    substitution_endpoints(); dispatch_and_cleavage_faults(); nul_insertion_contraction();
    puts("SM-C001 directed gates passed");
}
