# SM-XL001 frozen exploratory plan v1

Frozen before population outcomes, 2026-11-16. Scope: module 4, canonical host-only interaction locality versus offspring-placement locality. Not a continuation/rescue of B003, no replacement, parasites, BFF, H003 or confirmation.

## Complete population budget

Exactly four cells: GG (0,0), LG (1,0), GL (0,1), LL (1,1), where coordinates are INTERACTION_RADIUS, PLACEMENT_RADIUS. Each cell receives development seed **202620999**, with three executions: fully observed, exact observed repeat, observation-disabled. Total **12** population executions including all qualification/repeats. No other population executions, no retries. This seed is an inherited used development seed (lineage/renewal/scheduling workflows); not unseen. One independent realization per cell, technical repeats not replication. All executions use 5,000 ticks, timeout 600 s. Qualification unit fixtures do not run a population loop. Run cells serially; at most one native/replay process. Replay timeout 1,800 s. No expansion based on outcome.

Fixed config: configure_control canonical HOST sequence, fixed 140 host positions in its 15×10 rectangle minus ten-cell stripe, 40×40 torus, initial occupancy 140/1600. Initial occupancy and arrangement held constant, not dynamically clamped. Mutation 0, decay .0005, IMMEDIATE offspring eligibility, source RETAIN, NATIVE_VACANCY only, exact symbol conservation, zero initial free pool, decay recycling, report every 100 ticks. Use copied patch0001–0006 native source /tmp/sm/a7 (never modify original), no B003 admission adapter. Native default vacancy is the control, not stratified vacancy/replacement. Fresh build -j2.

## Actual semantics and confounds

Radius zero is a special global mode, NOT a distance-zero neighborhood. Global interaction uniformly chooses eligible unbound agents in remaining now-list order. Local radius one uniformly chooses eligible unbound G_NOW agents among eight toroidal Moore neighbors, scanning dx then dy; excludes origin. Local placement scans the nine Moore cells (origin occupied by active parent), uniformly chooses currently empty cell, centered on ACTIVE executor, not necessarily cleavage flow source. Global placement uniformly samples all empty cells in x-major order. No vacancy means failure and native cleanup/material return, never replacement. Only radii 0/1 are in scope; large-radius duplicate wrapping is not qualified.

Locality changes candidate count, RNG consumption, spatial arrangement, crowding, and accessible vacancies; cells sharing seeds are not matched random streams. Initial clumping is intentional fixed context. Occupancy trajectories are outcomes, not held fixed; radius affects encounters as well as their composition. No causal assignment to one downstream mediator from this pilot.

## Gates and positive controls

Before population launch: inspect source and logging; directed native fixtures for toroidal eligibility/rank including non-first neighbor, global distant eligibility, active-centered placement, full-local failure despite distant vacancy, global success, no occupancy overwrite. Synthetic independent geometry/rank verifier positives and tampered negatives. Exact conservation existing mechanism tests plus directed native invariants. Native source/build/config hashes retained. Existing admission replay is GLOBAL ONLY and cannot validate this experiment: its adapter explicitly rejects radii. Implement a separately justified verifier for native vacancy locality or fail closed with exact evidence; do not relabel old replay as local validation.

Within the frozen 12: observed repeat byte parity; observer-disabled parity on all common native files (exclude only documented observation streams). Independent reconstruction of local candidate ordering/rank, placement, conservation and linked lifecycle required for every observed cell before interpretation. Failure in any gate prevents population interpretation across the matrix, even if native output looks positive. GG is the canonical positive population control: require >=100 successful births and nonempty population at tick 4900; failure is a valid control-negative, not grounds to tune. Mechanical positive controls distinguish implemented locality from mere extinction.

## Frozen descriptive endpoints

Per cell: horizon/extinction, checkpoint population and tick4900 population, total births and partial (offset>0 with surviving source) transfers, reproductive descendant reuse (exclude founders), search count, empty searches, encounter count, bound encounters, nonempty cleavage attempts, successful and failed placements, vacancy availability, spatial occupied-neighbor fraction at checkpoints. Report raw counts and denominators; no p-values, adaptation, robustness or confirmatory claims. Trace ancestry is not competence proof with standardized partners. Report any unavailable endpoint explicitly rather than infer from absent logging.

## Storage and stop rules

Own worktree /tmp/sm/xl on explore/sm-xl001; controls /tmp/sm/xl-e in Elements POSIX image. Raw /run/media/jojo/Elements/bio-sim-results/sm-xl001-exploration-v1; portable verification /run/media/jojo/Elements/bio-sim-results/verification/sm-xl001-exploration-v1. Check mount/free space before output and batch. Additional POSIX <=4 GiB, raw <=25 GiB; stop new launches below 5 GiB POSIX or 10 GiB raw free, obey stronger inherited limits. Preserve failures, no overwrite/retry. Export ordinary regular files with SHA256 verification; retain seals in image. Shared read-only Python /var/home/jojo/bio-sim-proto/.venv/bin/python, cwd this worktree. No installs, agents, parent tasks, shared evidence edits, push/merge. Commit own source and hand off actual process state.
