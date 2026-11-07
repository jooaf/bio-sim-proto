// SM-B003 journal transport only; not an admission/eviction implementation.
#ifndef SM_B003_ADMISSION_JOURNAL_H
#define SM_B003_ADMISSION_JOURNAL_H
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

namespace sm_b003 {
#define SM_ADMISSION_FIELDS(X) \
 X(Version,version) X(Event,event) X(Tick,tick) X(Index,index) X(Transaction,transaction) \
 X(Policy,policy) X(Schedule,schedule) X(Horizon,horizon) X(Width,width) X(Height,height) \
 X(BufferSize,buffer_size) X(SourceDisposition,source_disposition) \
 X(MaterialIndex,material_index) X(BoundaryIndex,boundary_index) X(NowIds,now_ids) X(NextIds,next_ids) X(Population,population) \
 X(ProposalTotal,proposal_total) X(EvictionTotal,eviction_total) X(PartialTotal,partial_total) X(PartialCommitTotal,partial_commit_total) X(EvictionReturns,eviction_returns) \
 X(Active,active) X(Passive,passive) X(Source,source) X(Offset,offset) X(Child,child) X(Channel,channel) X(ChannelBits,channel_bits) X(RankBits,rank_bits) \
 X(VacantCount,vacant_count) X(OccupiedCount,occupied_count) X(TargetX,target_x) X(TargetY,target_y) X(Victim,victim) X(VictimEligibleTick,victim_eligible_tick) X(VictimOwner,victim_owner) \
 X(SourceBuffer,source_buffer) X(ChildBuffer,child_buffer) X(VictimBuffer,victim_buffer) X(PartialOpportunity,partial_opportunity) \
 X(Disposition,disposition) X(EvictionMaterialIndex,eviction_material_index) X(CleaveMaterialIndex,cleave_material_index) X(DeathIndex,death_index) X(BirthIndex,birth_index) X(ChildEligibleTick,child_eligible_tick) X(SourceAlive,source_alive)
#define SM_FIELD_ENUM(name, wire) name,
enum class Field { SM_ADMISSION_FIELDS(SM_FIELD_ENUM) Count };
#undef SM_FIELD_ENUM
#define SM_FIELD_NAME(name, wire) #wire,
static const char *const columns[] = { SM_ADMISSION_FIELDS(SM_FIELD_NAME) };
#undef SM_FIELD_NAME
#undef SM_ADMISSION_FIELDS
constexpr size_t field_count = static_cast<size_t>(Field::Count);
enum class Event { Start, Begin, Resolve, End };
enum class Policy { Native, Reject, Replace };
enum class Schedule { Immediate, Delay500 };

inline void ensure(bool condition, const char *why) {
    if (!condition) throw std::runtime_error(why);
}
inline std::string uniform_bits(double value) {
    static_assert(sizeof(double) == sizeof(uint64_t) && std::numeric_limits<double>::is_iec559, "IEEE binary64 required");
    const double word = std::ldexp(value, 32);
    ensure(std::isfinite(value) && value >= 0 && value < 1 && !std::signbit(value) && word == std::floor(word), "native MT uniform lattice");
    uint64_t bits;
    std::memcpy(&bits, &value, sizeof bits);
    const char *hex = "0123456789ABCDEF";
    std::string result(16, '0');
    for (int i=15; i>=0; --i) { result[i]=hex[bits & 15]; bits >>= 4; }
    return result;
}
class Row {
    friend class Journal;
    std::array<std::string, field_count> values{};
public:
    Row &set(Field field, const std::string &value) {
        const size_t i=static_cast<size_t>(field);
        ensure(i >= static_cast<size_t>(Field::MaterialIndex) && i < field_count, "reserved/unknown field");
        for (unsigned char c: value) ensure(c < 128 && c != ',' && c != '\r' && c != '\n' && c != '"', "noncanonical token");
        values[i]=value;
        return *this;
    }
    Row &number(Field field, uint64_t value) { return set(field, std::to_string(value)); }
};

class Journal {
    struct Close { void operator()(FILE *f) const noexcept { if (f) std::fclose(f); } };
    std::unique_ptr<FILE, Close> file;
    std::array<std::string, field_count> common{};
    uint64_t horizon, index=0, last_tick=0, last_transaction=0, pending_tick=0;
    bool pending=false, ended=false, poisoned=false;
    void output(const std::string &text) {
        // Once attempted, any write/flush failure permanently poisons this writer.
        poisoned=true;
        ensure(std::fwrite(text.data(), 1, text.size(), file.get()) == text.size() &&
               std::fflush(file.get()) == 0 && !std::ferror(file.get()), "admission journal write/flush failed");
        poisoned=false;
    }
public:
    Journal(const std::string &path, Policy policy, Schedule schedule, uint64_t end, unsigned width, unsigned height): horizon(end) {
        ensure(end > 0 && end <= UINT32_MAX && width > 0 && width <= 40 && height > 0 && height <= 40, "journal dimensions/horizon");
        const char *p=nullptr, *s=nullptr;
        switch (policy) {
            case Policy::Native: p="NATIVE_VACANCY"; break;
            case Policy::Reject: p="STRATIFIED_REJECT"; break;
            case Policy::Replace: p="STRATIFIED_REPLACE"; break;
        }
        switch (schedule) {
            case Schedule::Immediate: s="IMMEDIATE"; break;
            case Schedule::Delay500: s="DELAY500"; break;
        }
        ensure(p && s, "unknown journal policy");
        auto put=[&](Field f, const std::string &v) { common[static_cast<size_t>(f)]=v; };
        put(Field::Version,"SM-B003-ADMISSION-1"); put(Field::Policy,p); put(Field::Schedule,s);
        put(Field::Horizon,std::to_string(end)); put(Field::Width,std::to_string(width)); put(Field::Height,std::to_string(height));
        put(Field::BufferSize,"2001"); put(Field::SourceDisposition,"RETAIN");
        file.reset(std::fopen(path.c_str(), "wx"));
        ensure(bool(file), "exclusive admission journal open failed");
        std::string header;
        for (size_t i=0; i<field_count; ++i) { if (i) header+=','; header+=columns[i]; }
        output(header+'\n');
    }
    Journal(const Journal &)=delete;
    Journal &operator=(const Journal &)=delete;
    bool failed() const { return poisoned; }
    void emit(Event event, uint64_t tick, uint64_t transaction, Row row) {
        ensure(file && !poisoned && !ended, "closed/poisoned journal");
        ensure(tick >= last_tick && tick <= horizon && index < INT64_MAX, "journal clock/index");
        const char *name=nullptr;
        switch (event) {
            case Event::Start:
                ensure(index == 0 && tick == 0 && transaction == 0, "START order"); name="START"; break;
            case Event::Begin:
                ensure(index && !pending && transaction == last_transaction+1 && tick < horizon, "BEGIN order"); name="BEGIN"; break;
            case Event::Resolve:
                ensure(pending && transaction == last_transaction && tick == pending_tick, "RESOLVE order"); name="RESOLVE"; break;
            case Event::End:
                ensure(index && !pending && transaction == 0, "END order"); name="END"; break;
        }
        ensure(name != nullptr, "unknown event");
        for (size_t i=0; i<static_cast<size_t>(Field::MaterialIndex); ++i) row.values[i]=common[i];
        auto put=[&](Field f, const std::string &v) { row.values[static_cast<size_t>(f)]=v; };
        put(Field::Event,name); put(Field::Tick,std::to_string(tick)); put(Field::Index,std::to_string(index+1)); put(Field::Transaction,std::to_string(transaction));
        std::string text;
        for (size_t i=0; i<field_count; ++i) {
            const auto &value=row.values[i];
            ensure(value.size() <= 65536 && text.size()+value.size()+1 <= 65536, "journal row size");
            if (i) text+=',';
            text+=value;
        }
        ensure(text.size() < 65536, "journal row size including LF");
        output(text+'\n');
        ++index; last_tick=tick;
        if (event == Event::Begin) { pending=true; pending_tick=tick; last_transaction=transaction; }
        if (event == Event::Resolve) pending=false;
        if (event == Event::End) {
            ended=true; poisoned=true;
            ensure(std::fclose(file.release()) == 0, "journal close failed");
            poisoned=false;
        }
    }
};
} // namespace sm_b003
#endif
