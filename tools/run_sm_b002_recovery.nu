# Run the complete preregistered SM-B002-R1 recovery, analysis, and Mac export.
# Usage: nu tools/run_sm_b002_recovery.nu
# Fail closed; preserve failure evidence; never resume or selectively retry assays.
def checked [python: string, args: list<string>, name: string, logs: string] {
    {stage: $name, started: (date now)} | to nuon | save --force ($logs | path join 'status.nuon')
    let code = try {
        ^$python ...$args out> ($logs | path join ($name + '.stdout')) err> ($logs | path join ($name + '.stderr'))
        $env.LAST_EXIT_CODE
    } catch {|err| $err.exit_code? | default 1 }
    {stage: $name, exit_code: $code, finished: (date now)} | to nuon | save --force ($logs | path join ($name + '.result.nuon'))
    if $code != 0 { error make {msg: $'Critical recovery failure at ($name); evidence retained in ($logs)'} }
}

def main [] {
    let store = '/run/media/jojo/Elements/bio-sim-results'
    let logs = $store | path join 'verification/sm-b002-r1'
    mkdir $logs
    $nu.pid | into string | save --force ($logs | path join 'pid')
    let mount = (^findmnt --json --target /tmp/sm --output TARGET,SOURCE,FSTYPE | from json | get filesystems | first)
    if $mount.target != '/tmp/sm' or $mount.source != ($store | path join 'stringmol-posix.ext4') or $mount.fstype not-in ['fuse.ext4', 'fuse.fuse2fs'] { error make {msg: 'Elements POSIX image not mounted; refusing local fallback'} }
    if ('/tmp/sm/r1' | path exists) { error make {msg: 'Existing R1 attempt: no resume or overwrite'} }
    cd /tmp/sm/p
    $env.NUMBA_NUM_THREADS = '1'
    let python = '/tmp/sm/p/.venv/bin/python'
    let module = 'experiments.stringmol.recover_retirement'
    checked $python ['-m' 'pytest' '-q'] 'full-regression-tests' $logs
    checked $python ['-m' 'mypy' 'experiments/stringmol/recover_retirement.py' 'tests/test_stringmol_recovery.py'] 'recovery-types' $logs
    checked $python ['-m' $module 'preflight'
        '--root' '/tmp/sm/r1/preflight'
        '--build' '/tmp/sm/b/build.json'
        '--focused' '/tmp/sm/f-vendor-restored/focused.json'
        '--scheduling' '/tmp/sm/g-vendor-restored/inherited/gates.json'
        '--predecessor' ($store | path join 'checkout/runs/sm_b002_work/prepared')
        '--cleanup' ($store | path join 'checkout/logs/sm_b002_interrupted_cleanup.json')
        '--h001' ($store | path join 'archive/bazzite/sm_h001_reproductive_renewal/bazzite.attlocal.net')
    ] 'preflight' $logs
    checked $python ['-m' $module 'prepare' '--gates' '/tmp/sm/r1/preflight/gates.json' '--root' '/tmp/sm/r1/prepared'] 'prepare' $logs
    checked $python ['-m' $module 'run' '--manifest' '/tmp/sm/r1/prepared/preparation.json'] 'matrix-80' $logs
    checked $python ['-m' $module 'analyze' '--manifest' '/tmp/sm/r1/prepared/preparation.json' '--output' '/tmp/sm/r1/analysis.json'] 'independent-replay' $logs
    checked $python ['-m' $module 'analyze' '--manifest' '/tmp/sm/r1/prepared/preparation.json' '--output' '/tmp/sm/r1/analysis-repeat.json'] 'repeat-replay' $logs
    ^cmp /tmp/sm/r1/analysis.json /tmp/sm/r1/analysis-repeat.json
    if $env.LAST_EXIT_CODE != 0 { error make {msg: 'Repeated independent analysis differs'} }
    let result = open /tmp/sm/r1/analysis.json
    $result | select branch decision integrity arms run_denominator arm_denominator paired_denominator admission_design_authorized admission_execution_authorized | to json | save /tmp/sm/r1/decision.json
    [ '# SM-B002-R1 outcome' '' $'Decision: ($result.decision)' $'Integrity: ($result.integrity)' $'Branch: ($result.branch)' 'Denominator: 80 runs, 20 per arm.' '' 'The original decision ladder is unchanged. A valid non-pass is not rerun.' 'See analysis.json and analysis-repeat.json for complete outcomes and failures.' 'See source.bundle for source and the prospective recovery addendum.' 'Native Linux binaries must be rebuilt on macOS.' 'Prelaunch POSIX evidence is preserved in prelaunch.tar and the Elements image.' '' ] | str join "\n" | save /tmp/sm/r1/REPORT.md
    git bundle create /tmp/sm/r1/source.bundle --all
    if $env.LAST_EXIT_CODE != 0 { error make {msg: 'Source bundle failed'} }
    {stage: 'portable-export', started: (date now)} | to nuon | save --force ($logs | path join 'status.nuon')
    let export = $store | path join 'sm-b002-r1'
    if ($export | path exists) { error make {msg: 'Portable destination already exists; refusing overwrite'} }
    mkdir $export
    ^rsync -rt --modify-window=2 -- /tmp/sm/r1/ ($export + '/')
    if $env.LAST_EXIT_CODE != 0 { error make {msg: 'Portable export failed'} }
    let check = (^rsync -rcn --delete --itemize-changes -- /tmp/sm/r1/ ($export + '/') | complete)
    if $check.exit_code != 0 or ($check.stdout | str trim | is-not-empty) { error make {msg: 'Portable export checksum mismatch'} }
    ^tar -cf ($export | path join 'prelaunch.tar') -C /tmp/sm b l f-vendor-restored g-vendor-restored/inherited
    if $env.LAST_EXIT_CODE != 0 { error make {msg: 'Prelaunch archive failed'} }
    ^tar --compare -f ($export | path join 'prelaunch.tar') -C /tmp/sm
    if $env.LAST_EXIT_CODE != 0 { error make {msg: 'Prelaunch archive verification failed'} }
    cd $export
    ^sha256sum prelaunch.tar | save prelaunch.tar.sha256
    ^sync
    {decision: $result.decision, integrity: $result.integrity, branch: $result.branch, completed: (date now), export: $export} | to nuon | save ($logs | path join 'COMPLETE.nuon')
    if not $result.integrity { error make {msg: 'Critical: R1 integrity unevaluable; all outcomes retained; no automatic rerun'} }
}
