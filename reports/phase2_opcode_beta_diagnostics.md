# Exploratory diagnosis of the Phase 2 opcode-beta failure

These analyses inspect the completed acceptance run after its frozen NO-GO decision. They cannot rescue or replace that decision.

| label | block | unique fraction | singleton-tape fraction | beta excess | p |
|---|---:|---:|---:|---:|---:|
| ordered_full | 2 | 0.767 | 0.687 | 0.211846 | 0.075 |
| ordered_full | 4 | 0.767 | 0.687 | 0.093448 | 0.145 |
| ordered_full | 8 | 0.767 | 0.687 | 0.040686 | 0.135 |
| ordered_full | 16 | 0.767 | 0.687 | 0.014352 | 0.095 |
| ordered_prefix8 | 2 | 0.750 | 0.666 | 0.271980 | 0.025 |
| ordered_prefix8 | 4 | 0.750 | 0.666 | 0.103634 | 0.085 |
| ordered_prefix8 | 8 | 0.750 | 0.666 | 0.059866 | 0.045 |
| ordered_prefix8 | 16 | 0.750 | 0.666 | 0.022169 | 0.035 |
| opcode_histogram | 2 | 0.697 | 0.576 | 0.142626 | 0.110 |
| opcode_histogram | 4 | 0.697 | 0.576 | 0.035266 | 0.305 |
| opcode_histogram | 8 | 0.697 | 0.576 | 0.032641 | 0.145 |
| opcode_histogram | 16 | 0.697 | 0.576 | 0.014826 | 0.100 |
| opcode_presence | 2 | 0.472 | 0.278 | 0.347941 | 0.005 |
| opcode_presence | 4 | 0.472 | 0.278 | 0.114349 | 0.035 |
| opcode_presence | 8 | 0.472 | 0.278 | 0.039998 | 0.105 |
| opcode_presence | 16 | 0.472 | 0.278 | 0.015541 | 0.075 |

## Diagnostic interpretation

The frozen ordered-full opcode label had mean unique fraction 0.767 and mean singleton-tape fraction 0.687.
High singleton prevalence makes categorical beta behave similarly to the previously rejected exact-hash statistic: local byte similarity can be real while exact ordered opcode sequences rarely repeat.

Block-size and coarse-label results are hypothesis-generating only. Any new metric or treatment must be frozen on unseen seeds before confirmatory use.
