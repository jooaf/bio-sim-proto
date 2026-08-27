# Equilibrium-search results

## Executive summary

Pure parameter tuning did not produce equilibrium because chemical free energy flowed one-way into heat. Even a 10,000-tick zero-maintenance and zero-reproduction-cost control declined after an early population boom. The successful intervention was opt-in passive primary production, which conservatively transfers local heat back into chemical energy stored by existing body molecules.

The best explored profile was primary production 0.0125, maintenance 0.40, reproduction cost 0.20, asexual floor 0.50, and 4,900 deposits. Across ten 10,000-tick seeds it had 0 extinctions, 4 strict equilibrium passes, median late population 618, median trend -4.4% per 1,000 ticks, median late births/death 0.882, and median population CV 0.023. Seed 80 was nearly stationary at a late mean of 4,029 organisms, trend -0.3% per 1,000 ticks, births/death 0.995, and CV 0.004. The result remains seed-sensitive and is not a new default.

All 195 runs preserved every element exactly. Maximum absolute energy error remained below 1.76e-7.

## Operational criterion and all conditions

A run passes when its final 1,000 ticks have mean population ≥30, absolute normalized trend ≤20% per 1,000 ticks, births/deaths in [0.85, 1.15], CV ≤0.35, no extinction, and valid conservation checks.

