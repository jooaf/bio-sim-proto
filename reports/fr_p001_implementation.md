# FR-P001 implementation and repaired validation

Status: **v2 prepared; campaign not executed**. No campaign outcome analysis was run. Source access was limited to frozen source/input validation. The preregistration, pinned production helpers, FR-I002 kernel, and registries are unchanged. Implementation was committed only after this validation.

## Validation

- Regenerated preflight passed: 5.376 seconds excluding only explicit warm-up; 297.98 MiB peak RSS. Fresh-child wall time: 10.017 seconds; explicit warm-up: 4.641 seconds.
- Frozen scoring projection: 0.452 hours. This projects scoring only, not whole-simulation wall time.
- Repeated destination resource check on `sweeps/fr_p001/v2/prepared` passed: free disk 148,866,375,680 bytes (required 29,100,081,152); available RAM 21,097,799,680 bytes (required 6,169,698,304).
- All nine source batches/checkpoints, first-origin epochs/ranks and individual seed-0 witnesses revalidated. Each witness scored 64; every frozen shuffle scored below 64. All eighteen saved soups, labels, replacement indices, pools, and targets have exactly the same raw-array hashes as the previous preparation.
- Regenerated campaign-bound isolation passed and was published under exclusive campaign coordination. Saved preparation, source archives, resource evidence, and isolation pins were revalidated without starting any run.
- 282 focused, repair-policy, mechanics, isolation, and production-helper tests passed in 23.98 seconds. Strict scoped mypy passed for all three implementation modules and both focused test files.
- The previous repository-wide mypy attempt reported 230 errors in unchanged files; this repair pass reran the requested scoped checks. Historical diagnostics remain at `sweeps/fr_p001/mypy_repository.txt`.

Machine-readable evidence: [fr_p001_validation.json](fr_p001_validation.json) and [fr_p001_observation_isolation.json](fr_p001_observation_isolation.json).

| Pair | Source seed | First-origin epoch | Frozen rank | Witness score | Shuffle score |
|---|---:|---:|---:|---:|---:|
| 0 | 202612001 | 40901 | 0 | 64 | 0 |
| 1 | 202612003 | 98001 | 0 | 64 | 0 |
| 2 | 202612008 | 31901 | 0 | 64 | 0 |
| 3 | 202612009 | 95701 | 0 | 64 | 0 |
| 4 | 202613001 | 45801 | 0 | 64 | 0 |
| 5 | 202613008 | 76601 | 85 | 64 | 0 |
| 6 | 202613010 | 28601 | 0 | 64 | 0 |
| 7 | 202613013 | 12601 | 37 | 64 | 0 |
| 8 | 202613018 | 29201 | 0 | 64 | 0 |

## Versioned repair policy (policy version 1)

Artifact schema: `fr-p001-artifacts-v2`; current output version: `v2`. `version.json` binds the output version, repair policy and run pins before preparation. Preparation and preflight archive source bytes under `frozen_sources/`; validation checks every archived hash as well as the current run identity. The preparation manifest records the fixed source checkpoint/manifest hashes and input array hashes.

**Mechanics, runner, observer, or preparation-validation repair:** use a fresh output directory and output version; regenerate preflight, preparation and isolation, then rerun the entire unchanged 18-run protocol when authorized. Current run-pin mismatch rejects resume. Do not rewrite the old manifest or migrate old callbacks. Run binding checks include the new preparation checksum, so copying completed old runs into a fresh version fails. The original unversioned artifacts remain preserved and are superseded by `sweeps/fr_p001/v2/`.

**Analyzer/report-only repair:** edit the analyzer, retain preparation and run artifacts, rerun focused validation, and write to a fresh analysis-report directory. Analyzer identity is excluded from run/preflight/isolation pins. Each analysis report saves its analyzer source copy, current analyzer hash, repair policy, and validation outcome; it verifies the source did not change during analysis. Existing analysis reports are not overwritten. Shared observer or mechanics-validator changes count as run repairs, even when prompted by an analysis finding. The synthetic regression changes only the analyzer hash, validates the same preparation, and successfully reanalyzes the same completed synthetic runs.

## Mechanics-record validation

`validate_mechanics_record` is the common validator called before observation publication, during callback verification/resume, and explicitly by the analyzer. It checks conservation, binary labels, array shapes/nonnegative integer ledgers, pairing order, withdrawal/return totals, changing-write counter, scarcity metrics versus ledgers, zero friction, cross-copy totals and per-symbol withdrawal bounds, cross-copy metrics versus execution counts, exchange totals versus successful-write counts, and execution-write counts versus steps. Successful metrics include no-ops, so exchanges are bounded by successful writes rather than incorrectly equated to them.

