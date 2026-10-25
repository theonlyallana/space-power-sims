# space-power-sims

[![CI](https://github.com/theonlyallana/space-power-sims/actions/workflows/ci.yml/badge.svg)](https://github.com/theonlyallana/space-power-sims/actions/workflows/ci.yml)

Small, fully explained Python simulations of batteries and power systems for space. One repository, one licence, one set of tests. Each month of the series adds a folder. November is the one that is built.

Personal project using only public data. Not affiliated with or endorsed by my employer.

## The series

Cold, life, safety, mass, trust, then a power system. Each month has four Monday posts: the problem, one mechanism, the trade-off, then a case and a view. The chart for each post is made in this repository.

| Month | Dates | Posts | Folder | Charts |
|---|---|---|---|---|
| November 2026. Cold | 2, 9, 16, 23 Nov | Why a cold battery will not take a charge. Where the energy goes. Heaters, insulation or a radioisotope heater. Keep warm or hibernate. | [`01-lunar-night-battery`](01-lunar-night-battery/) | [A](01-lunar-night-battery/figures/A_plated_lithium.png) plating, [B](01-lunar-night-battery/figures/B_discharge_curves.png) discharge, [C](01-lunar-night-battery/figures/C_heater_energy.png) heater energy, [D](01-lunar-night-battery/figures/D_keep_warm_vs_hibernate.png) keep-warm against hibernate |
| December 2026. Lifetime | 7, 14, 21, 28 Dec | Sixteen cycles a day. The solid-electrolyte interphase. Radiation. What Opportunity teaches. | `02-orbit-cycle-ageing` | Planned. Not in this repository yet. |
| January 2027. Safety | 4, 11, 18, 25 Jan | Thermal runaway. The separator. Propagation. A fire you cannot walk away from. | `03-runaway-propagation` | Planned. Not in this repository yet. |
| February 2027. Mass | 1, 8, 15, 22 Feb | Watt-hours per kilogram. Silicon. Cell format. Solid-state. | `04-cell-to-pack-mass` | Planned. Not in this repository yet. |
| March 2027. Trust | 1, 8, 15, 22 Mar | State of health. Lot testing. The weakest cell. What to borrow from high-volume manufacturing. | `05-cell-lot-screening` | Planned. Not in this repository yet. |
| April 2027. A Moon base | 5, 12, 19, 26 Apr | Rover energy. Sunlight at the south pole. Batteries, fuel cells or fission. One architecture. | `06-lunar-power-sizing` | Planned. Not in this repository yet. |

November's long explanation, including every equation and every input, is [`01-lunar-night-battery/EXPLAINED.md`](01-lunar-night-battery/EXPLAINED.md).

## Layout

```
space-power-sims/
├─ README.md
├─ LICENSE                 MIT
├─ pyproject.toml          pinned PyBaMM, NumPy, SciPy, matplotlib, pandas, PyYAML
├─ common/                 constants, units, the parameter loader, plotting style
├─ 01-lunar-night-battery/
│   ├─ README.md
│   ├─ EXPLAINED.md
│   ├─ params.yaml         every input, with a URL or the word ASSUMPTION
│   ├─ notebook.ipynb
│   └─ figures/            PNGs written by the code
├─ tests/
└─ .github/workflows/ci.yml
```

`pandas` is pinned now because later months need it. November does not import it.

## Run November

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export PYBAMM_DISABLE_TELEMETRY=1
python 01-lunar-night-battery/run_all.py
pytest
```

The figures in `figures/` are whatever that command last wrote. Do not edit the PNGs.

CI runs the tests and a short smoke of the same scripts. It does not redraw the committed figures. PyBaMM 25.8 needs NumPy 1.x, which is why NumPy is pinned below 2.

There is no random number generator in November. The same inputs give the same charts.

## Licence

MIT, for the code. NASA public-domain material is cited where it is used. The LG M50 parameter set is used under the terms of PyBaMM and the papers it cites (Chen et al. 2020, O'Kane et al. 2022).
