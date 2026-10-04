// Run all frozen directed suites against patch 0006 before focused cases.
#define main sm_c001_main
#include "stringmol_conservation_directed.cpp"
#undef main

static s_ag *completion_target=NULL;
static int completion_expected=0, completion_calls=0;
extern "C" int __real__Z11AgentUnbindP4s_ag(s_ag *);
extern "C" int __wrap__Z11AgentUnbindP4s_ag(s_ag *p) {
    if(p==completion_target) { assert(p->ect==completion_expected); ++completion_calls; }
    return __real__Z11AgentUnbindP4s_ag(p);
}
static void policy(Fixture &f,const char *name) {
    setenv("STRINGMOL_SCHEDULING","1",1); setenv("STRINGMOL_SCHEDULING_POLICY",name,1);
    unsetenv("STRINGMOL_SCHEDULING_LOG"); f.a->next=f.b;
    f.sim.scheduling.init(f.a,5000,false); f.a->next=NULL;
}
static void source_policy(Fixture &f, const char *disposition="RETIRE") {
    setenv("STRINGMOL_SOURCE_RETENTION","1",1);
    setenv("STRINGMOL_SOURCE_DISPOSITION",disposition,1);
    setenv("STRINGMOL_RETIREMENT_LOG","0",1);
    f.sim.retirement.init(f.sim.conservation);
}
static void retire_cases() {
    for(const char *schedule:{"IMMEDIATE","DELAY500"})
    for(const char *disposition:{"RETAIN","RETIRE"})
    for(int target:{0,1}) for(int offset:{0,1,3,4})
    for(bool full:{false,true}) for(bool hidden:{false,true}) {
        Fixture f("%ABC","BCDA"); policy(f,schedule); f.sim.timestep=2500;
        if(hidden) { f.a->S[10]='Z'; f.b->S[11]='Y'; }
        f.a->ft=target; f.a->f[target]=(target?f.a->S:f.b->S)+offset;
        if(full) for(int x=0;x<3;++x) for(int y=0;y<3;++y)
            if(!f.sim.grid->grid[x][y]) f.sim.grid->grid[x][y]=f.a;
        f.enable(0); source_policy(f,disposition);
        auto &c=f.sim.conservation; auto before=SpatialConservation::sum(c.count(f.a),c.count(f.b));
        bool eligible=offset>0 && offset<4 && !full;
        bool retired=eligible && !strcmp(disposition,"RETIRE");
        SetRNGSeed(7); int destroyed=f.sim.OpcodeCleaveSpatial(f.a);
        assert(destroyed==(retired?4:offset==0?(target?1:2):0));
        assert(f.sim.retirement.proposals==1 && f.sim.retirement.eligible==eligible && f.sim.retirement.committed==retired);
        assert(rng()==after_draws(7,offset<4 && !full?1:0));
        if(retired) {
            s_ag *child=f.sim.nexthead, *survivor=target?f.b:f.a;
            assert(child && child->idx==2 && child->next==survivor && !survivor->next);
            assert(survivor->status==B_UNBOUND && !survivor->exec && !survivor->pass && survivor->ect==0);
            assert(!f.sim.grid->grid[target?0:1][0]);
            assert(child->eligible_tick==(!strcmp(schedule,"DELAY500")?3001:2501));
            assert(before==SpatialConservation::sum(SpatialConservation::sum(c.count(child),c.count(survivor)),c.pool));
            assert(c.retirement_returns==c.pool && c.decay==SpatialConservation::Counts{} && c.waste==SpatialConservation::Counts{});
            assert(c.event_index==2);
            assert(c.retirement_returns[SpatialConservation::symbol(target?'Z':'Y')]==(hidden?1:0));
        }
    }
}
static void completion_and_lists() {
    for(int target:{0,1}) for(int list:{0,1,2}) {
        Fixture f("%ABC","BCDA"); policy(f,"IMMEDIATE"); f.enable(0); source_policy(f);
        f.a->ft=target; f.a->f[target]=(target?f.a->S:f.b->S)+1;
        s_ag *src=target?f.a:f.b;
        if(list==1) f.sim.nowhead=src;
        if(list==2) f.sim.nexthead=src;
        completion_target=target?f.b:f.a; completion_expected=target?5:12; completion_calls=0;
        SetRNGSeed(7); f.sim.ReactionExecuteOpcode_Spatial(f.a,f.b);
        assert(completion_calls==1); completion_target=NULL;
        assert(f.sim.retirement.committed==1 && f.sim.energy==29);
        assert(!f.sim.nowhead && f.sim.nexthead->idx==2 && f.sim.nexthead->next->idx==(target?1:0));
        assert(!f.sim.nexthead->next->next);
    }
    // Native cleanup removes the empty nonsource partner before retirement.
    for(int target:{0,1}) {
        Fixture f(target?"%ABC":"",target?"":"BCDA"); policy(f,"IMMEDIATE"); f.enable(0); source_policy(f);
        f.a->ft=target; f.a->f[target]=(target?f.a->S:f.b->S)+1;
        assert(f.sim.OpcodeCleaveSpatial(f.a)==4);
        assert(f.sim.nexthead->idx==2 && !f.sim.nexthead->next);
        assert(!f.sim.grid->grid[0][0] && !f.sim.grid->grid[1][0]);
    }
}
// The throw wrapper observes the real mutated state BEFORE stack unwinding and
// rollback. Thus a hook accidentally moved back to preflight cannot pass.
#include <typeinfo>
#include <cerrno>
#include <sys/stat.h>
static std::function<void(const char *)> checkpoint_check;
extern "C" void __real___cxa_throw(void *, void *, void (*)(void *)) __attribute__((noreturn));
extern "C" void __wrap___cxa_throw(void *value, void *type, void (*destroy)(void *)) {
    if(checkpoint_check && *static_cast<std::type_info *>(type)==typeid(SpatialRetirement::Fault))
        checkpoint_check(static_cast<SpatialRetirement::Fault *>(value)->phase);
    __real___cxa_throw(value,type,destroy);
}
static int frees=0;
extern "C" int __real__Z16AgentFreeAndNullPP4s_ag(s_ag **);
extern "C" int __wrap__Z16AgentFreeAndNullPP4s_ag(s_ag **p) {
    int result=__real__Z16AgentFreeAndNullPP4s_ag(p); ++frees; return result;
}
static std::string transaction_state(Fixture &f) {
    std::ostringstream out; out << f.state() << rng();
    for(int x=0;x<3;++x) for(int y=0;y<3;++y)
        out << f.sim.grid->grid[x][y] << ':' << f.sim.grid->status[x][y] << ';';
    out << f.sim.nowhead << ':' << f.sim.nexthead << ';';
    std::set<s_ag *> nodes{f.a,f.b};
    for(s_ag *head:{f.sim.nowhead,f.sim.nexthead}) for(s_ag *p=head;p;p=p->next) nodes.insert(p);
    for(s_ag *p:nodes) {
        out.write(reinterpret_cast<const char *>(p),sizeof(*p)); out.write(p->S,SIZE);
    }
    auto &c=f.sim.conservation;
    for(const auto &counts:{c.pool,c.retirement_returns,c.minimum,c.stable_molecular,c.decay,c.waste,c.returns,c.failed,c.discard})
        out.write(reinterpret_cast<const char *>(counts.data()),sizeof(counts));
    out << c.event_index << ':' << f.sim.scheduling.index;
    return out.str();
}
struct FaultSink {
    FILE *backing=NULL, *stream=NULL;
    std::string bytes, trigger, mode;
    std::function<void()> birth;
    int attempts=0; size_t published=0;
    static ssize_t write(void *cookie,const char *data,size_t n) {
        FaultSink &s=*static_cast<FaultSink *>(cookie);
        std::string row(data,n);
        bool fail=!s.trigger.empty() && row.find(s.trigger)!=std::string::npos;
        size_t count=n;
        if(fail) { ++s.attempts; count=s.mode=="short"?n/2:0; s.published=count; }
        assert(fwrite(data,1,count,s.backing)==count); assert(fflush(s.backing)==0);
        s.bytes.append(data,count);
        if(s.birth && row.find("BIRTH,")==0) s.birth();
        if(fail) { errno=ENOSPC; return count?static_cast<ssize_t>(count):-1; }
        return n;
    }
    void open(const char *name) {
        backing=fopen(name,"wx"); assert(backing);
        cookie_io_functions_t io={}; io.write=write;
        stream=fopencookie(this,"w",io); assert(stream);
    }
};
static int phase_index(const std::string &step) {
    int i=0;
    for(const char *s:{"validate","unlink","grid","refund","complete","unbind","append","publication"}) {
        if(step==s) return i;
        ++i;
    }
    return -1;
}
static void fault_child(const std::string &step,int target,int list) {
    Fixture *f=new Fixture("%ABC","BCDA"); policy(*f,"IMMEDIATE"); f->enable(0); source_policy(*f);
    f->a->S[10]='Z'; f->b->S[11]='Y'; // full-buffer refund/rollback, not strlen
    // Reinitialize material after adding hidden tails.
    f->sim.conservation=SpatialConservation(); f->enable(0);
    f->a->ft=target; f->a->f[target]=(target?f->a->S:f->b->S)+1;
    s_ag *src=target?f->a:f->b, *other=target?f->b:f->a;
    if(list) { s_ag **head=list==1?&f->sim.nowhead:&f->sim.nexthead; AgentAppend(head,src); AgentAppend(head,other); }
    auto *material=new FaultSink, *boundary=new FaultSink, *source=new FaultSink;
    material->open("material.csv"); boundary->open("boundary.csv"); source->open("source.csv");
    f->sim.conservation.logging=true; f->sim.conservation.journal=material->stream;
    f->sim.scheduling.journal=boundary->stream;
    f->sim.retirement.logging=true; f->sim.retirement.journal=source->stream;
    std::string before, before_material, before_boundary;
    SpatialConservation::Counts units{};
    boundary->birth=[&] {
        before=transaction_state(*f); before_material=material->bytes; before_boundary=boundary->bytes;
        units=f->sim.conservation.count(src);
    };
    int phase=phase_index(step), seen=0;
    bool writing=step.find("_write_")!=std::string::npos;
    if(writing) {
        FaultSink *sink=step.find("material_")==0?material:step.find("death_")==0?boundary:source;
        sink->trigger="RETIRE"; sink->mode=step.substr(step.rfind('_')+1);
        unsetenv("STRINGMOL_RETIREMENT_FAULT");
    } else setenv("STRINGMOL_RETIREMENT_FAULT",step.c_str(),1);
    checkpoint_check=[&](const char *actual) {
        assert(step==actual && phase>=0 && ++seen==1);
        assert(f->sim.retirement.committed==0 && frees==0);
        if(phase==0) assert(transaction_state(*f)==before);
        else {
            assert(!f->sim.nowhead && f->sim.nexthead->idx==2);
            assert(f->sim.grid->grid[src->x][src->y]==(phase>=2?NULL:src));
            assert(f->sim.conservation.pool==(phase>=3?units:SpatialConservation::Counts{}));
            assert(f->sim.conservation.retirement_returns==f->sim.conservation.pool);
            assert(other->status==(phase>=5?B_UNBOUND:target?B_PASSIVE:B_ACTIVE));
            assert(other->ect==(phase>=5?0:target?5:phase>=4?12:11));
            assert(f->sim.nexthead->next==(phase>=6?other:NULL));
        }
        assert(material->bytes==before_material && boundary->bytes==before_boundary && source->bytes.empty());
    };
    failure_check=[&] {
        assert(!before.empty());
        auto &c=f->sim.conservation;
        assert(f->sim.retirement.proposals==1 && f->sim.retirement.eligible==1);
        if(phase>=0) {
            assert(seen==1 && transaction_state(*f)==before);
            assert(f->sim.retirement.committed==0 && frees==0);
            assert(material->bytes==before_material && boundary->bytes==before_boundary && source->bytes.empty());
        } else {
            assert(seen==0 && f->sim.retirement.committed==1);
            assert(c.pool==units && c.retirement_returns==units && c.event_index==2);
            assert(!f->sim.nowhead && f->sim.nexthead->idx==2 && f->sim.nexthead->next==other && !other->next);
            assert(other->status==B_UNBOUND && !other->pass && !other->exec);
            assert(!f->sim.grid->grid[target?0:1][0]);
            assert(frees==(step=="free"?1:0));
            if(writing) {
                FaultSink *sink=step.find("material_")==0?material:step.find("death_")==0?boundary:source;
                assert(sink->attempts==1 && ferror(sink->stream));
                assert((sink->published>0)==(sink->mode=="short"));
            }
        }
        // No fatal branch may return through generic completion or emit RETAIN.
        assert(boundary->bytes.find("COMPLETE,")==std::string::npos && source->bytes.find("RETAIN")==std::string::npos);
        FILE *receipt=fopen("witness.json","wx"); assert(receipt);
        fprintf(receipt,"{\"phase\":\"%s\",\"target\":%d,\"list\":%d,\"checkpoint_seen\":%d,\"rolled_back\":%s,\"committed\":%lld,\"frees\":%d,\"write_attempts\":%d,\"partial_write_bytes\":%zu,\"logging\":true,\"no_fallback\":true}\n",
            step.c_str(),target,list,seen,phase>=0?"true":"false",(long long)f->sim.retirement.committed,frees,
            material->attempts+boundary->attempts+source->attempts,material->published+boundary->published+source->published);
        assert(fclose(receipt)==0);
    };
    frees=0; SetRNGSeed(7);
    assert(atexit(check_failure_state)==0);
    f->sim.OpcodeCleaveSpatial(f->a);
    _exit(0); // Parent rejects any return, including a RETAIN fallback.
}
static void retirement_faults() {
    assert(mkdir("faults",0700)==0);
    for(const char *step:{"validate","unlink","grid","refund","complete","unbind","append","publication",
                         "material","death","journal","free_before","free",
                         "material_write_error","material_write_short","death_write_error","death_write_short",
                         "source_write_error","source_write_short"})
    for(int target:{0,1}) for(int list:{0,1,2}) {
        std::string name=std::string("faults/")+step+"-"+std::to_string(target)+"-"+std::to_string(list);
        assert(mkdir(name.c_str(),0700)==0); fflush(NULL);
        pid_t pid=fork(); assert(pid>=0);
        if(!pid) {
            assert(chdir(name.c_str())==0);
            assert(freopen("stderr.txt","w",stderr));
            fault_child(step,target,list); _exit(0);
        }
        int status=0; assert(waitpid(pid,&status,0)==pid);
        assert(WIFEXITED(status) && WEXITSTATUS(status)==EXIT_FAILURE);
        FILE *receipt=fopen((name+"/exit.json").c_str(),"wx"); assert(receipt);
        fprintf(receipt,"{\"exit_status\":%d}\n",WEXITSTATUS(status)); assert(fclose(receipt)==0);
    }
    unsetenv("STRINGMOL_RETIREMENT_FAULT");
    for(const char *value:{"", "retire", "garbage"}) must_fail([value]{Fixture f; f.enable(0); source_policy(f,value);});
    puts("SM-B002 phase faults: 48 rolled back, 30 publication/free fatal, 36 real journal-write failures");
}
int main() {
    unsetenv("STRINGMOL_SOURCE_RETENTION");
    for(int branch=0;branch<6;++branch) for(int dest=0;dest<2;++dest) for(int granular=0;granular<2;++granular)
        for(bool alias:{false,true}) for(bool blocked:{false,true}) parity_case(branch,dest,granular,alias,blocked);
    bounds(); transactions_and_gaps(); atomic_insertion_and_minima(); cleavage(); decay(); initialization();
    substitution_endpoints(); dispatch_and_cleavage_faults(); nul_insertion_contraction();
    setenv("STRINGMOL_DECAY_DESTINATION","recycle",1); setenv("STRINGMOL_CONSERVATION_LOG","0",1);
    retire_cases(); completion_and_lists(); retirement_faults();
    puts("SM-B002 directed gates passed"); return 0;
}