Tamper tests rewrite snapshot arrays, manifest fields, snapshot checksums and completion database checksums consistently. Observation, resume and analysis still reject invalid scarcity, friction, cross totals, cross-blocked counts, symbol ledgers, successful-write totals and step counts. Independent snapshot reconstruction and individual seed-0 rescoring remain mandatory; aggregate checksums alone are insufficient.

## Coordination, admission and resources

The launcher acquires its launch lock and exclusive campaign coordination before validation, isolation, or shared publication. After publishing isolation it downgrades coordination to shared, allowing workers while preventing another isolation/preparation publisher. Standalone `run-one` also holds shared campaign coordination. Every worker enters the same six file-lock slots before allocating simulation state; a seventh caller waits, and process exit releases its slot. Locks use resolved campaign paths. A competing launcher fails before validation/publication. The concurrency regression fills all six launcher slots while a separate standalone process waits, then verifies the maximum admitted worker count stays six.

Both launcher and standalone run/resume revalidate frozen preflight evidence, then repeat the frozen free-space and RAM thresholds against the actual resolved campaign output directory. Preflight-directory space is never substituted for campaign-destination space. Resource regression tests simulate sufficient preflight storage but insufficient campaign storage or RAM and verify that execution and isolation publication do not begin.

## Runtime artifacts

`experiments/fr_p001.py` owns observation, exact individual seed-0 scoring, disk-backed SQLite caching, audits, resource checks and coordination primitives. `experiments/run_fr_p001.py` prepares fixed inputs and invokes the separate FR-I002 kernel through its state adapter. `experiments/analyze_fr_p001.py` independently reconstructs occurrences and sequentially rescores eligible sequences using a fresh disk cache.

Each future run owns `runs/II_ARM/`: `binding.json`, `run.sqlite`, compressed callback snapshots and audit records, and `complete.json` after all 101 callbacks. Snapshots retain soup, labels, order, cumulative metrics, all ledgers/cross arrays and changing-write counter. SQLite tables are `scores(tape,score)`, `callbacks(epoch,manifest)` and `audit(epoch,tape,labels,abundance)`. Canonical audit bytes are exactly 64 raw bytes, one unsigned label-count byte and eight little-endian abundance bytes, sorted by tape then label count.

Callback files are flushed and renamed before the SQLite transaction publishes the callback. Resume verifies every committed callback, restores the last complete state and replays subsequent absolute epochs. Failed uncommitted observations leave no committed cache/aggregate rows. Invalid committed artifacts are not silently discarded. An integrity repair that changes run code requires a new output version and full rerun; no source replacement, subsampling, window changes or threshold changes are permitted.

## Commands

Executed for this repair:

```bash
uv run python -m experiments.run_fr_p001 preflight --output sweeps/fr_p001/v2/preflight
uv run python -m experiments.run_fr_p001 prepare --output sweeps/fr_p001/v2/prepared --output-version v2 --preflight sweeps/fr_p001/v2/preflight/preflight.json
uv run python -m experiments.run_fr_p001 validate-isolation --output sweeps/fr_p001/v2/prepared
uv run pytest -q tests/test_fr_p001.py tests/test_fr_p001_repairs.py tests/test_fr_i002_provenance.py tests/test_phase1_probe.py tests/test_paper_probe.py
uv run mypy experiments/fr_p001.py experiments/run_fr_p001.py experiments/analyze_fr_p001.py tests/test_fr_p001.py tests/test_fr_p001_repairs.py
```

Only when campaign execution is separately authorized, launch or resume:

```bash
uv run python -m experiments.run_fr_p001 launch --output sweeps/fr_p001/v2/prepared
```

Standalone execution uses `NUMBA_NUM_THREADS=1 uv run python -m experiments.run_fr_p001 run-one --output sweeps/fr_p001/v2/prepared --pair 0 --arm witness` and shares the same coordination, resource gate and six-slot limit. Neither execution entry point was called on prepared campaign inputs.

Only when outcome analysis is authorized:

```bash
uv run python -m experiments.analyze_fr_p001 --preparation sweeps/fr_p001/v2/prepared --report sweeps/fr_p001/v2/analysis-r1
```

An analyzer-only repair uses a fresh report directory such as `analysis-r2`, with the same preparation. Reports contain separate integrity, witness sampled-presence, control-specificity and paired-load gates; all trajectories, exact-target diagnostics, endpoints and the frozen directional sign tail. Incomplete or invalid artifacts yield unevaluable. A valid-integrity failure triggers the frozen stop/pivot decision. Passing supports only sampled non-exact operational-candidate presence, not continuous lineage, inherited-byte causation or biological ancestry.
