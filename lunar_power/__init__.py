"""One lunar outpost power model, built a layer at a time.

November is the cold electrochemistry and the lunar-night thermal balance.
December is ageing: orbit cycling, diffusion-limited growth of the surface
film, and depth of discharge. Later months add safety, pack mass, cell-to-cell
variation and the mission energy balance. Those names are switches on the
scenario runner. They are not implemented yet.

Ageing, when it is switched on, changes the lithium inventory and the film
resistance the cold model uses. Switched off, the November numbers are the
November numbers.

Personal project using only public data. Not affiliated with or endorsed by my employer.
"""

from lunar_power.scenario import FUTURE_LAYERS, Layers, parse_layers, run_scenario

__all__ = [
    "FUTURE_LAYERS",
    "Layers",
    "parse_layers",
    "run_scenario",
]
