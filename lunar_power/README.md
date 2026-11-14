# Lunar power model

Personal project using only public data. Not affiliated with or endorsed by my employer.

The long version, with the derivations, is [EXPLAINED.md](EXPLAINED.md). This page is the map of the package. The repository overview is the [root README](../README.md).

## The question, so far

November: how do you get a battery through two weeks of lunar darkness without destroying it on the way back into the Sun?

December: once it can cycle, what uses it up — the number of orbits, the surface film, radiation, or the depth of each cycle?

## What it models

One model with switches.

The cell model is a single spherical particle in each electrode, with Butler-Volmer intercalation, Fick diffusion, an Arrhenius temperature factor, and a plating rule: if the negative electrode would have to sit below 0 V vs Li/Li+ to pass the charge current, the excess current deposits as metal. PyBaMM's Doyle-Fuller-Newman model is the cross-check on charts A and B.

The night model is one thermal mass in a vacuum:

\[
m c \frac{dT}{dt} = P_\text{heater} + P_\text{RHU} - G (T - T_\text{env})
\]

The ageing model is a diffusion-limited film on the graphite, \(L = \sqrt{L_0^2 + 2kt}\), plus a crack term that rebuilds a fraction of that film each cycle. The fraction scales with the square of the depth of discharge. Radiation is drawn and is not in the rate. When the ageing switch is on, the lost lithium and the film resistance are the cell the cold discharge sees, and the remaining fraction scales the watt-hours the night has to spend. Charts A to D are always the fresh cell.

## Inputs

Every input is in [params.yaml](params.yaml). Each one has a public URL or the word `ASSUMPTION`, and an assumption says what range was swept. The constants \(F\), \(R\), \(k_B\) and \(\sigma\) are in `common/constants.py` (CODATA 2018).

The cell is the LG M50 parameter set of Chen et al. (2020) as extended by O'Kane et al. (2022) and shipped in PyBaMM 25.8.0. It is a commercial 5 Ah cell. It is not a space cell, and it is not the Mars rover's cells.

## How to run

From the repository root, with the versions pinned in `pyproject.toml`:

```bash
pip install -e ".[dev]"
export PYBAMM_DISABLE_TELEMETRY=1
python -m lunar_power.run
```

That rewrites `figures/`. There is no random seed to set. Layers:

```bash
python -m lunar_power.run --layers thermal,electrochemistry
python -m lunar_power.run --layers thermal,electrochemistry,ageing
```

`safety`, `pack`, `variation` and `mission` raise `NotImplementedError`. To execute the notebook from the repository root:

```bash
jupyter nbconvert --execute --to notebook --inplace lunar_power/notebook.ipynb
```

Set `SPACE_POWER_SIMS_MODE=smoke` first if you want the short path CI uses.

To rebuild the PyBaMM film cache that chart F plots:

```bash
python -c "from lunar_power.ageing.pybamm_sei import build_cache; build_cache()"
```

## Results

The figures spell the units out. A 1-hour charge is the current that fills the 5 Ah nameplate in one hour. Heater energy is in watt-hours. The December orbit chart says "55 minute charge" and "35 minute discharge". The film chart says nanometres. The fade chart says the fraction of the 5 Ah nameplate still available.

| Chart | Takeaway | Post |
|---|---|---|
| [A](figures/A_plated_lithium.png) | Our 0 V rule is a step: a 2-hour charge plates about 125 mAh only at −20 °C, and a 1-hour charge plates about 75 mAh at −10 °C but only about 33 mAh at −20 °C because that charge hits 4.2 V sooner. PyBaMM's kinetics rise smoothly and plate at every temperature. | 2 Nov 2026 |
| [B](figures/B_discharge_curves.png) | Our model returns about 10.5% less energy at 0 °C than at 25 °C (17.3 Wh down to 15.5 Wh). PyBaMM returns about 11.4% less. Ingenuity's different pack was estimated 12.6% less (38.8 / 44.4 Wh). | 9 Nov 2026 |
| [C](figures/C_heater_energy.png) | With no radioisotope heater, heater energy is proportional to the heat-leak conductance. One 1 W unit only covers the leak below about 0.006 W/K. | 16 Nov 2026 |
| [D](figures/D_keep_warm_vs_hibernate.png) | A 3 kg pack at 0.02 W/K spends its stored energy during the 354 h night and is at the sink by dawn anyway. Hibernation still has a full state of charge, at the same sink temperature. | 23 Nov 2026 |
| [E](figures/E_sixteen_cycles_a_day.png) | A 90 minute orbit is 16 cycles in one Earth day. NASA's 30,000 cycle goal is 1,875 days on that clock. One cycle a day, and one cycle a lunar day, do not get there on the same axis. | 7 Dec 2026 |
| [F](figures/F_sei_growth.png) | The surface film thickens with the square root of time, so thickness squared is a straight line. At 0 °C it grows more slowly than at 25 °C. The markers are a PyBaMM rest of the same equation. | 14 Dec 2026 |
| [G](figures/G_radiation_concept.png) | Radiation is a box on the diagram, not a curve. A 2004 irradiation study saw only a marginal decline up to 25 Mrad, and that study had no unirradiated control. The diffusivity multipliers under the box are an assumption and are not in the fade. | 21 Dec 2026 |
| [H](figures/H_fade_three_depths.png) | At 16 cycles a day, a deeper cycle consumes the nameplate sooner, and the shaded band is the crack-fraction assumption. One cycle a sol at 60% depth is a different life. The marks are Opportunity's 90 sol plan and sol 5111. | 28 Dec 2026 |

