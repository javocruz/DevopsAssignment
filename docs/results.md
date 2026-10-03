# C16 results

Real Jev on the 35 fixture markets. `basic` is the question with no headlines. `news` uses the headlines already stored in the fixture. No second pass was needed: both estimate runs reported zero failures. Five paper bets settled: 2 won, 3 lost. Portfolio `total_pnl` is -50.04.

Lower Brier is better.

## basic

- decider: jev
- context_level: basic
- count: 35
- jev_brier: 0.20960571428571426
- market_brier: 0.13601720714285714

jev_calibration:

- 0.0-0.1: count 29, avg_pred 0.033448275862068964, actual_rate 0.20689655172413793
- 0.1-0.2: count 3, avg_pred 0.17666666666666667, actual_rate 0.6666666666666666
- 0.2-0.3: count 1, avg_pred 0.24, actual_rate 0.0
- 0.3-0.4: count 1, avg_pred 0.34, actual_rate 0.0
- 0.6-0.7: count 1, avg_pred 0.68, actual_rate 1.0

market_calibration:

- 0.0-0.1: count 23, avg_pred 0.01847826086956522, actual_rate 0.043478260869565216
- 0.1-0.2: count 3, avg_pred 0.15166666666666664, actual_rate 0.6666666666666666
- 0.2-0.3: count 2, avg_pred 0.255, actual_rate 1.0
- 0.3-0.4: count 3, avg_pred 0.3678333333333333, actual_rate 0.3333333333333333
- 0.6-0.7: count 2, avg_pred 0.635, actual_rate 0.5
- 0.9-1.0: count 2, avg_pred 0.9570000000000001, actual_rate 1.0

## news

- decider: jev
- context_level: news
- count: 35
- jev_brier: 0.20955428571428575
- market_brier: 0.13601720714285714

jev_calibration:

- 0.0-0.1: count 28, avg_pred 0.031071428571428573, actual_rate 0.21428571428571427
- 0.1-0.2: count 3, avg_pred 0.15, actual_rate 0.3333333333333333
- 0.2-0.3: count 1, avg_pred 0.25, actual_rate 1.0
- 0.3-0.4: count 1, avg_pred 0.3, actual_rate 0.0
- 0.4-0.5: count 1, avg_pred 0.48, actual_rate 0.0
- 0.7-0.8: count 1, avg_pred 0.75, actual_rate 1.0

market_calibration:

- 0.0-0.1: count 23, avg_pred 0.01847826086956522, actual_rate 0.043478260869565216
- 0.1-0.2: count 3, avg_pred 0.15166666666666664, actual_rate 0.6666666666666666
- 0.2-0.3: count 2, avg_pred 0.255, actual_rate 1.0
- 0.3-0.4: count 3, avg_pred 0.3678333333333333, actual_rate 0.3333333333333333
- 0.6-0.7: count 2, avg_pred 0.635, actual_rate 0.5
- 0.9-1.0: count 2, avg_pred 0.9570000000000001, actual_rate 1.0

## What this says

On basic, the market's Brier is 0.136 and Jev's is 0.210. Lower is better, so the market was closer than Jev.

News moves Jev from 0.2096 to 0.2096, a hair lower, and the market stays 0.136 because the prices and outcomes are the same 35 markets.

This is 35 already-resolved markets, and the bets are paper only.
