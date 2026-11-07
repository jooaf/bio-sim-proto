// Read-only native cleanup-branch probe; no population or admission execution.
#include <array>
#include <cassert>
#include <cstdio>
#include "default_config.h"
#include "alignment.h"
#include "agent.h"

int main() {
    std::puts("active_empty,passive_empty,hidden,action");
    for (int active_empty: {0,1}) for (int passive_empty: {0,1}) for (int hidden: {0,1}) {
        std::array<char,2001> active{}, passive{};
        if (!active_empty) active[0]='A';
        if (!passive_empty) passive[0]='B';
        if (hidden) { active[10]='Z'; passive[11]='Y'; }
        s_ag a{}, b{};
        a.S=active.data(); b.S=passive.data();
        a.pass=&b; b.exec=&a; a.status=B_ACTIVE; b.status=B_PASSIVE;
        for (int t=0; t<2; ++t) a.i[t]=a.r[t]=a.w[t]=a.f[t]=t?a.S:b.S;
        const int action=AgentCheckZeroLengthString(&a);
        assert(action == (active_empty?1:passive_empty?2:0));
        assert(active[10] == (hidden?'Z':0) && passive[11] == (hidden?'Y':0));
        std::printf("%d,%d,%d,%d\n",active_empty,passive_empty,hidden,action);
    }
}