## Assumptions and limitations

This is a teaching model, not a design tool and not a safety tool.

- One temperature for the whole pack. No gradients inside a cell, no neighbouring cells.
- Our cell model holds the electrolyte concentration fixed. That is why, at −20 °C and a 1-hour discharge, it still delivers more charge than PyBaMM's Doyle-Fuller-Newman model.
- The plating rule is a switch at 0 V. PyBaMM integrates a Butler-Volmer plating reaction. The two panels of chart A are supposed to disagree in magnitude.
- The film parameters are the OKane2022 fitting values. They are not a measured space cell.
- The crack fraction, the day-to-night ratio, the cycles per sol, and the age at which ageing is fed back are assumptions. The ranges are in `params.yaml`.
- Radiation is not a rate. Chart G says so on the figure.
- Chart H reaching zero is the inventory count under the drawn crack fraction. It is not a voltage-cutoff prediction, and it is not Opportunity's battery.
- Insulation conductance, pack mass, specific heat and the sunset temperature are assumptions. Specific heat is held constant down to 95 K, which overstates the thermal mass in the cold.
- NASA Glenn's freeze-thaw tests were at low state of charge. Chart D starts full, so it can show the heater budget. It is not a claim that a full cell survives 95 K.

## Validation

Ingenuity's beginning-of-life pack energy, 44.4 Wh at 25 °C and 38.8 Wh at 0 °C, is a 12.6% drop. Our single-particle model drops about 10.5% over that step on a 1-hour discharge. PyBaMM's DFN drops about 11.4%. The watt-hours themselves are not comparable: different cells. A warm slow discharge of our model returns within 10% of the 5 Ah nameplate.

The orbit arithmetic is 16 cycles a day, exactly. The film thickness matches PyBaMM's solvent-diffusion-limited rest to well under 0.1% relative on the cached points. A fresh cell reproduces the November discharge energy and the November plated-lithium anchor. An aged cell returns less of both charge and energy, and its resistance is higher.

## Sources

November's sources are listed in [EXPLAINED.md](EXPLAINED.md). December adds:

- NASA Glenn, LEO battery testing, [NTRS 20050192209](https://ntrs.nasa.gov/citations/20050192209). 90 min, 55 min charge, 35 min discharge, goal of 30,000 cycles.
- NASA, lithium-ion LEO status, [NTRS 20080008855](https://ntrs.nasa.gov/citations/20080008855). 40% depth of discharge, over 12,000 cycles at the time of that paper.
- NASA LEO verification matrix, [NTRS 20050185205](https://ntrs.nasa.gov/citations/20050185205). Includes a 20% depth.
- Ploehn, Ramadass and White, J. Electrochem. Soc. 151 (2004), [10.1149/1.1644601](https://doi.org/10.1149/1.1644601). Square-root film growth.
- O'Kane et al., Phys. Chem. Chem. Phys. 24 (2022), [10.1039/D2CP00417H](https://doi.org/10.1039/D2CP00417H). The diffusion-limited film as coded, and the parameter set.
- Wang et al., npj Computational Materials (2018), [10.1038/s41524-018-0064-0](https://doi.org/10.1038/s41524-018-0064-0). Review of film models.
- Schweidler et al., J. Phys. Chem. C (2018), [10.1021/acs.jpcc.8b01873](https://doi.org/10.1021/acs.jpcc.8b01873). 13.2% graphite volume change to LiC₆.
- Ratnakumar et al., J. Electrochem. Soc. 151 (2004) A652, [10.1149/1.1666128](https://doi.org/10.1149/1.1666128). Radiation context. Not a fade law.
- NASA, Opportunity end of mission, [release](https://www.nasa.gov/news-release/nasas-record-setting-opportunity-rover-mission-on-mars-comes-to-end/) and [NTRS 20200000214](https://ntrs.nasa.gov/citations/20200000214). 90 sols, sol 5111, almost 15 years.
- NASA GISS Mars24, [mean sol](https://www.giss.nasa.gov/tools/mars24/help/notes.html). 24 h 39 min 35.244 s.
- MER battery workshop 2004, [NTRS 20080015793](https://ntrs.nasa.gov/citations/20080015793). Early-mission depth typically 60–70% through sol 54.

## Background

Approach carried over from my MSc DustPy disc-evolution modelling: take the numbers from the papers, integrate a physical model, and plot the result rather than drawing it. In my day job I work on lithium-ion cells. Nothing from that work is in this package.

## Licence

MIT for the code. Credit the papers and the NASA material under their own terms. NASA data used here is public.
