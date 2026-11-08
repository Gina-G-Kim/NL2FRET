# INSTALL_NOTES (2026-11-07)

- machine: macOS 15.7.9, x86_64
- ltlfilt (Spot): not found on PATH. `brew install spot` was not run. `brew install --dry-run spot` printed: Homebrew has no support for macOS Intel x86_64 and no longer builds bottles for this configuration (message recommends MacPorts); it also stopped with an error that /usr/local/share/man/man8 is not writable by the user (suggested fix: sudo chown). No sudo or ownership change was done. MacPorts is not installed.
- NuSMV / nuXmv: not found on PATH. `brew search nusmv` and `brew search nuxmv`: no formula or cask found for nusmv; nuxmv gave only an unrelated name (nuxi). No other install method is known to me (unknown).
- z3: python module z3 present (version 5.1.0 as printed by z3.get_version_string()), so the third engine z3b is used.
- consequence per README section 1: NuSMV excluded; Spot not available either, so only z3b runs.
