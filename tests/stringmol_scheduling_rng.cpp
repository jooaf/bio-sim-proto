// Test-only wrapper: call the exact release main (only its symbol is renamed),
// then observe all MT words and the cursor after the full run and destructors.
#include <cstdio>
#include "mt19937-2.h"
extern "C" int sm_b001_native_main(int argc, char **argv);
int main(int argc, char **argv) {
    int result=sm_b001_native_main(argc,argv);
    FILE *fp=fopen("final_rng.txt","wx");
    if(!fp) return 91;
    MersenneTwisterPrintStatusToFile(fp);
    if(fflush(fp) || ferror(fp) || fclose(fp)) return 92;
    return result;
}
