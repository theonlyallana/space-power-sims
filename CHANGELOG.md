# Changelog

This repository is one lunar outpost power model, built a layer at a time. The version tags are Andrew's to apply. This file only records what each layer added, and which post it supports.

## v0.2 — December 2026, ageing

Not tagged in this change. Tag v0.2 when this layer is accepted. v0.1, the November cold model, is tagged on main after that model is merged, not from this branch.

What the layer adds:

- The code is one package, `lunar_power`, with a module per layer. `electrochemistry` and `thermal` are the November model. `ageing` is new. `safety`, `pack`, `variation` and `mission` are switches that raise until those months exist.
- One `params.yaml`. A scenario runner switches layers on and off. With ageing on, lost lithium and film resistance are what the cold discharge and the night's stored energy use. With ageing off, the November charts are unchanged.
- Orbit counting for a 90 minute low-Earth orbit: 55 minutes of charge, 35 minutes of discharge, 40% depth of discharge, 16 cycles in an Earth day.
- A diffusion-limited surface film, square root of time, Arrhenius in temperature, cross-checked against PyBaMM's solvent-diffusion-limited option on cached rests.
- Capacity fade at 20%, 40% and 60% depth of discharge, with a crack-area assumption that is swept. The Opportunity case is the rover's clock set next to the orbit's clock.
- Radiation drawn as a labelled stressor. It is not a term in the fade rate.

Posts: 7 December, sixteen cycles a day. 14 December, the surface film. 21 December, radiation. 28 December, Opportunity and three depths of discharge.

## v0.1 — November 2026, cold

The lunar-night model as first merged: plating on a cold charge, discharge energy at three temperatures, heater energy against the heat leak, keep-warm against hibernation. Charts A to D. Tag this on main after merge. This branch does not create the tag.

Posts: 2 November, plating. 9 November, where the energy goes. 16 November, heaters. 23 November, keep warm or hibernate.
