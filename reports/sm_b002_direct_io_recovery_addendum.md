# SM-B002-R2/R3 — prospective operational I/O recovery

The user requires continued autonomous engineering recovery after operational
failures. This addendum is frozen before R2 or R3 assay execution. All R1 attempts,
including its 38 timeouts, remain preserved. R1's partial arm counts are not
interpreted biologically and never select or change a scientific input.

## Measured mechanism and operational qualification

The preregistered development screen uses seed 202620999 and unchanged native
bytes/config/logging. Initial measurements: POSIX-image serial execution 258 s;
direct exFAT serial 16 s; six direct exFAT executions 16–18 s each. All completed
outputs matched the frozen development reference byte-for-byte. The remaining
POSIX six-worker profile is retained whether it finishes or times out. This is a
fixed-order descriptive screen, not a randomized performance study.

The diagnostic plan's rule selects six direct-I/O workers only when all six
complete with exact parity and maximum elapsed time <=300 seconds; otherwise two
must qualify separately. Before R2, independently validate direct-I/O execution for
**all four arms**, on the same development seed, against their own frozen native
outputs and ordered-journal replay. A faster but different result blocks launch.

## Storage separation

- Immutable configs, manifests, receipts, source provenance and analyses: the
  existing POSIX image on Elements, under `/tmp/sm/r2` (or `/tmp/sm/r3`).
- Native raw journals: ordinary exFAT directories under
  `/run/media/jojo/Elements/bio-sim-results/sm-b002-r2/runs/` (or `r3`).
- Receipts live in the POSIX control tree and hash every raw file. No filesystem
  permission semantics are assumed for ordinary exFAT files.
- Controls, analyses, provenance and reports are exported and checksum-verified
  alongside the raw journals for direct macOS access.

The native binary, chemistry, seed matrix, initial states, logging, 5,000-tick
biological horizon and original decision/replay code remain unchanged. Config
comparison permits only the already documented SUBMAT pathname relocation.
All R1-successful outputs must match corresponding completed R2 outputs exactly;
this is a reproducibility check, not pooling or reuse of scientific observations.

## Fixed attempt ladder

1. **R2:** the diagnostic-qualified worker count (at most six), direct raw I/O,
   unchanged **600-second** wall-time safety limit, all 80 inputs executed anew.
2. Run independent ordered replay and repeat analysis, retain every failure in
   the denominator of 80, and export all outcomes.
3. If R2 is scientifically evaluable, stop this recovery ladder regardless of
   whether its biological classification is favorable. Never rerun valid negatives.
4. Only if every integrity failure is a verified process timeout, all 80 receipts
   exist, every other run passes replay, and no raw/inventory/source error exists,
   automatically proceed to **R3**. Requalify all four development arms serially,
   then rerun the entire unchanged matrix serially with one fixed **3,600-second
   wall-time safety limit** for every run. This changes engineering headroom, not
   the 5,000-tick biological horizon. No partial state is resumed or substituted.
5. R3 also receives full independent replay, repeat analysis and verified export.
   Exact-output crosschecks include all previously completed runs from R1/R2.
   A further integrity problem requires diagnosis, not an unbounded retry loop.

No R3 follows missing receipts, source drift, different successful output bytes,
or a conservation/replay defect. Those require engineering investigation. This
bounded automatic ladder does not replace reasoning about unexpected failures.
Stopping an invalid attempt must not be represented as active autonomous work.

## Prelaunch and reporting

Require the pinned R1 preparation, receipt matrix and both analysis hashes; R1 must
be documented as an operationally invalid attempt. Verify the preserved R1 live-
gate artifact hashes, unchanged scientific source and native/config bytes, and
reproducible qualified diagnostic receipts. Freeze the new driver/tests/addendum
and execution script in a clean commit directly observed on origin/main.
Require >=100 GiB free on the ordinary external volume and >=10 GiB free in the
POSIX control image. Before each assay, enforce a 2-GiB raw/1-GiB control emergency
floor. Do not silently fall back to internal storage.

The new pipeline automatically connects qualification, immutable preparation,
execution, both analyses, export, and the narrowly authorized serial fallback.
Independent reference replay is unchanged; byte-identical repeat analysis checks
reproducibility, not independent implementations. All original control/exposure
thresholds and the eight-branch decision ladder apply without modification.
Admission-stage execution remains unauthorized. A verified negative classification
is reported as such rather than recast as an infrastructure problem.
