# Bounded, predeclared pilot: one seed per BFF dimensionality.
# These pilots validate instrumentation and generate estimates; they are not
# evidence for dimensional differences without additional predeclared replicates.

let root = ($env.FILE_PWD | path dirname | path dirname)
let runner = ($root | path join 'experiments' 'replicator_length_study' 'run_bff_dimensions.py')
let results = ($root | path join 'experiments' 'replicator_length_study' 'results')

uv run python $runner --dimension 0 --population-size 128 --ticks 512 --max-steps 512 --metric-interval 16 --functional-density-samples 64 --functional-sample-size 16 --output-dir ($results | path join 'pilot-0d-seed-0')
uv run python $runner --dimension 1 --population-size 128 --width 128 --ticks 512 --max-steps 512 --metric-interval 16 --functional-density-samples 64 --functional-sample-size 16 --output-dir ($results | path join 'pilot-1d-seed-0')
uv run python $runner --dimension 2 --population-size 128 --width 16 --height 8 --ticks 512 --max-steps 512 --metric-interval 16 --functional-density-samples 64 --functional-sample-size 16 --output-dir ($results | path join 'pilot-2d-seed-0')
