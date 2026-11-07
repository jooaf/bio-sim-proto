// Transport fixture, not a Stringmol population assay.
#include "experiments/stringmol/native/admission_journal.h"
#include <cerrno>
#include <iostream>
using namespace sm_b003;
static int flushes=0, fail_at=0, writes=0, fail_write_at=0;
static bool fail_close=false;
extern "C" size_t __real_fwrite(const void *, size_t, size_t, FILE *);
extern "C" int __real_fclose(FILE *);
extern "C" size_t __wrap_fwrite(const void *p, size_t size, size_t count, FILE *f) {
    if (++writes == fail_write_at) { errno=ENOSPC; return __real_fwrite(p,size,count/2,f); }
    return __real_fwrite(p,size,count,f);
}
extern "C" int __wrap_fclose(FILE *f) {
    const int result=__real_fclose(f);
    if (fail_close) { errno=EIO; return EOF; }
    return result;
}
extern "C" int __real_fflush(FILE *);
extern "C" int __wrap_fflush(FILE *f) {
    if (++flushes == fail_at) { errno=ENOSPC; return EOF; }
    return __real_fflush(f);
}
static Row marker(unsigned boundary) {
    Row r;
    r.number(Field::MaterialIndex,0).number(Field::BoundaryIndex,boundary)
     .set(Field::NowIds,"").set(Field::NextIds,"").number(Field::Population,0)
     .number(Field::ProposalTotal,0).number(Field::EvictionTotal,0)
     .number(Field::PartialTotal,0).number(Field::PartialCommitTotal,0);
    std::string zero="0";
    for (int i=1; i<33; ++i) zero+=";0";
    return r.set(Field::EvictionReturns,zero);
}
static std::string full_hex(std::string bytes) {
    bytes.resize(2001,'\0');
    std::string result;
    const char *hex="0123456789ABCDEF";
    for (unsigned char c: bytes) { result+=hex[c>>4]; result+=hex[c&15]; }
    return result;
}
static void proposal(Journal &log) {
    Row start=marker(1);
    start.set(Field::NowIds,"0;1;2").number(Field::Population,3);
    log.emit(Event::Start,0,0,start);
    Row b;
    b.number(Field::MaterialIndex,3).number(Field::BoundaryIndex,5).set(Field::NowIds,"2").number(Field::Population,3)
     .number(Field::Active,0).number(Field::Passive,1).number(Field::Source,0).number(Field::Offset,1).number(Field::Child,3)
     .set(Field::Channel,"OCCUPIED").set(Field::ChannelBits,uniform_bits(0.25)).set(Field::RankBits,uniform_bits(0.0))
     .number(Field::VacantCount,3).number(Field::OccupiedCount,1).number(Field::TargetX,1).number(Field::TargetY,0)
     .number(Field::Victim,2).number(Field::VictimEligibleTick,0).set(Field::VictimOwner,"NOW")
     .set(Field::SourceBuffer,full_hex("%ABC")).set(Field::ChildBuffer,full_hex("ABC"))
     .set(Field::VictimBuffer,full_hex(std::string("A\0BB",4))).number(Field::PartialOpportunity,1);
    log.emit(Event::Begin,10,1,b);
    std::string refund="1;2";
    for (int i=2; i<33; ++i) refund+=";0";
    Row r=marker(8);
    r.number(Field::MaterialIndex,5).set(Field::NextIds,"3;0;1").number(Field::Population,3)
     .number(Field::ProposalTotal,1).number(Field::EvictionTotal,1).number(Field::PartialTotal,1).number(Field::PartialCommitTotal,1)
     .set(Field::EvictionReturns,refund).set(Field::Disposition,"ADMIT_REPLACEMENT")
     .number(Field::EvictionMaterialIndex,4).number(Field::CleaveMaterialIndex,5).number(Field::DeathIndex,6).number(Field::BirthIndex,7)
     .number(Field::ChildEligibleTick,511).number(Field::SourceAlive,1);
    log.emit(Event::Resolve,10,1,r);
    Row end=marker(12);
    end.number(Field::MaterialIndex,10).set(Field::NowIds,"3;0;1").number(Field::Population,3)
       .number(Field::ProposalTotal,1).number(Field::EvictionTotal,1).number(Field::PartialTotal,1).number(Field::PartialCommitTotal,1)
       .set(Field::EvictionReturns,refund);
    log.emit(Event::End,50,0,end);
}
int main(int argc, char **argv) {
    try {
        ensure(argc == 3, "mode and output path required");
        const std::string mode=argv[1];
        if (mode == "bits") {
            std::cout << uniform_bits(0.0) << '\n' << uniform_bits(0.5) << '\n'
                      << uniform_bits(1.0-std::ldexp(1.0,-32)) << '\n';
            for (double bad: {-0.0, 0.1, 1.0, std::numeric_limits<double>::infinity()}) {
                bool rejected=false;
                try { uniform_bits(bad); } catch (const std::runtime_error &) { rejected=true; }
                ensure(rejected,"invalid uniform accepted");
            }
            return 0;
        }
        if (mode == "header-fault") fail_at=1;
        if (mode == "write-fault") fail_at=2;
        if (mode == "short-write") fail_write_at=2;
        if (mode == "close-fault") fail_close=true;
        Journal log(argv[2], Policy::Replace, Schedule::Delay500, 50, 3, 2);
        if (mode == "proposal") { proposal(log); return 0; }
        if (mode == "write-fault" || mode == "short-write") {
            bool first=false, second=false;
            try { log.emit(Event::Start,0,0,marker(1)); } catch (const std::runtime_error &) { first=true; }
            const int before=flushes, before_writes=writes;
            fail_at=fail_write_at=0;
            try { log.emit(Event::Start,0,0,marker(1)); } catch (const std::runtime_error &) { second=true; }
            ensure(first && second && log.failed() && flushes == before && writes == before_writes,"failed writer reused");
            return 91;
        }
        log.emit(Event::Start,0,0,marker(1));
        if (mode == "missing-end") return 0;
        if (mode == "duplicate") log.emit(Event::Start,0,0,marker(1));
        if (mode == "pending") {
            log.emit(Event::Begin,1,1,Row{}); // deliberately incomplete payload
            log.emit(Event::End,50,0,marker(3));
        }
        if (mode == "oversize") {
            Row r=marker(2); r.set(Field::NowIds,std::string(65536,'1'));
            log.emit(Event::End,50,0,r);
        }
        log.emit(Event::End,0,0,marker(2)); // zero-population early extinction
        if (mode == "after-end") log.emit(Event::End,0,0,marker(2));
        return 0;
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 92;
    }
}
