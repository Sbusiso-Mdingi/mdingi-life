# Protocol: v1.2 Liabilities, windows by sex

Written on 26 October 2026, after v1.1 was run and reported (`RESULTS_v1.1.md`), and before any v1.2 run. A revision made in response to v1.1's results. v1 and v1.1 stay frozen and reported as they are.

Frozen at commit: `1dc85fcda492`

## The one change

Everything in v1.1 (`PROTOCOL_v1.1.md`, frozen at `785cd61cc5ab`) stands except this: **each sex chooses its own fitting window for each model**, the one with the lower design deviance for that sex alone. v1 and v1.1 summed the design deviance over both sexes and imposed one window per model on both.

Men's and women's mortality in South Africa have been driven by different things (the timing and size of the HIV epidemic and of treatment, injury and violence, work and smoking), so there is no reason for one window to suit both. The weights, the anchor, overdispersion, the data, the tests Q1 to Q4 with their pass marks, the prices and the reporting are v1.1's, applied to each sex with its own windows.

## Seen beforehand, and disclosed

v1.1's design deviances are already reported, so the windows this rule picks can be read off them: post-peak for all three models for men; post-peak for LC and CBD and full for RH for women. Women's windows are therefore the same as v1.1's, and only men's RH changes (full to post-peak). On v1.1's anchored design deviances, men's weights will again fall almost entirely on RH. The tests, prices and life expectancies have not been computed.

## Reporting

As v1.1, with v1.1's figures alongside. Seed 20261029. Script `research/v12.py`, output `research/results/v12.json`. v2 to v4 are not rerun until decided.
