# Pinned Spatial Stringmol control

This directory builds an external, independently published artificial chemistry for the retained Phase 2 parasite gate. It is an ecological control, not part of the conserved BFF simulator.

## Build

```nu
nu experiments/stringmol/bootstrap.nu --test
```

The bootstrap script:

1. clones `source.lock.json`'s exact upstream commit into ignored `vendor/stringmol/`;
2. applies the reviewed patch series from `patches/`;
3. builds the release binary;
4. optionally runs the upstream Catch test suite and requires its pass marker.

The upstream checkout and generated runs are intentionally not committed.

## Patch policy

Patches may repair reproducibility defects and expose locality controls. They must not change Stringmol binding scores, opcodes, mutation, decay, copy, or cleavage chemistry.

The current patch:

- fixes an upstream missing-braces/counter defect that returned the first eligible spatial neighbor instead of the randomly drawn neighbor;
- adds `INTERACTION_RADIUS` and `PLACEMENT_RADIUS` configuration fields;
- preserves radius 1 as the upstream default;
- uses radius 0 as an explicit global/well-mixed control;
- writes both fields into checkpoint configurations.

## Scientific order

1. Validate a fixed source-grounded parasite candidate in parasite-alone and host-plus-parasite global controls.
2. Freeze the candidate and inoculum before comparing locality.
3. Require the large-radius/global positive control to pass before interpreting a local treatment.
4. Keep all failures and exact source/config/output hashes.

See `reports/phase2_replacement_host_parasite_audit.md` for the audit and limitations.
