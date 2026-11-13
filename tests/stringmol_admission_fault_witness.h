// Link-time witnesses observe the actual opcode before unwinding and at exit.
// Nothing is injected into production source for these assertions.
#include <typeinfo>
#include <cerrno>
#include <fstream>
static Stringmol_Spatial *witness_sim=nullptr;
static s_ag *witness_child=nullptr;
static FILE *witness_begin_stream=nullptr;
static std::string witness_before, witness_rng, witness_phase;
static int witness_seen=0, witness_victim_frees=0;
static bool witness_enabled=false;
static std::string witness_io, witness_admission_event;
static FILE *witness_admission_stream=nullptr, *witness_terminal_stream=nullptr;
extern "C" FILE *__real_fopen(const char *,const char *);
extern "C" FILE *__wrap_fopen(const char *path,const char *mode) {
    const bool terminal=witness_enabled && !strcmp(path,"vm_end007.csv");
    if(terminal && witness_io=="terminal-open") { ++witness_seen; errno=ENOSPC; return nullptr; }
    FILE *result=__real_fopen(path,mode);
    if(terminal) witness_terminal_stream=result;
    return result;
}
extern "C" int __real_fclose(FILE *);
extern "C" int __wrap_fclose(FILE *stream) {
    const bool fail=witness_enabled && !witness_seen && witness_io=="terminal-close" && stream==witness_terminal_stream;
    const int result=__real_fclose(stream);
    if(fail) { ++witness_seen; errno=ENOSPC; return EOF; }
    return result;
}
static std::string native_snapshot() {
    auto &s=*witness_sim; auto &m=s.conservation;
    std::ostringstream out;
    out << s.agct << ',' << s.energy << ',' << s.biomass << ',' << m.event_index << ',' << s.scheduling.index << ';';
    out << SpatialScheduling::ids(s.nowhead) << '/' << SpatialScheduling::ids(s.nexthead) << ';';
    for(const auto &v:{m.pool,m.minimum,m.eviction_returns,m.retirement_returns,m.stable_molecular,m.decay,m.failed,m.discard,m.waste,m.returns,m.withdrawals})
        for(auto n:v) out << n << ',';
    std::set<s_ag *> agents;
    for(int x=0;x<s.grid->gridx;++x) for(int y=0;y<s.grid->gridy;++y) {
        auto p=s.grid->grid[x][y]; out << p << ':' << s.grid->status[x][y] << ';';
        if(p) agents.insert(p);
    }
    if(witness_child) agents.insert(witness_child);
    for(auto p:agents) {
        out << p << ',' << p->idx << ',' << p->status << ',' << p->len << ',' << p->label << ','
            << p->prev << ',' << p->next << ',' << p->pass << ',' << p->exec << ',' << p->spp << ','
            << p->biomass << ',' << p->ect << ',' << p->nbind << ',' << p->eligible_tick << ','
            << p->set << ',' << p->x << ',' << p->y << ';';
        out.write(p->S,2001);
        if(p->status==B_ACTIVE) {
            out << p->it << ',' << p->rt << ',' << p->wt << ',' << p->ft << ';';
            for(int t=0;t<2;++t) for(auto head:{p->i[t],p->r[t],p->w[t],p->f[t]}) out << static_cast<void *>(head) << ',';
        }
    }
    return out.str();
}
extern "C" s_ag *__real__Z9AgentMakeim(int,unsigned long);
extern "C" s_ag *__wrap__Z9AgentMakeim(int label,unsigned long id) {
    auto p=__real__Z9AgentMakeim(label,id);
    if(witness_enabled) witness_child=p;
    return p;
}
extern "C" int __real__Z16AgentFreeAndNullPP4s_ag(s_ag **);
extern "C" int __wrap__Z16AgentFreeAndNullPP4s_ag(s_ag **p) {
    if(witness_enabled && *p) {
        if((*p)->idx==2) ++witness_victim_frees;
        if(*p==witness_child) witness_child=nullptr;
    }
    return __real__Z16AgentFreeAndNullPP4s_ag(p);
}
extern "C" size_t __real_fwrite(const void *,size_t,size_t,FILE *);
extern "C" size_t __wrap_fwrite(const void *data,size_t size,size_t count,FILE *stream) {
    const auto result=__real_fwrite(data,size,count,stream);
    const char prefix[]="SM-B003-ADMISSION-2,BEGIN,";
    if(witness_enabled && size*count>=sizeof(prefix)-1 && !memcmp(data,prefix,sizeof(prefix)-1)) witness_begin_stream=stream;
    const char version[]="SM-B003-ADMISSION-2,";
    if(witness_enabled && size*count>=sizeof(version)-1 && !memcmp(data,version,sizeof(version)-1)) {
        witness_admission_stream=stream;
        const std::string text(static_cast<const char *>(data),size*count);
        const size_t first=text.find(',')+1;
        witness_admission_event=text.substr(first,text.find(',',first)-first);
    }
    return result;
}
extern "C" int __real_fflush(FILE *);
extern "C" int __wrap_fflush(FILE *stream) {
    const int result=__real_fflush(stream);
    if(witness_enabled && stream==witness_begin_stream && witness_before.empty()) {
        assert(result==0); witness_begin_stream=nullptr;
        witness_before=native_snapshot(); witness_rng=rng();
    }
    if(witness_enabled && !witness_io.empty() && !witness_seen && witness_sim) {
        auto &s=*witness_sim;
        const bool hit=(witness_io=="terminal" && stream==witness_terminal_stream) ||
            (witness_io=="material" && stream==s.conservation.journal && s.conservation.event_index==1) ||
            (witness_io=="death" && stream==s.scheduling.journal && s.scheduling.index==3) ||
            (witness_io=="birth" && stream==s.scheduling.journal && s.scheduling.index==4) ||
            (witness_io=="source" && stream==s.retirement.journal && s.conservation.event_index==2) ||
            (witness_io=="complete" && stream==s.scheduling.journal && s.scheduling.index==5) ||
            (stream==witness_admission_stream && ((witness_io=="begin" && witness_admission_event=="BEGIN") ||
             (witness_io=="resolve" && witness_admission_event=="RESOLVE") || (witness_io=="end" && witness_admission_event=="END")));
        if(hit) { assert(!witness_before.empty()); ++witness_seen; errno=ENOSPC; return EOF; }
    }
    return result;
}
static int prepublication_phase() {
    int index=0;
    for(const char *name:{"validate","unlink","grid","refund","ready"}) {
        if(witness_phase==name) return index;
        ++index;
    }
    return -1;
}
extern "C" void __real___cxa_throw(void *,void *,void (*)(void *)) __attribute__((noreturn));
extern "C" void __wrap___cxa_throw(void *value,void *type,void (*destroy)(void *)) {
    if(witness_enabled && *static_cast<std::type_info *>(type)==typeid(std::runtime_error) &&
       static_cast<std::runtime_error *>(value)->what()==witness_phase) {
        assert(!witness_before.empty() && ++witness_seen==1);
        const int phase=prepublication_phase();
        if(phase==0) assert(native_snapshot()==witness_before);
        if(phase>0) {
            assert(native_snapshot()!=witness_before);
            auto &s=*witness_sim;
            for(s_ag *head:{s.nowhead,s.nexthead}) for(auto p=head;p;p=p->next) assert(p->idx!=2);
            assert(s.grid->grid[0][1]->idx==(phase>=2?3:2));
            int64_t returns=0; for(auto n:s.conservation.eviction_returns) returns+=n;
            assert(returns==(phase>=3?3:0));
        }
    }
    __real___cxa_throw(value,type,destroy);
}
static void witness_exit() {
    if(!witness_enabled) return;
    assert(!witness_before.empty() && witness_seen==1);
    const bool rollback=prepublication_phase()>=0 || witness_io=="begin";
    assert(rng()==witness_rng); // proposal draws are never rewound or supplemented
    auto &s=*witness_sim;
    if(rollback) assert(native_snapshot()==witness_before && witness_victim_frees==0);
    else {
        assert(native_snapshot()!=witness_before);
        assert(s.grid->grid[0][1] && s.grid->grid[0][1]->idx==3);
        int64_t returns=0; for(auto n:s.conservation.eviction_returns) returns+=n;
        assert(returns==3 && s.agct==4);
        const bool released=witness_phase=="free" || witness_phase=="birth" || witness_phase=="cleave" || witness_phase=="complete" || witness_phase=="journal" ||
            witness_io=="birth" || witness_io=="source" || witness_io=="complete" || witness_io=="resolve" || witness_io=="end" ||
            witness_io=="terminal" || witness_io=="terminal-open" || witness_io=="terminal-close";
        assert(witness_victim_frees==int(released));
    }
    FILE *f=fopen("fault-witness.json","wx"); assert(f);
    fprintf(f,"{\"phase\":\"%s\",\"rollback\":%s,\"checkpoint_seen\":%d,\"victim_frees\":%d,\"rng_preserved\":true,\"next_identity\":%lu}\n",
            witness_phase.c_str(),rollback?"true":"false",witness_seen,witness_victim_frees,s.agct);
    assert(!fclose(f));
}
