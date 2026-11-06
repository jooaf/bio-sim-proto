# Wait for development qualification, then run the complete R2/R3 recovery ladder.
# Usage: nu tools/run_sm_b002_io_recovery.nu --commit <published-source-commit>
# The native matrix, independent/repeat replay, export, and timeout-only serial
# fallback are connected. Valid scientific non-passes never trigger a rerun.
def checked [program: string, args: list<string>, name: string, logs: string] {
    {stage: $name, started: (date now)} | to nuon | save --force ($logs | path join 'status.nuon')
    let code = try {
        ^$program ...$args out> ($logs | path join ($name + '.stdout')) err> ($logs | path join ($name + '.stderr'))
        $env.LAST_EXIT_CODE
    } catch {|err| $err.exit_code? | default 1 }
    {stage: $name, exit_code: $code, finished: (date now)} | to nuon | save --force ($logs | path join ($name + '.result.nuon'))
    if $code != 0 { error make {msg: $'Recovery stopped at ($name): inspect ($logs); retain evidence and continue engineering diagnosis'} }
}

def main [--commit: string] {
    if $commit == null or $commit !~ '^[0-9a-f]{40}$' { error make {msg: 'Exact published commit required'} }
    let store = '/run/media/jojo/Elements/bio-sim-results'
    if (^findmnt -n -o TARGET --target $store | str trim) != '/run/media/jojo/Elements' { error make {msg: 'Elements not mounted'} }
    let logs = $store | path join 'verification/sm-b002-io-recovery'
    mkdir $logs
    $nu.pid | into string | save --force ($logs | path join 'pid')
    {stage: 'waiting-for-development-qualification', started: (date now)} | to nuon | save --force ($logs | path join 'status.nuon')
    let diagnostic = $store | path join 'timeout-diagnostics-v1'
    while not (($diagnostic | path join 'COMPLETE.json') | path exists) {
        let pid = (open --raw ($diagnostic | path join 'pid') | str trim | into int)
        if (ps | where pid == $pid | is-empty) { error make {msg: 'Diagnostic stopped without qualification; inspect its logs before repairing/restarting development work'} }
        sleep 10sec
    }
    cd /tmp/sm/p
    if (git status --porcelain | str trim | is-not-empty) { error make {msg: 'Recovery checkout is dirty; do not overwrite user work'} }
    checked 'git' ['fetch' 'origin' 'main'] 'fetch-source' $logs
    checked 'git' ['checkout' '--detach' $commit] 'freeze-source' $logs
    $env.NUMBA_NUM_THREADS = '1'
    let python = '/tmp/sm/p/.venv/bin/python'
    checked $python ['-m' 'pytest' '-q'] 'full-regression' $logs
    checked $python ['-m' 'mypy' 'experiments/stringmol/diagnose_retirement_runtime.py' 'experiments/stringmol/recover_retirement_io.py' 'tests/test_stringmol_runtime_diagnostics.py' 'tests/test_stringmol_io_recovery.py'] 'strict-types' $logs
    checked $python ['-m' 'experiments.stringmol.recover_retirement_io'] 'complete-recovery-ladder' $logs
    let final = [($store | path join 'sm-b002-r3/COMPLETE.json') ($store | path join 'sm-b002-r2/COMPLETE.json')] | where { |path| $path | path exists } | first
    let result = open $final
    if not $result.integrity or not $result.export_verified { error make {msg: 'No scientifically evaluable, verified final attempt'} }
    {result: $result, receipt: $final, finished: (date now)} | to nuon | save --force ($logs | path join 'COMPLETE.nuon')
}
