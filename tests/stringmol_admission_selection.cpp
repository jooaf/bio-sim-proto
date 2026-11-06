// Mechanical selector prototype only: no native population, cleavage or eviction.
// Link the exact pinned native MT object; compare complete RNG state with an
// independent straight-line draw consumer. Biology/transaction gates remain open.
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>
#include "mt19937-2.h"

enum class Policy { Native, Reject, Replace };
Policy parse_policy(const std::string &name) {
    if (name == "NATIVE_VACANCY") return Policy::Native;
    if (name == "STRATIFIED_REJECT") return Policy::Reject;
    if (name == "STRATIFIED_REPLACE") return Policy::Replace;
    throw std::runtime_error("unknown policy");
}

int main(int argc, char **argv) {
    try {
        if (argc != 4) throw std::runtime_error("mode seed layout-or-count required");
        const std::string mode(argv[1]);
        const unsigned long seed = std::stoul(argv[2]);
        if (seed < 1 || seed > 64) throw std::runtime_error("synthetic RNG fixture seeds only");
        SetRNGSeed(seed);
        std::vector<double> values;
        auto draw = [&]() { double value = GenerateRandomDouble(); values.push_back(value); return value; };
        const char *channel = "VACANT", *disposition = "NO_CANDIDATE";
        int target = -1, count = 0;
        if (mode == "reference") {
            const int n = std::stoi(argv[3]);
            if (n < 0 || n > 2) throw std::runtime_error("reference draw count");
            for (int i = 0; i < n; ++i) draw();
        } else {
            const Policy policy = parse_policy(mode);
            const std::string grid(argv[3]);
            if (grid.size() != 6 || grid.substr(0, 2) != "AP") throw std::runtime_error("fixture grid");
            const bool occupied = policy != Policy::Native && draw() < 0.5;
            channel = occupied ? "OCCUPIED" : "VACANT";
            std::vector<int> candidates;
            for (int cell = 0; cell < 6; ++cell) {
                if (std::string("APUXYZH.").find(grid[cell]) == std::string::npos) throw std::runtime_error("fixture occupant");
                if (occupied ? grid[cell] == 'U' : grid[cell] == '.') candidates.push_back(cell);
            }
            count = static_cast<int>(candidates.size());
            if (count) {
                target = candidates.at(static_cast<size_t>(std::floor(draw() * count)));
                disposition = !occupied ? "ADMIT_VACANCY" : policy == Policy::Replace ? "ADMIT_REPLACEMENT" : "REJECT_OCCUPIED";
            }
        }
        std::printf("{\"channel\":\"%s\",\"disposition\":\"%s\",\"target\":%d,\"candidate_count\":%d,\"values\":[", channel, disposition, target, count);
        for (size_t i = 0; i < values.size(); ++i) std::printf("%s%.17g", i ? "," : "", values[i]);
        std::printf("]}\n");
        MersenneTwisterPrintStatusToFile(stdout);
        return std::fflush(stdout) || std::ferror(stdout) ? 91 : 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 92;
    }
}
