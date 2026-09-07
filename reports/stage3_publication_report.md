# Stage 3 raw-results publication

Published 2026-09-07 with the repository `just publish-to` recipe.

Destination root:

```text
jojo@100.80.185.9:/home/jojo/bio-sim-results/Joels-MacBook-Pro-2.local/
```

Published append-only directories:

1. `stage3r_reproduction_liveness`
2. `stage3r_lineage_patch`
3. `stage3_vacancy_pilot`
4. `stage3_exact_copy_pilot`
5. `stage3_vacancy_lineage`
6. `stage3_energy_liveness`
7. `stage3_energy_birth`
8. `stage3_lineage_persistence`
9. `stage3_organization_diagnostic`

All nine `just publish-to` commands exited successfully. Each local source directory contains a `PUBLISHED.json` marker and the publisher finalized each remote directory only after `rsync` succeeded.

The publication markers record Git commit `6422991`. They also truthfully record a dirty checkout because unrelated `organism-sim/` work and the documentation updates in this commit were present. Scientific provenance remains pinned independently in each run manifest and the compact checksummed campaign manifests under `reports/`.
