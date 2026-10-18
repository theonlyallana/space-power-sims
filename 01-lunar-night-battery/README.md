# 01 — Lunar night battery

Personal project using only public data. Not affiliated with or endorsed by my employer.

The long version, with the derivations, is [EXPLAINED.md](EXPLAINED.md). This page is the map.

## The question

How do you get a battery through two weeks of lunar darkness without destroying it on the way back into the Sun?

## What it models

Two models, kept separate on purpose.

The cell model is a single spherical particle in each electrode, with Butler-Volmer intercalation, Fick diffusion, an Arrhenius temperature factor, and a plating rule: if the negative electrode would have to sit below 0 V vs Li/Li+ to pass the charge current, the excess current deposits as metal. PyBaMM's Doyle-Fuller-Newman model, with the published irreversible plating kinetics, is run on the same cases and drawn on the same axes.

The night model is one thermal mass in a vacuum:

\[
m c \frac{dT}{dt} = P_\text{heater} + P_\text{RHU} - G (T - T_\text{env})
\]

State variables are the lithium concentration in each particle shell, the moles of plated metal, and, for the night, temperature and stored energy.

## Inputs

Every input is in [params.yaml](params.yaml). Each one has a public URL or the word `ASSUMPTION`, and an assumption says what range was swept. The constants \(F\), \(R\), \(k_B\) and \(\sigma\) are in `common/constants.py` (CODATA 2018).

The cell is the LG M50 parameter set of Chen et al. (2020) as extended by O'Kane et al. (2022) and shipped in PyBaMM 25.8.0. It is a commercial 5 Ah cell. It is not Ingenuity's Sony pack and it is not a space cell.

## How to run

From the repository root, with the versions pinned in `pyproject.toml`:

```bash
pip install -e ".[dev]"
export PYBAMM_DISABLE_TELEMETRY=1
python 01-lunar-night-battery/run_all.py
```

That rewrites `figures/`. There is no random seed to set: nothing in this folder draws a random number. To execute the notebook from the same directory:

```bash
jupyter nbconvert --execute --to notebook --inplace 01-lunar-night-battery/notebook.ipynb
```

Set `SPACE_POWER_SIMS_MODE=smoke` first if you want the short path CI uses.

## Results

| Chart | Takeaway | Post |
|---|---|---|
| [A](figures/A_plated_lithium.png) | At 1C our 0 V rule plates about 200 mAh once the charge is at −10 °C or below, and none at 0 °C or warmer. PyBaMM's kinetics plate at every temperature and plate more as it gets colder. | 2 Nov 2026 |
| [B](figures/B_discharge_curves.png) | Our model returns 8% less energy at 0 °C than at 25 °C (17.5 Wh down to 16.1 Wh). PyBaMM returns 11% less. Ingenuity's different pack was estimated 13% less (38.8 / 44.4 Wh). | 9 Nov 2026 |
| [C](figures/C_heater_energy.png) | With no radioisotope heater, heater energy is proportional to the heat-leak conductance. One 1 W unit only covers the leak below about 0.006 W/K. | 16 Nov 2026 |
| [D](figures/D_keep_warm_vs_hibernate.png) | A 3 kg pack at 0.02 W/K spends all 426 Wh by about 124 h and is at the 95 K sink by dawn anyway. Hibernation still has a full state of charge, at the same sink temperature. | 23 Nov 2026 |

## Assumptions and limitations

This is a teaching model, not a design tool and not a safety tool.

- One temperature for the whole pack. No gradients inside a cell, no neighbouring cells.
- Our cell model holds the electrolyte concentration fixed. That is why, at −20 °C and 1C, it still delivers about 4.1 Ah while PyBaMM's Doyle-Fuller-Newman model is down near 1.1 Ah.
- The plating rule is a switch at 0 V. PyBaMM integrates a Butler-Volmer plating reaction, including a tail above 0 V. The two panels of chart A are supposed to disagree in magnitude.
- The PyBaMM cell is an LG M50 parameter set (NMC / graphite), not Ingenuity's six Sony VTC4 cells, and not a cell qualified for space.
- Insulation conductance, pack mass, specific heat and the sunset temperature are assumptions. Specific heat is held constant down to 95 K, which overstates the thermal mass in the cold.
- NASA Glenn's freeze-thaw tests were at 0, 20 and 40% state of charge. Chart D starts full, so it can show the heater budget. It is not a claim that a full cell survives 95 K.

## Validation

Ingenuity's beginning-of-life pack energy, 44.4 Wh at 25 °C and 38.8 Wh at 0 °C, is a 12.6% drop. Our single-particle model drops 8.3% over that step at 1C. PyBaMM's DFN drops 11.4%. The watt-hours themselves are not comparable: different cells, and our cell is about 5 Ah rather than Ingenuity's 2 Ah cells. A warm slow discharge of our model returns within 10% of the 5 Ah nameplate. The night model conserves energy to a few hundred joules, and with no radioisotope heat the heater energy doubles when the conductance doubles.

## Sources

- NASA Glenn, cryogenic hibernation, NTRS 20240004406. 354-hour night, freeze toward ~50 K.
- NASA, Lunar Terrain Vehicle thermal challenges, NTRS 20230002802. Battery often sets the heater; 0 °C or −10 °C; 125-hour extended night; 50 K.
- Williams et al., Icarus 2017, [10.1016/j.icarus.2016.08.012](https://doi.org/10.1016/j.icarus.2016.08.012). Diviner: about 95 K before dawn at the equator.
- NASA Science, radioisotope heater units. About 1 W each.
- NASA battery presentation for Perseverance and Ingenuity. 44.4 Wh, 38.8 Wh, charge window, cell mass.
- Chen et al., J. Electrochem. Soc. 167 (2020) 080534. [10.1149/1945-7111/ab9050](https://doi.org/10.1149/1945-7111/ab9050).
- O'Kane et al., Phys. Chem. Chem. Phys. 24 (2022) 7909. [10.1039/D2CP00417H](https://doi.org/10.1039/D2CP00417H).
- O'Kane et al., J. Electrochem. Soc. 167 (2020) 090540. [10.1149/1945-7111/ab90ac](https://doi.org/10.1149/1945-7111/ab90ac).
- Nyman, Behm and Lindbergh, Electrochimica Acta 53 (2008) 6356. [10.1016/j.electacta.2008.04.023](https://doi.org/10.1016/j.electacta.2008.04.023).
- Sulzer et al., PyBaMM, J. Open Res. Softw. 2021. [10.5334/jors.309](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.309).
- NIST CODATA 2018 for \(F\), \(R\), \(k_B\) and \(\sigma\).

## Background

Approach carried over from my MSc DustPy disc-evolution modelling: take the numbers from the papers, integrate a physical model, and plot the result rather than drawing it. In my day job I work on lithium-ion cells. Nothing from that work is in this folder.

## Licence

MIT for the code. Credit the papers and the NASA material under their own terms. NASA data used here is public.
