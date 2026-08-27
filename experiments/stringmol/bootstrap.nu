# Reproduce the pinned Stringmol checkout, apply reviewed patches, and build it.

def require-success [result: record, label: string] {
    if $result.exit_code != 0 {
        error make {
            msg: $"($label) failed with exit code ($result.exit_code)\n($result.stderr)"
        }
    }
}

# Clone and build pinned Stringmol. Use --test to run its upstream Catch suite.
def main [--test] {
    let here = ($env.FILE_PWD? | default (pwd))
    let lock = (open ($here | path join "source.lock.json"))
    let vendor_root = ($here | path join "vendor")
    let source = ($vendor_root | path join "stringmol")
    let patches = (glob ($here | path join "patches" "*.patch") | sort)

    mkdir $vendor_root
    if not ($source | path exists) {
        let cloned = (^git clone --no-checkout $lock.repository $source | complete)
        require-success $cloned "Stringmol clone"
        let checked_out = (^git -C $source checkout --detach $lock.commit | complete)
        require-success $checked_out "Stringmol checkout"
    }

    let actual_commit = (^git -C $source rev-parse HEAD | str trim)
    if $actual_commit != $lock.commit {
        error make {
            msg: $"Stringmol checkout is ($actual_commit), expected ($lock.commit)"
        }
    }

    for patch in $patches {
        let forward = (^git -C $source apply --check $patch | complete)
        if $forward.exit_code == 0 {
            let applied = (^git -C $source apply $patch | complete)
            require-success $applied $"apply patch ($patch | path basename)"
        } else {
            let reverse = (^git -C $source apply --reverse --check $patch | complete)
            if $reverse.exit_code != 0 {
                error make {
                    msg: $"patch is neither applicable nor already applied: ($patch)"
                }
            }
        }
    }

    mkdir ($source | path join "debug") ($source | path join "release")
    let built = (do { cd ($source | path join "src"); ^make all } | complete)
    require-success $built "Stringmol release build"

    if $test {
        let tested = (do { cd ($source | path join "tests"); ^bash RunCatchTests.sh } | complete)
        require-success $tested "Stringmol upstream tests"
        if not ($tested.stdout | str contains "All tests passed") {
            error make {msg: "Stringmol test process exited zero without its pass marker"}
        }
        let rebuilt = (do { cd ($source | path join "src"); ^make all } | complete)
        require-success $rebuilt "Stringmol release rebuild after tests"
    }

    let binary = ($source | path join "release" "stringmol")
    if not ($binary | path exists) {
        error make {msg: $"Stringmol binary was not created: ($binary)"}
    }
    print {
        source: $source
        commit: $actual_commit
        patches: ($patches | each {|patch| $patch | path basename})
        binary: $binary
        upstream_tests_run: $test
    }
}
