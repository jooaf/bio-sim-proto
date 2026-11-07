// Deliberately invalid controls: prove ASan/UBSan actually execute.
#include <climits>
#include <cstring>
#include <cstdlib>

__attribute__((noinline)) int read_freed(int *p) { return *p; }
int main(int argc, char **argv) {
    if (argc < 2) return 2;
    if (!std::strcmp(argv[1], "uaf")) {
        int *p = new int(17);
        delete p;
        return read_freed(p);
    }
    if (!std::strcmp(argv[1], "overflow")) {
        volatile int maximum = INT_MAX;
        return maximum + argc;
    }
    return 2;
}