| Stage | Condition | Passes | Extinct | Late population | Trend/1K | Births/death | CV | Species | Energy blocked | Score |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| closed_control | `maint-0_cost-0_floor-0p5` | 0/1 | 0/1 | 282.6 | -34.2% | 0.190 | 0.099 | 7.0 | 0.0% | 1.802 |
| confirm | `production-0p0125_maint-0p4` | 4/10 | 0/10 | 618.2 | -4.4% | 0.882 | 0.023 | 3.5 | 37.4% | 0.209 |
| confirm | `production-0p01_maint-0p4` | 4/10 | 0/10 | 612.2 | -4.6% | 0.853 | 0.038 | 2.5 | 55.6% | 0.240 |
| fertility | `cost-0_floor-0p5` | 0/3 | 0/3 | 47.8 | -93.4% | 0.532 | 0.271 | 3.0 | 0.0% | 1.541 |
| fertility | `cost-0_floor-0p7` | 0/3 | 1/3 | 42.9 | -95.8% | 0.414 | 0.277 | 2.0 | 0.0% | 1.669 |
| fertility | `cost-0_floor-0p9` | 0/3 | 0/3 | 54.6 | -109.8% | 0.419 | 0.317 | 2.0 | 0.0% | 2.027 |
| fertility | `cost-0p1_floor-0p5` | 0/3 | 0/3 | 46.4 | -95.3% | 0.500 | 0.278 | 2.0 | 83.2% | 1.667 |
| fertility | `cost-0p1_floor-0p7` | 0/3 | 0/3 | 35.7 | -81.3% | 0.562 | 0.237 | 2.0 | 86.8% | 1.511 |
| fertility | `cost-0p1_floor-0p9` | 0/3 | 0/3 | 40.7 | -98.8% | 0.448 | 0.288 | 2.0 | 89.7% | 1.977 |
| fertility | `cost-0p2_floor-0p5` | 1/3 | 0/3 | 39.1 | -49.2% | 0.527 | 0.145 | 2.0 | 83.6% | 0.933 |
| fertility | `cost-0p2_floor-0p7` | 0/3 | 0/3 | 40.3 | -86.3% | 0.452 | 0.250 | 2.0 | 86.3% | 1.511 |
| fertility | `cost-0p2_floor-0p9` | 0/3 | 0/3 | 37.9 | -104.5% | 0.330 | 0.304 | 2.0 | 88.2% | 1.953 |
| production | `production-0p02_maint-0p4` | 0/3 | 0/3 | 102.8 | -65.5% | 0.440 | 0.191 | 5.0 | 80.7% | 1.275 |
| production | `production-0p02_maint-0p55` | 0/3 | 0/3 | 60.0 | -67.5% | 0.475 | 0.200 | 4.0 | 81.7% | 1.165 |
| production | `production-0p02_maint-0p7` | 0/3 | 0/3 | 55.0 | -84.6% | 0.492 | 0.245 | 3.0 | 79.6% | 1.356 |
| production | `production-0p05_maint-0p4` | 0/3 | 0/3 | 91.4 | -56.2% | 0.531 | 0.163 | 4.0 | 83.0% | 1.280 |
| production | `production-0p05_maint-0p55` | 0/3 | 0/3 | 73.1 | -74.0% | 0.567 | 0.214 | 4.0 | 80.5% | 1.264 |
| production | `production-0p05_maint-0p7` | 0/3 | 0/3 | 41.0 | -57.0% | 0.622 | 0.168 | 3.0 | 78.7% | 0.953 |
| production | `production-0p1_maint-0p4` | 0/3 | 0/3 | 81.2 | -56.1% | 0.534 | 0.167 | 4.0 | 81.5% | 0.928 |
| production | `production-0p1_maint-0p55` | 0/3 | 0/3 | 67.2 | -92.0% | 0.554 | 0.267 | 4.0 | 79.6% | 1.622 |
| production | `production-0p1_maint-0p7` | 0/3 | 0/3 | 36.5 | -78.1% | 0.651 | 0.257 | 3.0 | 76.9% | 0.932 |
| production | `production-0p25_maint-0p4` | 0/3 | 0/3 | 92.3 | -57.4% | 0.518 | 0.175 | 4.0 | 79.9% | 1.121 |
| production | `production-0p25_maint-0p55` | 0/3 | 0/3 | 56.9 | -89.7% | 0.509 | 0.264 | 4.0 | 79.8% | 1.379 |
| production | `production-0p25_maint-0p7` | 0/3 | 0/3 | 42.0 | -89.4% | 0.625 | 0.268 | 3.0 | 77.3% | 1.476 |
| production2 | `production-0p005_maint-0p4` | 0/3 | 0/3 | 146.9 | -92.1% | 0.404 | 0.269 | 4.0 | 77.0% | 1.628 |
| production2 | `production-0p005_maint-0p55` | 1/3 | 0/3 | 58.8 | -67.1% | 0.500 | 0.200 | 4.0 | 68.0% | 1.164 |
| production2 | `production-0p005_maint-0p7` | 1/3 | 0/3 | 43.5 | -27.7% | 0.763 | 0.092 | 4.0 | 76.1% | 0.347 |
| production2 | `production-0p01_maint-0p4` | 2/3 | 0/3 | 635.1 | -0.7% | 0.951 | 0.018 | 5.0 | 72.5% | 0.104 |
| production2 | `production-0p01_maint-0p55` | 0/3 | 0/3 | 228.8 | -33.3% | 0.714 | 0.100 | 4.0 | 79.8% | 1.102 |
| production2 | `production-0p01_maint-0p7` | 0/3 | 0/3 | 94.9 | -62.9% | 0.585 | 0.193 | 4.0 | 70.6% | 1.257 |
| production2 | `production-0p025_maint-0p4` | 1/3 | 0/3 | 1549.0 | +5.5% | 1.195 | 0.016 | 9.0 | 12.7% | 0.178 |
| production2 | `production-0p025_maint-0p55` | 0/3 | 0/3 | 1502.7 | +13.2% | 1.278 | 0.041 | 8.0 | 14.3% | 0.245 |
| production2 | `production-0p025_maint-0p7` | 0/3 | 0/3 | 1517.5 | +16.7% | 1.726 | 0.049 | 8.0 | 34.7% | 0.566 |
| production2 | `production-0p05_maint-0p4` | 0/3 | 0/3 | 1895.2 | +17.2% | 1.436 | 0.052 | 10.0 | 0.0% | 0.362 |
| production2 | `production-0p05_maint-0p55` | 1/3 | 0/3 | 1559.3 | +16.5% | 1.514 | 0.049 | 10.0 | 0.0% | 0.415 |
| production2 | `production-0p05_maint-0p7` | 1/3 | 0/3 | 1521.7 | +17.6% | 1.451 | 0.052 | 9.0 | 4.0% | 0.372 |
| refine | `production-0p005_maint-0p7` | 0/5 | 1/5 | 28.6 | -54.4% | 0.304 | 0.162 | 1.0 | 86.3% | 1.580 |
| refine | `production-0p0075_maint-0p55` | 1/5 | 0/5 | 165.8 | -21.3% | 0.666 | 0.069 | 3.0 | 77.4% | 0.615 |
| refine | `production-0p01_maint-0p4` | 2/5 | 0/5 | 733.1 | -4.3% | 0.912 | 0.020 | 7.0 | 66.0% | 0.288 |
| reproduction | `cost-0_floor-0p2` | 0/3 | 0/3 | 29.8 | -99.1% | 0.333 | 0.287 | 2.0 | 0.0% | 1.947 |
| reproduction | `cost-0_floor-0p35` | 0/3 | 0/3 | 46.1 | -107.7% | 0.400 | 0.314 | 3.0 | 0.0% | 1.919 |
| reproduction | `cost-0p1_floor-0p2` | 0/3 | 0/3 | 40.0 | -73.4% | 0.415 | 0.223 | 3.0 | 75.0% | 1.413 |
| reproduction | `cost-0p1_floor-0p35` | 0/3 | 0/3 | 39.8 | -84.2% | 0.533 | 0.245 | 3.0 | 81.3% | 1.615 |
| reproduction | `cost-0p2_floor-0p2` | 0/3 | 0/3 | 36.2 | -61.0% | 0.497 | 0.181 | 3.0 | 76.7% | 1.109 |
| reproduction | `cost-0p2_floor-0p35` | 0/3 | 0/3 | 35.5 | -53.0% | 0.537 | 0.156 | 2.0 | 81.3% | 0.956 |
| reproduction | `cost-0p3_floor-0p2` | 0/3 | 0/3 | 32.6 | -115.2% | 0.366 | 0.335 | 2.0 | 77.6% | 2.272 |
| reproduction | `cost-0p3_floor-0p35` | 0/3 | 0/3 | 36.5 | -106.1% | 0.395 | 0.310 | 3.0 | 80.0% | 2.040 |
| screen | `maint-0p25_distributed` | 0/3 | 0/3 | 71.7 | -56.5% | 0.429 | 0.166 | 5.0 | 82.2% | 1.212 |
| screen | `maint-0p25_rich` | 0/3 | 0/3 | 80.7 | -65.5% | 0.331 | 0.191 | 4.0 | 81.1% | 1.480 |
| screen | `maint-0p25_standard` | 0/3 | 0/3 | 67.1 | -83.5% | 0.292 | 0.255 | 4.0 | 86.2% | 1.552 |
| screen | `maint-0p4_distributed` | 0/3 | 0/3 | 40.3 | -70.3% | 0.368 | 0.224 | 3.0 | 80.7% | 1.498 |
| screen | `maint-0p4_rich` | 0/3 | 0/3 | 44.6 | -66.3% | 0.500 | 0.192 | 4.0 | 83.1% | 1.439 |
| screen | `maint-0p4_standard` | 0/3 | 0/3 | 40.8 | -78.4% | 0.356 | 0.239 | 3.0 | 82.5% | 1.751 |
| screen | `maint-0p55_distributed` | 0/3 | 0/3 | 35.5 | -61.6% | 0.518 | 0.180 | 3.0 | 77.5% | 1.073 |
| screen | `maint-0p55_rich` | 0/3 | 0/3 | 34.9 | -73.8% | 0.455 | 0.237 | 3.0 | 77.4% | 1.355 |
| screen | `maint-0p55_standard` | 0/3 | 0/3 | 21.6 | -78.9% | 0.357 | 0.229 | 2.0 | 80.3% | 1.624 |
| screen | `maint-0p7_distributed` | 0/3 | 0/3 | 24.9 | -93.1% | 0.478 | 0.277 | 3.0 | 75.4% | 1.589 |
| screen | `maint-0p7_rich` | 0/3 | 0/3 | 29.4 | -71.7% | 0.514 | 0.212 | 2.0 | 72.6% | 1.217 |
| screen | `maint-0p7_standard` | 0/3 | 0/3 | 20.2 | -66.5% | 0.567 | 0.195 | 2.0 | 76.2% | 1.263 |
