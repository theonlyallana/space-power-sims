# Lunar night, explained

Personal project using only public data. Not affiliated with or endorsed by my employer.

This note is for someone who can read Python and a conservation law, and who has not met this model before. It derives the November cell and the November night, then the December ageing layer. The short map is [README.md](README.md). Every digit the code uses is in [params.yaml](params.yaml) or in `common/constants.py`.

The code lives in the `lunar_power` package. `electrochemistry` and `thermal` are November. `ageing` is December. One scenario runner switches the layers. Ageing, when it is on, changes the lithium inventory and the film resistance those earlier layers use. When it is off, the November numbers are unchanged. The December chapter is at the end.

The order is fundamentals, then the cell, then the night, then the November results, then ageing.

## The question

A lander at a non-polar site spends about fourteen Earth days in darkness. NASA Glenn's hibernation paper calls that a 354-hour lunar night ([NTRS 20240004406](https://ntrs.nasa.gov/citations/20240004406)). At the south pole a stationary vehicle can see an extended night of 125 hours, and the surface in shadow can fall to 50 K ([NTRS 20230002802](https://ntrs.nasa.gov/citations/20230002802)). Williams, Paige, Greenhagen and Sefton-Nash, using Diviner, put the equatorial surface near 95 K just before dawn ([Icarus, 2017](https://doi.org/10.1016/j.icarus.2016.08.012)).

The battery has to come out of that night able to take a charge. Two different things go wrong if it does not.

One is temporary. A cold cell sags, hits its voltage cut-off early, and gives back less energy. Warm it up and that energy is still there. Ingenuity's pack was estimated at 44.4 Wh at 25 °C and 38.8 Wh at 0 °C, which is 12.6% less ([NASA battery presentation](https://www.nasa.gov/wp-content/uploads/2024/01/battery-system-design-testing-and-operation-for-the-mars-perseverance-rover-and-ingenuity-helicopter.pdf)). That pack is six Sony VTC4 cells. The cell in this folder is not those cells. The comparison is the percentage, not the watt-hours.

The other is permanent. Push charge current into a cold negative electrode and lithium can deposit as metal instead of sliding into the host. That metal is inventory the cell does not get back, and the deposit can grow into a spike that pierces the separator. O'Kane, Campbell, Marzook, Offer and Marinescu describe that short-circuit risk as the main barrier to fast charging at low temperature ([J. Electrochem. Soc. 167, 2020, 090540](https://doi.org/10.1149/1945-7111/ab90ac)).

The practical lever is temperature. The Lunar Terrain Vehicle thermal paper says the battery is usually the component that sets the heater, and it takes a typical minimum of 0 °C or −10 °C. This study holds 0 °C, the more demanding of those two published choices. A radioisotope heater unit puts out about one watt and has no moving parts ([NASA Science](https://science.nasa.gov/planetary-science/programs/radioisotope-power-systems/thermal-radioisotope-heater-units/)).

The four posts are the four charts:

| Chart | Post | Question the chart answers |
|---|---|---|
| A | 2 November 2026 | How much lithium plates as the charge gets colder, at two rates? |
| B | 9 November 2026 | How much energy comes back out at 25, 0 and −20 °C? |
| C | 16 November 2026 | How does heater energy, and the cell mass that stores it, scale with the heat leak? |
| D | 23 November 2026 | Through one 354-hour night, what does keep-warm do that hibernation does not? |

## What a cell is

A cell is the smallest complete electrochemical unit: one negative electrode, one positive electrode, a porous separator and an electrolyte, in one container. Several cells with structure and monitoring make a module. A pack adds the management system, the housing and the thermal hardware. This folder models one cell. The night then treats a pack as one thermal mass, and turns heater watt-hours into a cell mass using a published specific energy. Structure and a management system are not in that mass.

On discharge, lithium ions move from the negative electrode to the positive electrode through the electrolyte. Electrons cannot cross the separator, so they travel through the external circuit and do the work. Charging is the same shuttle run backwards, driven by a supply. The electrodes in this parameter set are intercalation hosts. The ion slots into the host structure. It does not, while the cell is behaving, form a new lump of metal.

The numbers are the LG M50 parameter set of Chen et al. ([J. Electrochem. Soc. 167, 2020, 080534](https://doi.org/10.1149/1945-7111/ab9050)), extended with the degradation parameters of O'Kane et al. ([Phys. Chem. Chem. Phys. 24, 2022, 7909](https://doi.org/10.1039/D2CP00417H)), as shipped in PyBaMM 25.8.0 (Sulzer et al., [Journal of Open Research Software, 2021](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.309)). The negative host is represented by Chen's graphite open-circuit fit. The positive host is NMC. The commercial cell those papers parameterise is a 5 Ah cell with voltage limits 2.5 V and 4.2 V in the published set. It is a commercial cell, not a cell qualified for space, and it is not Ingenuity's Sony pack.

Five functional parts sit behind those numbers, even though the model only resolves some of them.

- The positive electrode is an NMC coating. It sets most of the cell voltage. Its current collector is aluminium foil. The foil is not a separate domain here.
- The negative electrode is the graphite host on copper foil. The foil is not resolved either.
- The separator is a thin porous film, 12 µm in this set. Ions cross it. Electrons do not, which is what keeps the two electrodes from shorting.
- The electrolyte is the liquid the ions travel in. Conductivity is the Nyman, Behm and Lindbergh fit for a LiPF6 carbonate electrolyte ([Electrochimica Acta 53, 2008, 6356](https://doi.org/10.1016/j.electacta.2008.04.023)).
- The current collectors carry electrons out to the tabs. They are lumped into the assumption that the solid phase is a good enough conductor to ignore, except where the cross-check puts that assumption back. The positive electronic conductivity in this parameter set is only 0.18 S/m, so the assumption is the weak one, and section "Why this is not a Doyle–Fuller–Newman model" says so.

A module and a pack are the right language for later months. November's cell curves are one cell. November's night curves are one thermal mass.

## Fundamentals

Each law below is stated, then the assumption that lets us use the form in the code, then where the code calls it. Physical constants are CODATA 2018, written out in `common/constants.py`:

| Symbol | Value | Unit | Role |
|---|---|---|---|
| \(k_B\) | \(1.380649 \times 10^{-23}\) | J/K | Boltzmann's constant. Exact in the 2019 SI. |
| \(R\) | \(8.314462618\) | J/(mol·K) | Gas constant, \(N_A k_B\). Exact. |
| \(F\) | \(96485.3321\) | C/mol | Faraday constant. CODATA 2018, not exact. |
| \(\sigma\) | \(5.670374419 \times 10^{-8}\) | W/(m²·K⁴) | Stefan–Boltzmann constant. |

NIST records the same digits: [F](https://physics.nist.gov/cgi-bin/cuu/Value?f), [R](https://physics.nist.gov/cgi-bin/cuu/Value?r), [k](https://physics.nist.gov/cgi-bin/cuu/Value?k), [σ](https://physics.nist.gov/cgi-bin/cuu/Value?sigma).

### Charge and mass

Current \(I\) is charge per time, in amperes. One lithium ion carries one elementary charge, so the molar rate tied to a current is

\[
\dot n = \frac{I}{F}
\]

with \(\dot n\) in mol/s. Capacity is that statement integrated,

\[
Q = \int I \, dt
\]

and the code stores \(Q\) in ampere-hours by dividing the coulomb integral by 3600. Energy delivered while the current flows is

\[
E = \int V I \, dt
\]

in joules, reported in watt-hours the same way. A C-rate is defined on the nameplate, not on whatever the cell happens to deliver today:

\[
I = (\text{C-rate}) \times Q_\text{nom}
\]

So 1C on this cell is 5 A, and C/2 is 2.5 A. The nameplate \(Q_\text{nom} = 5\) Ah is the parameter set's, from Chen et al.

Sign. Discharge current is positive: lithium leaves the graphite and enters the NMC. Charge current is negative. PyBaMM uses the same sign, which is why the two energy integrals can be compared.

The interfacial current density \(j\) (A/m²) is the cell current spread over the surface of the active material. For spheres the area-to-volume ratio is \(3/R\). The active volume is the active-material fraction \(\varepsilon_s\) times the electrode volume \(L A\), so

\[
S = \frac{3 \varepsilon_s}{R} L A, \qquad j = \frac{I}{S}
\]

\(S\) is `negative_surface_area_m2` and `positive_surface_area_m2`. A smaller particle radius spreads the same cell current over more area, so \(j\) falls and plating becomes harder to trigger. That is a geometric output, not a threshold typed into the scenario.

Lithium in the two hosts plus lithium metal is conserved, because every electron that leaves the positive electrode arrives at the negative electrode and either intercalates or plates:

\[
n_\text{graphite} + n_\text{NMC} + n_\text{plated} = \text{constant}
\]

The test `test_plating.py` checks this to a relative tolerance of \(10^{-3}\) on a −20 °C, 1C charge. The electrolyte concentration is held fixed in our model. That is consistent with salt conservation when the anode current and the cathode current match: each electron corresponds to one Li⁺ released at the positive electrode and one Li⁺ consumed at the negative electrode. It is not consistent with a real electrolyte, which develops gradients. The cross-check keeps those gradients.

Assumption at this step: one electron per lithium ion, no other side reaction, and a uniform reaction over each electrode's surface. The last of those is the single-particle assumption, dropped by the Doyle–Fuller–Newman model.

### Ohm's law

In a conductor the current density is conductivity times the field. Across a slab of thickness \(L\), area \(A\) and conductivity \(\kappa\),

\[
R = \frac{L}{\kappa A}, \qquad V = I R
\]

The electrolyte does not fill the electrode. It fills the pores. The Bruggeman correction used by this parameter set replaces \(\kappa\) with \(\kappa \varepsilon^{b}\) and \(b = 1.5\). That exponent is an estimate of a tortuous pore network, not a constant derived in this repository. Summing the negative electrode, the separator and the positive electrode,

\[
R_\Omega(T) = \frac{1}{A} \sum_i \frac{L_i}{\kappa(T) \, \varepsilon_i^{b}}
\]

which is `Cell.ohmic_resistance`. \(\kappa(T)\) is Nyman's polynomial at the fixed salt concentration, multiplied by the Arrhenius factor below. Nyman et al. did not publish a temperature dependence. PyBaMM's function applies an activation energy of 17000 J/mol and its comment attributes that digit to Ecker et al. (2015). I have not re-read Ecker. The test checks our factor against PyBaMM's function, not against Ecker.

What this resistance leaves out is the solid phase. Electrons have to cross the coating to reach the reaction. The positive coating in this set is a poor electronic conductor (0.18 S/m). Leaving that path out makes our cell too willing at high current and low temperature. The Doyle–Fuller–Newman cross-check puts it back.

### Faraday, used as a boundary condition

Fick's law moves lithium inside a particle. It does not, by itself, know about the circuit. Faraday's law is the boundary condition at the particle surface: the molar flux out of the particle equals the intercalation current density divided by \(F\),

\[
N_r(R) = \frac{j_\text{intercalation}}{F}
\]

A negative (charging) current on the graphite pushes lithium in. Plating current is not part of this flux. Plated metal sits on the surface and is integrated separately,

\[
\frac{d n_\text{plated}}{dt} = -\frac{j_\text{plated} S}{F}
\]

with \(j_\text{plated}\) negative while metal is depositing, so \(n_\text{plated}\) grows.

### Nernst, and why the open-circuit potential is a fit

For a reaction \(\mathrm{Li}^+ + e^- + \text{site} \rightleftharpoons \mathrm{Li\text{-}site}\), the equilibrium potential measured against a lithium-metal reference is the Nernst equation

\[
U = U^\circ - \frac{RT}{F} \ln \frac{a_\text{Li-site}}{a_{\mathrm{Li}^+} \, a_\text{site}}
\]

If the host were an ideal solution, the activities would be the stoichiometry \(\theta = c_s / c_{s,\max}\) and \(1-\theta\), and \(U(\theta)\) would be a logarithm. Graphite is staged. NMC is not an ideal solution either. The measured equilibrium potential is a curve with plateaus and steep ends, not that logarithm.

Chen et al. fit the half-cell curves. We use those fits, copied from PyBaMM's `Chen2020.py` so the coefficients are visible in `params.yaml`. Stoichiometry is clipped to \((10^{-6},\, 1-10^{-6})\) only so the fit is not evaluated on a singular argument. The graphite fit is

\[
\begin{align*}
U_-(\theta) &= a_e e^{b_e \theta} + c_0 \\
&\quad + a_1 \tanh[b_1(\theta - \theta_1)] \\
&\quad + a_2 \tanh[b_2(\theta - \theta_2)] \\
&\quad + a_3 \tanh[b_3(\theta - \theta_3)]
\end{align*}
\]

and the NMC fit is a straight line plus three tanh terms. The coefficients are the `ocp_negative_coefficients` and `ocp_positive_coefficients` entries. O'Kane's parameter file replaces the graphite curve with a CSV interpolant of the same electrode. Our model keeps the closed form. PyBaMM's cross-check uses the interpolant. That difference is part of the gap between the solid and dashed curves, and it is small next to the modelling gap.

Assumption: the open-circuit potential depends on surface stoichiometry and not, separately, on temperature. A real entropy term would add a few millivolts. It is not in this parameter set, so it is not in the model.

### Butler–Volmer kinetics

The driving force for the intercalation reaction is the surface overpotential

\[
\eta = \varphi_s - \varphi_e - U(\theta)
\]

where \(\varphi_s - \varphi_e\) is the potential of the solid relative to the electrolyte next to it, and \(U\) is the open-circuit potential above. Both potentials are in volts, measured in the lithium-metal scale, so \(\varphi = 0\) means the surface is at the same potential as lithium metal.

The current density that overpotential produces is the Butler–Volmer equation

\[
j = j_0 \left[ \exp\left(\frac{\alpha F \eta}{RT}\right) - \exp\left(-\frac{(1-\alpha) F \eta}{RT}\right) \right]
\]

Positive \(j\) is anodic: lithium leaving the particle. The transfer coefficient \(\alpha\) is 0.5 for intercalation in this parameter set, so the two branches are symmetric. The exchange current density follows the standard one-electron concentration dependence used by Chen et al.,

\[
j_0 = m_\text{ref} \exp\left[\frac{E_{a,k}}{R}\left(\frac{1}{T_\text{ref}} - \frac{1}{T}\right)\right] \sqrt{c_e \, c_s \, (c_{s,\max} - c_s)}
\]

\(j_0\) goes to zero when the surface is empty or full. Near the end of a charge the graphite surface fills up, the square root collapses, and the overpotential has to grow to keep passing current. That is an output of the kinetics.

The code solves Butler–Volmer for \(\varphi_s\) at a known \(j\), by Newton. The exponential is clipped at \(\pm 40\) so a wild step cannot overflow, and the Newton step is capped at 0.25 V. Those are numerical guards, not electrochemistry. The derivative used by Newton is analytic:

\[
\frac{\partial j}{\partial \varphi_s} = j_0 \frac{F}{RT} \left[ \alpha e^{\alpha F \eta / RT} + (1-\alpha) e^{-(1-\alpha) F \eta / RT} \right]
\]

which is positive, so there is one root.

A linearisation is useful for reading chart B and wrong for computing it. For small \(\eta\) and \(\alpha = 1/2\),

\[
j \approx j_0 \frac{F}{RT} \eta
\]

so the charge-transfer resistance of a patch of area \(S\) is \(RT / (j_0 F S)\). Two temperature effects sit in that expression and they point opposite ways. The explicit \(T\) in the numerator would make the same \(j_0\) slightly easier to drive when the cell is colder. The exchange current \(j_0\) itself falls exponentially, and that fall wins. For the graphite kinetics, \(E_{a,k} = 35000\) J/mol, the Arrhenius factor from 25 °C to −20 °C is

\[
\exp\left[\frac{35000}{R}\left(\frac{1}{298.15} - \frac{1}{253.15}\right)\right] \approx 0.081
\]

about a twelvefold drop. The positive electrode's kinetic activation energy is 17800 J/mol, so its exchange current falls less. The model uses the full Butler–Volmer equation, not the linearisation.

### Fick's law in a spherical particle

Lithium inside a particle moves by diffusion. In spherical symmetry, with diffusivity \(D\) taken independent of concentration (which is what this parameter set does),

\[
\frac{\partial c_s}{\partial t} = \frac{1}{r^2} \frac{\partial}{\partial r} \left( r^2 D \frac{\partial c_s}{\partial r} \right)
\]

No flux at the centre, because there is no preferred direction. Faraday's boundary condition at \(r = R\), as above.

The code does not discretise that partial differential equation in differential form. It uses the integral form on shells, which is the same statement. Shell \(i\) has volume \(V_i\) and shares faces of area \(A_i\) with its neighbours. The molar flux through a face, from Fick, is

\[
N = -D \frac{c_{i+1} - c_i}{r_{i+1} - r_i}
\]

and the shell gains whatever arrives on the inner face and loses whatever leaves on the outer face,

\[
V_i \frac{d c_i}{dt} = A_i N_\text{in} - A_{i+1} N_\text{out}
\]

The outer face of the outer shell is the reaction, \(N = j_\text{intercalation}/F\), not a ghost concentration outside the particle. Thirty-two shells are used, packed toward the surface. Equal shells with only eight bins made the outer bin thick. The flux between bin centres then required an exaggerated concentration jump, the open-circuit potential fell through 0 V, and a C/2 charge plated about 9.5 mAh at 0 °C and about 1.5 mAh at −10 °C. That ordering reversed the temperatures and disappeared once the surface was resolved: it was the mesh, not the 0 V rule. The edges are \(R(1-(1-u)^{2})\) with \(u\) uniform in the bin index. Grading 2 with 32 shells matches grading 2 with 64 shells to about one percent on the plated amounts. Equal shells were still drifting at 128 bins. A warm C/5 discharge on this mesh returns within 10% of the 5 Ah nameplate.

Outer shells hold more material. State of charge and the inventory use the volume-weighted average, not the mean of the eight numbers.

Assumption: one particle radius per electrode, the published \(R\), standing in for a distribution of radii. Fickian diffusion, constant \(D\) apart from temperature. No stress, no cracking.

### Arrhenius

A rate that has to climb an energy barrier \(E_a\) scales as

\[
k(T) = k(T_\text{ref}) \exp\left[\frac{E_a}{R}\left(\frac{1}{T_\text{ref}} - \frac{1}{T}\right)\right]
\]

\(T_\text{ref} = 298.15\) K. Below that temperature the exponent is negative and the rate falls. The same function multiplies the two diffusivities, the two exchange-current prefactors, and the electrolyte conductivity. Diffusivity activation energies in the PyBaMM functions are 30300 J/mol (graphite) and 25000 J/mol (NMC). The graphite comment says Chen et al. did not report it and points at Ecker et al. (2015). The NMC comment points at O'Kane et al. after Cabañero et al. (2018). I have not re-read those tables. The values are whatever PyBaMM 25.8.0 evaluates, and the test locks our factor to that evaluation at 253.15 K and 298.15 K, to a relative tolerance of \(10^{-6}\).

This is the cold mechanism before any particular mission is introduced. Diffusion slows, so the surface depletes or fills while the middle of the particle still holds lithium. Charge transfer slows, so the overpotential grows. Electrolyte conductivity falls, so the ohmic drop grows. The voltage cut-off arrives early. Warm the cell and the rates recover, and so does the energy, provided the lithium is still in the host.

### Joule heating, and why the discharge curves stay isothermal

Resistive dissipation in a current \(I\) through a resistance \(R\) is

\[
\dot Q_\text{Joule} = I^2 R
\]

It rises with the square of current. A cold cell has a larger \(R\), from the Arrhenius conductivity and from the kinetic resistance above, so the same current heats it more. A higher C-rate heats it much more. That heat is real, and it is one reason a pack under load is not at the ambient temperature written on the test plan.

Chart B does not include it. The three curves are isothermal, at 25, 0 and −20 °C, in our model and in the PyBaMM cross-check (`"thermal": "isothermal"`). The chart is a comparison at a stated temperature, matching the way NASA quotes Ingenuity's two energies. Coupling \(I^2 R\) back into \(T\) would warm the cold curve as it discharged and hide the comparison.

### Lithium plating

Cell-technology background. If the charge current is pushed hard, or the cell is cold, lithium deposits as metal on the negative surface instead of intercalating. Three consequences follow. The metal is lithium that no longer shuttles, so the capacity loss stays when the cell is warmed. The deposit can grow as a filament and pierce the separator, which is an internal short. O'Kane et al. (2020) identify that short as the reason fast charge at low temperature is a chemistry problem rather than a charger setting. The reaction can also make gas. This model does not track gas or the mechanics of a puncture. It tracks the moles of metal.

The current and temperature where plating starts are outputs of the anode material, the electrolyte, the particle size and the electrode thickness. They are not a knob. NASA's limits make that concrete, because the two batteries in the same presentation do not share a window. Ingenuity's low-rate charge is allowed from −5 °C to 25 °C on the cell surface. Perseverance's different EaglePicher cells are allowed to charge and discharge from −20 °C to +30 °C. Neither window is coded as a stop. The model will charge at whatever temperature `params.yaml` lists. The chemistry then decides whether the negative potential stays above 0 V.

Our criterion is the simplest statement of that output. Solve the intercalation problem alone. If the potential required to pass the whole current is still at or above 0 V versus Li/Li⁺, no metal is deposited. If intercalation alone would need a potential below 0 V, pin the surface at 0 V, let intercalation take whatever current Butler–Volmer supplies there, and send the leftover current into plating, provided that leftover is a reduction. In symbols, with \(j_\text{app}\) the applied interfacial current (negative while charging):

\[
\begin{align*}
\varphi &\ge 0 &&\Rightarrow& j_\text{intercalation} &= j_\text{app}, & j_\text{plated} &= 0 \\
\varphi &< 0 &&\Rightarrow& \varphi &= 0, & j_\text{plated} &= j_\text{app} - j(0)
\end{align*}
\]

and if \(j_\text{app} - j(0)\) comes out positive, the surface at 0 V is already happy to give lithium up, which is not plating, and the leftover is discarded. This is a switch. It has no plating rate constant. The published \(k_\text{pl} = 10^{-9}\) m/s is recorded in `params.yaml` because the cross-check uses it. Our switch does not.

PyBaMM's irreversible model is a Butler–Volmer plating reaction, read from the library's plating submodel in version 25.8.0. With the SEI film overpotential at zero (irreversible plating does not, by itself, turn SEI growth on),

\[
j = -j_{0,\text{pl}} \exp\left(\frac{\alpha_\text{pl} F \eta_\text{pl}}{RT}\right), \qquad \eta_\text{pl} = -(\varphi_s - \varphi_e), \qquad j_{0,\text{pl}} = F k_\text{pl} c_e
\]

\(\alpha_\text{pl} = 0.65\). Because this is irreversible, the code path has no stripping branch, and every plated mole is counted as dead lithium. The exponential is small when the anode sits above 0 V, but it is not zero. That tail is why the cross-check plates tens of milliampere-hours even at 25 °C, where our switch plates none. The two panels of chart A are supposed to disagree in magnitude. Agreeing would mean one of them had been tuned to the other.

A further difference: our switch plates only the current that intercalation cannot accept, and the cell keeps charging until 4.2 V. PyBaMM distributes the reaction through the electrode thickness, grows ohmic and concentration drops the single-particle model ignores, and often hits 4.2 V having accepted less charge. Absolute plated milliampere-hours are therefore not a pure "colder means more metal" dial. A colder cell also accepts less charge before the cut-off. The honest reading is the pair of numbers in each row of the results section: plated metal, and how much charge was passed.

The shape of chart A is the criterion, and the two panels are supposed to disagree.

Our switch plates nothing until intercalation alone would need a potential below 0 V. The moment it crosses, the leftover current all becomes metal. Plotted against temperature, that is a step: zero, then a jump. There is no constant-voltage tail after 4.2 V. The charge is constant-current and it stops at the voltage limit, so the plated amount is whatever accumulated before that instant. PyBaMM's irreversible model is the exponential above, evaluated all the way through the electrode thickness. The rate is small above 0 V and never quite zero, and different depths of the electrode cross 0 V at different times. Plotted against temperature, that is a smooth rise. Matching the two curves would mean one of them had been tuned to the other.

On the resolved mesh the C/2 charge plates only at −20 °C, about 125 mAh, after 1.36 Ah of a 2.13 Ah charge. At 0 °C the anode bottoms at about 3 mV and plates nothing. At −10 °C it bottoms at about 9 mV. The warmer of those two gets closer to 0 V because it accepts more charge (3.32 Ah against 2.85 Ah) and the graphite surface fills further. It does not cross. The few-milliampere-hour dip that used to sit on this curve, about 9.5 mAh at 0 °C and about 1.5 mAh at −10 °C, was the eight-shell mesh described above. It is not in the figure.

At 1C the switch is off at 0 °C and above (the anode bottoms at about 14 mV, 20 mV and 3 mV at 25, 10 and 0 °C). It trips at −10 °C after 1.17 Ah and finishes with about 75 mAh, having passed 1.59 Ah. At −20 °C it trips earlier, after 0.72 Ah, but the cell is already at 4.2 V by 0.92 Ah, so the total is only about 33 mAh. Colder started sooner and still deposited less, because the voltage limit arrived first. That is the 0 V rule plus a cutoff, not a grid artefact: 32 shells and 64 shells agree to about a milliampere-hour. The onset, not the final total, is what moves earlier as the cell gets colder.

PyBaMM's irreversible model, from the same empty start, plates more as the temperature falls at both rates. At C/2 the plated amounts from 25 °C down to −20 °C are about 67, 77, 99, 121 and 129 mAh. At 1C they are about 37, 49, 53, 60 and 78 mAh. The 1C charge at −20 °C only passes about 0.79 Ah before 4.2 V, which is why its plated total is smaller than the C/2 charge at the same temperature even though a larger fraction of the current is going into metal. PyBaMM does not show our step, and our step does not show PyBaMM's tail.

Waldmann et al. (2014) is often cited for which ageing mechanism dominates below room temperature. The paper resolves, and I have not read the numbers, so this note does not quote a temperature threshold from it.

### From these laws to the two cell models

The Doyle–Fuller–Newman model is what you get if you refuse the uniform-reaction assumption. Along the electrode thickness \(x\) you keep an electrolyte concentration \(c_e(x,t)\) and potential \(\varphi_e(x,t)\), a solid potential \(\varphi_s(x,t)\), and a particle \(c_s(r,t; x)\) at each \(x\). Charge conservation says the divergence of the current in each phase equals the reaction. Ohm's law, with the Bruggeman correction, closes the potentials. Nernst–Planck transport moves the salt. Butler–Volmer and Fick are unchanged; they just happen at every \(x\) rather than once. Plating, if it is on, is an extra reaction at the negative particles. PyBaMM's DFN discretises that system and the IDAKLU solver integrates it. That is the cross-check.

The single-particle model keeps Butler–Volmer, Fick, Arrhenius, Faraday and a lumped Ohm drop, and drops everything that needs an \(x\) coordinate:

- one particle per electrode, so one surface concentration and one overpotential;
- electrolyte concentration fixed at 1000 mol/m³, the published initial value;
- no solid-phase ohmic drop;
- temperature uniform and imposed.

Those are the reasons a full DFN was not reimplemented here. The electrolyte equation is a conservation law in \(x\) coupled to a particle at each mesh point, and the potentials are algebraic constraints. Doing it properly means a DAE solver and Jacobians. PyBaMM already is that solver, documented by Sulzer et al. A second implementation would mostly be a transcription, and its bugs would be ours. The single-particle model is short enough that the file is the derivation. The figure shows where the shortcut stops being cheap: at −20 °C and 1C, our model still delivers about 3.21 Ah (10.2 Wh), and the DFN is down near 1.07 Ah (3.51 Wh). The missing electrolyte gradient and the missing solid resistance are doing that, not a plotting error. Tightening the DFN solver from the library default to a relative tolerance of \(10^{-8}\) left that cutoff where it was. What did move the picture was the capacity axis: spacing solver steps evenly in ampere-hours drew a flat stretch near 3.3 V, because once the salt has emptied the solver takes many tiny steps at nearly the same voltage. The axis on chart B is the integral of current. On that axis the −20 °C DFN voltage falls smoothly and is finished by about 1.07 Ah.

### Energy balance for the night

The control volume is the cells and the heater, inside the insulation. One temperature \(T\) describes it. That is the lumped-capacitance assumption: the interior is well mixed compared with the drop across the insulation. No phase change, no mass crossing the boundary. Specific heat \(c\) is constant. The first law then says the internal energy rises when heat is added and falls when heat leaks:

\[
m c \frac{dT}{dt} = P_\text{heater} + P_\text{RHU} - G (T - T_\text{env})
\]

\(m\) is in kg, \(c\) in J/(kg·K), \(T\) in K, powers in W, and \(G\) in W/K. \(T_\text{env}\) is the sink: 95 K for the equatorial night, 50 K for the shadowed 125-hour case.

\(P_\text{heater}\) is electrical power drawn from the battery and dissipated as heat inside the control volume. It is not added again as \(I^2 R\). The electrical energy has already left the stored-energy account and re-entered as heat. Adding a Joule term on top would count the same watts twice. Internal dissipation in the cells, on the way to a heater, is a split of that same energy and is neglected. Self-discharge is neglected. In hibernation the battery is disconnected, which is NASA Glenn's description, so \(P_\text{heater} = 0\) and the state of charge is constant.

At steady state the derivative is zero and the heater holds the setpoint \(T_\text{set}\):

\[
P_\text{balance} = \max\left(0,\; G (T_\text{set} - T_\text{env}) - P_\text{RHU}\right)
\]

When \(P_\text{RHU} = 0\), halving \(G\) halves \(P_\text{balance}\). That is the sentence chart C is for. Chart C multiplies by the length of the night and ignores the free cooldown from the sunset temperature. Chart D integrates the transient, including that cooldown.

Integrate the balance over a night and the testable statement is

\[
m c \left(T_\text{end} - T_\text{start}\right) = \int \left(P_\text{heater} + P_\text{RHU} - G (T - T_\text{env})\right) dt
\]

`conservation_residual_J` is the left-hand side minus the right-hand side. The test requires the absolute residual under 500 J on both strategies. The integrator samples are joined carefully: the timestep where the heater switches is stored twice, once at zero power and once at balance power, so the trapezium rule does not average across the switch and drop half a step of heater energy.

An ideal thermostat inside a single right-hand side chatters, because the adaptive solver tries to resolve the discontinuity. The night is integrated as three smooth pieces instead. Cool with the heater off until \(T\) hits the setpoint. Hold \(T\) fixed and run the stored energy down at \(P_\text{balance}\). Cool again towards the sink once the energy is gone or the Sun is back. Hibernate is only the cooling piece.

Stored energy sets the state of charge. The 0 °C Ingenuity pack energy divided by the mass of its six cells is

\[
\frac{38.8\ \text{Wh}}{6 \times 45.5\ \text{g}} = 142.12\ \text{Wh/kg}
\]

NASA does not quote that specific energy. The division is ours, and it is cell-level: no structure, no management system. The 0 °C figure is used because the keep-warm setpoint is 0 °C. The 25 °C energy would give a higher specific energy and a lighter mass axis. Chart D's 3 kg pack at full state of charge therefore stores \(3 \times 142.12 = 426.37\) Wh. That state of charge is an assumption. NASA Glenn's freeze-thaw dwells were at 0, 20 and 40% state of charge. Starting full shows the heater budget. It is not the condition they demonstrated.

### Stefan–Boltzmann, when the leak is radiation

A grey surface radiating to a sink exchanges

\[
\dot Q = \varepsilon \sigma A \left(T^4 - T_\text{sink}^4\right)
\]

Factor the difference of fourth powers:

\[
T^4 - T_\text{sink}^4 = (T - T_\text{sink})(T + T_\text{sink})(T^2 + T_\text{sink}^2)
\]

so the same exchange is \(G_\text{rad}(T - T_\text{sink})\) with

\[
G_\text{rad} = \varepsilon \sigma A (T^2 + T_\text{sink}^2)(T + T_\text{sink})
\]

\(G_\text{rad}\) depends on both temperatures. It is not a property of a blanket. The sweep on chart C treats \(G\) as constant, which is the right picture for conduction through insulation and only a snapshot for radiation. Evaluated at the 0 °C setpoint against a 95 K sink, \(\sigma (T^2 + T_\text{sink}^2)(T + T_\text{sink}) \approx 1.746\) W/(m²·K). The example \(\varepsilon = 0.2\) and \(A = 0.1\) m², both assumptions, give \(G \approx 0.0349\) W/K, which is the vertical line on the left-hand panel. It is not a measured multi-layer blanket.

One consequence for the two sinks: at 273 K, \(T^4\) is so much larger than either \(95^4\) or \(50^4\) that a pure radiative leak barely notices which cold sink it faces. The 125-hour case is cheaper than the 354-hour case at the same \(G\) because it is shorter, not because 50 K is "only a bit colder" in the conduction model. The conduction model does feel the sink, through \(T - T_\text{env}\). The radiation remark is there so the example line is not over-read.

The threshold where one 1 W unit covers the equatorial hold is \(G (273.15 - 95) = 1\), so \(G \approx 0.0056\) W/K. Below that, on the long night, the radioisotope unit is enough and the battery heater energy on chart C is zero.

## How the code runs

`python -m lunar_power.run` is the entry point. `lunar_power/run.py` is that module.

1. `run.main` parses `--smoke`, `--out` and `--layers`. The default layers are `thermal,electrochemistry,ageing`. Smoke mode writes to a temporary directory and does not touch `figures/`. It still draws the December charts, because those are closed-form, and it shortens the November electrochemical cases and skips PyBaMM on charts A and B.
2. `common.params.load_params` reads `lunar_power/params.yaml`. Each entry needs `value`, `unit`, `source` and `note`. The source is an `https://` URL or the exact word `ASSUMPTION`. An assumption's note must contain "swept". `require` fetches one entry by the name the code uses, and fails with that name if it is missing.
3. `lunar_power.charts.november.generate` builds a fresh cell, with the ageing feed left at zero, and draws A, B, C and D. `lunar_power.charts.december.generate` draws E, F, G and H. Outside smoke mode, `run_scenario` then writes the coupled block into `figures/summary.json`.

`cell_from_params` copies the book into a frozen `Cell`. There is no hidden default. Electrode area is height times width, \(0.065 \times 1.58 = 0.1027\) m².

Chart A calls `discharged_state`, which is a C/5 discharge at 25 °C from the published full concentrations down to 2.5 V. The particle profiles are replaced by their volume averages. That pair, about 1082 mol/m³ in the graphite (stoichiometry about 0.033) and about 53623 mol/m³ in the NMC (stoichiometry about 0.85), is the rested empty start for every plating charge. Each charge is `simulate(..., direction="charge")` at one temperature and one C-rate, stopped at 4.2 V. Smoke mode keeps only the first and last temperatures and only the 1C rate, and skips PyBaMM.

`simulate` builds 32 surface-packed shells per electrode, then asks SciPy's `solve_ivp` (BDF, relative tolerance \(10^{-4}\), absolute tolerance \(10^{-8}\), maximum step 5 s, dense output on) to integrate the shell concentrations and the plated moles. A stored step that moves the voltage by more than 40 mV is filled in from that dense output, so a cut-off is not drawn as one straight chord. At every evaluation:

- `split` turns the cell current into an interfacial current on each electrode.
- `_anode_split` does the 0 V test described above. The cathode has no plating branch; its interfacial current is the whole cell current.
- `_particle_rates` applies Fick.
- Voltage is \(\varphi_+ - \varphi_- - I R_\Omega\), with \(I\) the discharge-positive current, so a positive discharge current lowers the terminal voltage.
- Events stop the run when voltage crosses 2.5 V downward or 4.2 V downward in the event function's sign. For the first \(10^{-8}\) s the event functions return a harmless positive value, because a rested empty cell sits near 2.5 V and would otherwise abort a charge at the first instant.

Plated ampere-hours are \(n_\text{plated} F / 3600\). Throughput is \(|I| t / 3600\). Energy is the trapezium integral of \(V I\), divided by 3600.

Chart B discharges from the published full concentrations (29866 and 17038 mol/m³) at 1C, plating inactive because the anode potential stays positive. PyBaMM's discharge turns plating off explicitly, so chart B is about resistance. Smoke mode keeps 25 °C and 0 °C only, and skips PyBaMM.

Charts C and D do not touch the cell model. `steady_heater_energy_Wh` is \(P_\text{balance}\) times duration. `radiative_conductance_W_per_K` is the factored Stefan–Boltzmann expression. `simulate_night` is the three-piece integrator. `ingenuity_specific_energy_Wh_per_kg` is the division above, and `battery_mass_kg` divides heater watt-hours by that specific energy.

`pybamm_check` sets `PYBAMM_DISABLE_TELEMETRY` before importing the library. The first import otherwise asks a question on stdin and a test run hangs. `_solve` builds an isothermal DFN, loads `ParameterValues("OKane2022")`, sets the ambient temperature and the two initial concentrations, and integrates one experimental step with `IDAKLUSolver`. Plating runs use `"irreversible"` and the variable `Loss of capacity to negative lithium plating [A.h]`. Discharge runs use `"none"`.

`common.plotting.apply_style` sets DejaVu Sans, drops the top and right spines, and uses a fixed colour set (Okabe–Ito) so a warm curve and a cold curve survive greyscale. `save_figure` writes a PNG at 140 dpi, the whole canvas, with no tight bounding box. Constrained layout is given the rectangle `(0, 0.055, 1, 0.945)`, which is left, bottom, width and height: a height of 1 with the bottom raised would shove the titles off the top of the canvas. The disclaimer is a `figure.text` in the strip under that rectangle. Ticks the locator places outside the view are dropped, and the save raises if any text artist's window extent falls outside the figure. Every figure carries the disclaimer, because the image is what gets posted.

`common.units` holds the 3600 J/Wh conversion and a `trapz` that calls `numpy.trapezoid` if it exists and `numpy.trapz` otherwise. NumPy 1.26, which PyBaMM 25.8 requires, only has `trapz`.

`lunar_power/__init__.py` exports the scenario runner. It does not add physics. The old `model.py` map is this package: `electrochemistry/cell.py`, `electrochemistry/spm.py`, `electrochemistry/pybamm_check.py`, `thermal/night.py`, `charts/november.py`.

The notebook `notebook.ipynb` calls the same entry point. If `SPACE_POWER_SIMS_MODE=smoke` it writes to a temporary directory. Otherwise it rewrites `figures/`.

## Parameters

Constants are in the table at the top of "Fundamentals". Everything else is one entry in `params.yaml`. Grouped by why it is there:

**Geometry and inventory, Chen et al. / O'Kane et al., via PyBaMM 25.8.0.** Electrode height 0.065 m, width 1.58 m. Thicknesses 85.2 µm (negative), 12 µm (separator), 75.6 µm (positive). Particle radii 5.86 µm and 5.22 µm. Porosities 0.25, 0.47, 0.335. Active fractions 0.75 and 0.665. In this set the active fraction plus the porosity is 1, so binder is not given its own volume. Bruggeman exponent 1.5. Maximum concentrations 33133 and 63104 mol/m³. Initial concentrations 29866 and 17038 mol/m³, a nearly full cell. Electrolyte 1000 mol/m³. Nameplate 5 Ah. Cut-offs 2.5 V and 4.2 V. Intercalation transfer coefficient 0.5. Reference temperature 298.15 K. These are used because they are a complete public parameter set with a plating extension, not because an LG M50 is a space cell.

**Kinetics.** Graphite diffusivity \(3.3 \times 10^{-14}\) m²/s with activation energy 30300 J/mol. NMC diffusivity \(4 \times 10^{-15}\) m²/s with 25000 J/mol. Exchange-current prefactors \(6.48 \times 10^{-7}\) and \(3.42 \times 10^{-6}\), in A/m² times (m³/mol)^(1.5), with activation energies 35000 and 17800 J/mol. The activation energies are taken from PyBaMM's function source, which attributes them to Ecker, Cabañero and Chen. See the gap list. They are used so our Arrhenius factor is the same function PyBaMM evaluates.

**Plating constants, used by PyBaMM only.** \(k_\text{pl} = 10^{-9}\) m/s, \(\alpha_\text{pl} = 0.65\), from the O'Kane 2022 set. PyBaMM's own documentation notes that these degradation parameters are fitting values and not a claim to represent a particular cell.

**Electrolyte conductivity, Nyman's polynomial.** \(\kappa = 0.1297 c^3 - 2.51 c^{1.5} + 3.329 c\) with \(c = c_e/1000\), then the Arrhenius factor with 17000 J/mol. Same caveat as the other activation energies.

**Open-circuit coefficients.** Listed under `ocp_negative_coefficients` and `ocp_positive_coefficients`. They are Chen's fit, not a Nernst derivation. The formula is in the Nernst section.

**Numerical assumptions.** 32 shells, graded toward the surface with power 2. Relative tolerance \(10^{-4}\). Absolute tolerance \(10^{-8}\). Swept as discretisation choices. Eight equal shells false-plated a few milliampere-hours around 0 °C; the graded mesh does not, and 32 shells match 64. Tighter integrator tolerances did not move the plotted curves enough to see.

**Scenario assumptions and cited temperatures.** Plating temperatures −20, −10, 0, 10, 25 °C, swept to cover Ingenuity's charge window and Perseverance's lower limit. Plating rates 0.5C and 1C, swept because NASA does not publish Ingenuity's charge current. Discharge temperatures 25, 0 and −20 °C, cited: the first two are Ingenuity's energy temperatures, and −20 °C is Perseverance's lower limit. Discharge rate 1C, swept against 0.2C; at 0.2C the sag from 25 °C to 0 °C is only a few percent and the chart has nothing to show. Precondition C/5, a slow discharge so the empty state is nearly rested.

**Night.** 354 h and 125 h, sinks 95 K and 50 K, setpoint 0 °C, radioisotope power 1 W, all cited above. Conductance swept from 0.005 to 0.2 W/K. Chart D uses 0.02 W/K inside that sweep, pack mass 3 kg inside a 1–10 kg choice, specific heat 900 J/(kg·K) inside 700–1200, sunset temperature 20 °C inside 0–30 °C, and state of charge 1. Specific heat is held constant down to 95 K, which overstates the thermal mass once the pack is cryogenic, because real solids lose heat capacity as they cool. Chen's electrode-material value of 700 J/(kg·K) is a material property of the coating, not this whole-cell number, and it is not what is used. Example emissivity 0.2 and area 0.1 m² are illustrations chosen so the radiative marker lands inside the sweep.

**Comparison only.** Ingenuity 44.4 Wh, 38.8 Wh, 45.5 g, six cells, charge window −5 °C to 25 °C. Perseverance −20 °C to +30 °C. None of these replace the LG M50 parameters.

## How to run

From the repository root, with the versions pinned in `pyproject.toml`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
export PYBAMM_DISABLE_TELEMETRY=1
python -m lunar_power.run
pytest
```

Nothing in the November layers draws a random number. The same `params.yaml` gives the same charts. `--smoke` is the short path: fewer electrochemical cases, output in a temporary directory. The notebook obeys `SPACE_POWER_SIMS_MODE=smoke` for the same reason. CI installs the pinned stack, runs pytest, and smoke-runs `python -m lunar_power.run --smoke`. It does not redraw the committed PNGs.

## How to read the charts

### A — 2 November. Below 0 °C, charging starts to plate lithium

Two panels, same vertical axis. The left is titled "Our model: off until the anode hits 0 V". The right is titled "Cross-check: plating rises smoothly". That cross-check is PyBaMM's irreversible plating kinetics on the Doyle–Fuller–Newman model, which is a Butler–Volmer tail: small above 0 V, never quite zero. The legend does not say "C/2" and "1C" on their own. It says "2-hour charge (C/2 = 2.5 A)" and "1-hour charge (1C = 5 A)". The line under the title says what a C-rate is: 1C charges the full 5 Ah cell in one hour. The vertical axis is labelled "Lithium plated during charge (mAh of charge diverted to plating)", read at the moment the cell hits 4.2 V, from the same rested empty state. The right-hand scale is the same quantity in milligrams of lithium metal. One ampere-hour of plating is about 259 mg, from \((3600 / F) \times 6.94\) g, with \(F\) the Faraday constant.

The title is about the onset. A title that said colder charging deposits more metal would be false for our 1C result: −10 °C finishes with more metal than −20 °C, because the colder charge hits 4.2 V first.

The left-hand panel is a step because the rule is a step. Nothing plates while the anode can still pass the current above 0 V versus lithium metal. When it cannot, the leftover current plates, and the line jumps. There is no constant-voltage phase after 4.2 V to round that corner off. The right-hand panel rises smoothly because PyBaMM's plating rate is a Butler–Volmer exponential that is small but not zero above 0 V, and because the reaction is spread through the thickness of the electrode. The two shapes are the two models. They are not two measurements of one curve.

On our panel, C/2 plates only at −20 °C, about 125 mAh out of 2.13 Ah. At 0 °C and −10 °C it plates nothing (the anode stays about 3 mV and 9 mV positive). 1C plates nothing down through 0 °C, about 75 mAh at −10 °C (1.59 Ah passed, plating from 1.17 Ah), and about 33 mAh at −20 °C (only 0.92 Ah passed, plating from 0.72 Ah). The −20 °C point is below the −10 °C point because the voltage limit cuts the charge off. The onset still moves earlier as the cell gets colder. A version of this figure with eight equal shells showed a few milliampere-hours at 0 °C and −10 °C on C/2, in that order. That was the outer bin over-filling. It is not this figure.

PyBaMM plates at every temperature, more as it gets colder, and less in absolute milliampere-hours at 1C than at C/2 because the 1C charge is cut short. Read that panel as the kinetics having a tail, and the electrode not being uniform.

Takeaway: the cold-charge limit is the negative electrode potential reaching 0 V versus lithium metal. It comes out of the kinetics and the transport. It is not a number typed in as a charger setting. The amount of metal at the voltage cutoff is not, by itself, a ranking of how cold the cell was.

### B — 9 November. Same charge, less energy back when the cell is cold

Solid lines are our model. Dashed lines are labelled "Full cell model": PyBaMM's Doyle–Fuller–Newman model, plating off. Warm is 25 °C, blue is 0 °C, green is −20 °C. The axes say "Charge taken out (ampere-hours)" and "Cell voltage (volts)". The title states the rate in words: a 1-hour discharge, 5 A on this 5 Ah cell. The corner note gives the energy drop in watt-hours and says to compare the percentage.

| | 25 °C | 0 °C | −20 °C | Drop, 0 °C vs 25 °C |
|---|---|---|---|---|
| Our single-particle model | 17.30 Wh, 4.94 Ah | 15.48 Wh, 4.66 Ah | 10.22 Wh, 3.21 Ah | 10.5% |
| PyBaMM DFN | 17.22 Wh, 4.92 Ah | 15.27 Wh, 4.63 Ah | 3.51 Wh, 1.07 Ah | 11.4% |
| Ingenuity's pack, different cells | 44.4 Wh | 38.8 Wh | not the comparison | 12.6% |

The watt-hours are not comparable across the bottom row. Ingenuity's cells are 2 Ah nameplate in a six-cell series string. Ours is one 5 Ah commercial cell. The percentages from 25 °C to 0 °C land in the same neighbourhood: 11%, 11%, 13%.

The −20 °C dashed curve ending near 1.1 Ah is the single-particle assumption failing in public. During discharge, lithium ions are consumed at the positive electrode and released at the negative one. In the DFN the positive-electrode salt concentration falls from the initial 1000 mol/m³ to essentially zero by about 0.4 Ah, while the negative electrode is enriched past 3000 mol/m³. Once a pore is empty of salt, that part of the electrode cannot keep the reaction going, and the terminal voltage is pulled down to 2.5 V by about 1.07 Ah. The solver's minimum goes a fraction below zero there; tightening the relative tolerance to \(10^{-8}\) did not move the cutoff, so that undershoot is the empty-pore limit of this discretisation, not a second plateau. An earlier draft of the figure spaced the solver's time steps evenly along the ampere-hour axis. After the salt had gone, those steps are tiny and the voltage is nearly constant, so the line looked flat near 3.3 V from about 0.2 to 0.7 Ah. The axis is now the integral of current, and the voltage falls smoothly.

Our model holds the salt concentration at 1000 mol/m³ everywhere and ignores the electronic resistance of the positive coating (0.18 S/m in this parameter set). It still has lithium it can reach. The discharge now ends when the NMC surface fills and the terminal voltage hits 2.5 V, at 3.21 Ah and 10.22 Wh. That number is what the single-particle assumptions produce. It is not a prediction of this cell at −20 °C. From 25 °C to 0 °C the two models still agree on the size of the drop, and that is the comparison with Ingenuity. Below that, trust the DFN direction: transport in the electrolyte, which we removed, is what ends the discharge.

An earlier draft of the solid −20 °C curve stepped from about 2.78 V to about 2.66 V near 3.2 Ah and then ran flat out to 3.75 Ah. That plateau was a guard on the exchange current. The surface concentration was clipped a whole 1 mol/m³ short of full, so once the outer shell was that close the exchange current stopped changing while the shell kept filling. The overpotential sat still, near 2.66 V, for about another half an ampere-hour, and the 2.5 V event never fired. The clip is now \(10^{-10}\) of the maximum concentration. The exchange current keeps falling as the surface fills, the voltage falls through 2.5 V, and the line ends. The last few thousandths of an ampere-hour are steep, because the exchange current is heading for zero. That is the cut-off. The 25 °C and 0 °C energies are unchanged, because those discharges were already ending on the cut-off.

Takeaway: cold energy loss of this kind is voltage sag. Warm the cell and it comes back. That is a different loss from the metal in chart A.

### C — 16 November. Halve the heat leak and you roughly halve the battery

Top left: heater energy against the heat leak, no radioisotope heat, for a 354-hour night at a 95 K sink and a 125-hour night at a 50 K sink. The axes say watt-hours and watts per °C. A difference of one kelvin is one degree Celsius, so a watt per °C is the same number as a watt per kelvin. The legend says "354-hour night" and "125-hour shadowed night" rather than abbreviations, and the title says the 1 W heater is a radioisotope heater. Both lines are straight in energy versus the leak, which is \(P = G \Delta T\) times a fixed duration. At the low end, 0.005 W/°C, the long night needs about 315 Wh and the short night about 139 Wh. At 0.2 W/°C those are about 12613 Wh and about 5579 Wh. The vertical line is the example radiative leak, about 0.0349 W/°C.

Top right: the same two leaks, converted to cell mass at 142.12 Wh/kg. The mass is on its own axes. A second vertical scale drawn on the energy panel printed its tick labels on top of the neighbouring panel. At 0.02 W/K the long-night hold is about 3.56 W, about 1261 Wh, about 8.9 kg of cells.

Bottom: all four combinations, zoomed to \(G \le 0.04\) W/K, so a 1 W radioisotope unit is visible. On the long night at 0.005 W/K the unit covers the leak and the heater energy is zero. The unit saves about 1 W times the length of the night only when the leak exceeds 1 W. On the full-scale energy panel that offset is a few percent, which is why the zoom has its own axes.

The 354-hour night costs more heater energy than the 125-hour night at the same conductance, even though the short night's sink is colder. Duration dominates this particular sweep.

Takeaway: insulation conductance is the multiplier on the battery you have to fly. A one-watt radioisotope unit matters for a very tight leak, and stops mattering once the leak is many watts.

### D — 23 November. A small pack that heats itself can still freeze

One 354-hour equatorial night, \(G = 0.02\) W/K, 3 kg, specific heat 900 J/(kg·K), starting at 20 °C and full. Stored energy 426 Wh. No radioisotope heat.

Keep-warm cools from 20 °C to 0 °C with the heater off, holds 0 °C until the battery is empty at about 124 hours, then falls toward the sink. The figure marks that moment "heater stops, 124 hours". Hibernation never turns the heater on. The lower axis is "State of charge (1 means full)", and hibernation stays at 1. Both traces finish within a degree of −178 °C. The figure labels that line "surroundings, −178 °C (95 K)". They do not reach 50 K, because the equatorial sink in this scenario is 95 K.

The 3 kg pack cannot buy the whole night at this conductance. Chart C's 8.9 kg figure is what the whole-night hold costs. Hibernation arrives at the same dawn temperature with the charge still in the cells. Whether those cells then accept a charge is the question chart A is about, and NASA's dwells were not run at 100% state of charge.

Takeaway: once the heater has spent the battery, keep-warm and hibernation are the same cold pack, except hibernation still has a state of charge.

## Validation

- Inventory. Graphite plus NMC plus plated metal is conserved to a relative tolerance of \(10^{-3}\) on a plating charge.
- Nameplate. A warm C/5 discharge returns within 10% of 5 Ah and ends at 2.5 V.
- Arrhenius. Our factors match PyBaMM's evaluated functions at 253.15 K and 298.15 K.
- Energy, night model. The integrated balance closes to better than 500 J on keep-warm and on hibernation. Doubling \(G\), with no radioisotope heat, doubles the heater energy both as algebra and in a short dynamic hold.
- Ingenuity. Relative drop 12.6% against our 10.5% and PyBaMM's 11.4% from 25 °C to 0 °C at 1C. Direction and rough size only.
- Plating onset. At 1C our switch stays off at 25 °C and at 0 °C. Plating at −20 °C begins after less charge than plating at −10 °C. The final milliampere-hours go the other way, because the −20 °C charge hits 4.2 V first. On C/2 the resolved mesh plates at −20 °C and not at 0 °C or −10 °C. PyBaMM's plated amount at −20 °C exceeds its amount at 25 °C.
- A ten-second PyBaMM discharge at 25 °C stays inside the voltage window. That is a smoke check, not a validation.

## Assumptions and limitations

This is a teaching model. It is not a design tool and it is not a safety tool. Do not size a lander from chart C, and do not treat the 0 V switch as a charge-protocol recommendation.

- One temperature for the whole pack. No gradients inside a cell on the night model, and no neighbouring cells.
- Our cell model holds the electrolyte concentration fixed and ignores solid electronic resistance. Chart B at −20 °C is where that shows.
- The plating rule is a switch at 0 V. PyBaMM integrates a Butler–Volmer plating reaction, including a tail above 0 V, and all of that metal is dead. Neither model grows a dendrite or a short. O'Kane et al. (2020) are the citation for why the short matters; the figure does not simulate the short.
- The PyBaMM cell is an LG M50 parameter set. PyBaMM does not claim the degradation parameters are representative of a real cell's plating rate. Ingenuity's cells are a different product, with a different charge window.
- Insulation conductance, pack mass, specific heat, sunset temperature, sunset state of charge, the example emissivity and area, the C-rates, the shell count and the integrator tolerances are assumptions. The ranges are in the YAML notes.
- Specific heat does not fall at cryogenic temperature in this model, so the cooldown in chart D is slower than a real solid would manage.
- Chart D starts full. NASA Glenn froze cells at 40% state of charge and below, and marked higher states of charge as future work.
- Discharge curves are isothermal. A real cold discharge warms itself through \(I^2 R\).
- The open-circuit potential does not depend on temperature. Activation energies for diffusion and conductivity were not re-read in Ecker or Cabañero.

## Ideas to try next

- Let the cell warm from \(I^2 R\) during a cold discharge, and see how much of chart B's sag it claws back.
- Replace the 0 V switch with the irreversible Butler–Volmer plating rate, still inside the single-particle model, so the tail above 0 V can be compared against PyBaMM without the DFN gap mixed in.
- Give the pack a heat capacity that falls towards the sink temperature.
- Rerun chart D with the 50 K sink and the 125-hour night.
- Replace the example \(\varepsilon\) and area with a cited multi-layer-insulation value, and show \(G_\text{rad}(T)\) instead of a constant \(G\).
- Start chart D at 40% state of charge, which is the top of the range NASA Glenn actually dwelt.

## Questions someone will ask

**Why not just refuse to charge below −5 °C, as Ingenuity does?** That limit is NASA's operating window for those Sony cells at a low rate. Perseverance's cells, in the same presentation, are allowed down to −20 °C. The window is an output of the chemistry and the rate. The step on the left of chart A is that output for this parameter set and this 0 V rule. It is not a charger setting typed in as a temperature.

**Your two plating models disagree by a factor of several. Which one is right?** Neither is a measurement. Ours is the 0 V criterion with uniform reaction and a fixed electrolyte, so it is silent until the criterion trips and then it dumps the leftover current into metal. PyBaMM's is a distributed electrode with a plating rate that never quite turns off, and a parameter set whose plating constant is a fitted value. On our panel the onset moves earlier as the cell gets colder, and the final milliampere-hours at 1C do not, because the −20 °C charge hits 4.2 V first. PyBaMM's totals do rise as it gets colder. Neither set of milliamperes is a prediction for a named cell.

**Why is the −20 °C dashed curve so much worse than the solid one?** Because the dashed curve is allowed to run out of electrolyte salt at the positive electrode, and to drop voltage across a poorly conducting positive coating. By about 0.4 Ah the positive-electrode salt concentration in the DFN is essentially zero, and the discharge is over by 1.07 Ah and 3.51 Wh. The solid curve holds the salt at 1000 mol/m³ and skips that electronic resistance, so it still delivers 3.21 Ah and 10.2 Wh. The gap is the model. Trust the dashed direction at −20 °C. The 25 °C to 0 °C drop is where the two models, and Ingenuity's percentage, still sit together.

**Is the 10% drop a validation against Ingenuity?** Only as a relative drop, on a different cell, at a C-rate Ingenuity's presentation does not state. Matching 44.4 Wh would have meant the wrong cell.

**Chart D says hibernation wins. Does a cell survive 95 K at full state of charge?** The chart does not say that. It says the heater runs out and both strategies reach the sink, and that hibernation still has its charge. NASA's public dwells were at low state of charge. Survival at full charge is not a result of this repository.

**Why is one 1 W heater unit almost invisible on the top left of chart C?** Because that axis runs to about 12 kWh. One watt for 354 hours is 354 Wh, which is the entire low-end point and a small offset at the high end. The bottom panel is that offset, on a scale where it fits.

**Where does the 142 Wh/kg come from?** 38.8 Wh divided by 0.273 kg. Both inputs are NASA's Ingenuity numbers. The quotient is not a quoted specific energy, and it is cells only.

**What would you change first if this had to inform a design?** The conductance. Chart C is proportional to \(G\), and \(G\) here is an assumption swept over nearly two orders of magnitude. A measured heat leak would move the battery mass more than a finer particle grid would.

## Sources, and the gaps

Cited and used as numbers in the model or the comparison:

- NASA Glenn, cryogenic hibernation, [NTRS 20240004406](https://ntrs.nasa.gov/citations/20240004406). 354-hour night. Freeze-thaw context for chart D.
- NASA, Lunar Terrain Vehicle thermal challenges, [NTRS 20230002802](https://ntrs.nasa.gov/citations/20230002802). Battery often sets the heater. 0 °C or −10 °C. 125-hour extended night. 50 K.
- Williams et al., Icarus 2017, [10.1016/j.icarus.2016.08.012](https://doi.org/10.1016/j.icarus.2016.08.012). Equatorial pre-dawn temperature about 95 K. Equatorial noon is quoted in the paper as about 387–397 K; that day value is not a model input.
- NASA Science, radioisotope heater units. About 1 W, plutonium-238, no moving parts.
- NASA, battery design, testing and operation for Perseverance and Ingenuity. Energies, mass, charge window, cell count and chemistry distinction.
- Chen et al. 2020, [10.1149/1945-7111/ab9050](https://doi.org/10.1149/1945-7111/ab9050). LG M50 parameter set.
- O'Kane et al. 2022, [10.1039/D2CP00417H](https://doi.org/10.1039/D2CP00417H). Plating parameter set.
- O'Kane et al. 2020, [10.1149/1945-7111/ab90ac](https://doi.org/10.1149/1945-7111/ab90ac). Why plating at low temperature is a short-circuit problem.
- Nyman, Behm and Lindbergh 2008, [10.1016/j.electacta.2008.04.023](https://doi.org/10.1016/j.electacta.2008.04.023). Electrolyte conductivity fit.
- Sulzer et al. 2021, [10.5334/jors.309](https://openresearchsoftware.metajnl.com/articles/10.5334/jors.309). PyBaMM.
- PyBaMM 25.8.0 parameter source: [OKane2022.py](https://github.com/pybamm-team/PyBaMM/blob/v25.8.0/src/pybamm/input/parameters/lithium_ion/OKane2022.py), [Chen2020.py](https://github.com/pybamm-team/PyBaMM/blob/v25.8.0/src/pybamm/input/parameters/lithium_ion/Chen2020.py).
- NIST CODATA for \(F\), \(R\), \(k_B\) and \(\sigma\).

Not used as quoted results, because the digit was not re-read or has no public source pinned down:

- The activation energies 30300, 25000, 35000, 17800 and 17000 J/mol are PyBaMM's function values. The file comments name Ecker et al. (2015) and Cabañero et al. (2018). Those papers were not re-read for this repository. The test checks PyBaMM, not those tables.
- Chen and O'Kane scalars were checked against the installed PyBaMM 25.8.0 parameter object. They were not transcribed by hand from the PDFs.
- Waldmann et al., Journal of Power Sources 262 (2014), [10.1016/j.jpowsour.2014.03.112](https://doi.org/10.1016/j.jpowsour.2014.03.112), was not read. No plating-versus-temperature threshold is quoted from it.
- No public conductance for a generic small lander was found. \(G\), mass, specific heat, sunset temperature, sunset state of charge, emissivity and radiating area stay labelled assumptions.
- A journal calorimetry value sometimes quoted for a commercial 18650 was not opened, so specific heat stays an assumption inside 700–1200 J/(kg·K) and that value is not cited.
- An "80% state of health" end-of-life line is not drawn. No standard was opened for that convention, so it is not a result of this model.
- Graphite's volume change on full lithiation is used in the December chapter, from Schweidler et al. (2018), and only there.

## December: the ageing layer

Personal project using only public data. Not affiliated with or endorsed by my employer.

November asks whether a cell can take a charge in the cold, and what a lunar night costs in heater energy. December asks how the cell loses capacity once it is warm enough to cycle. It is the same model. The film thickness and the lithium it consumes are handed back to the November cell as a lower graphite inventory and a higher series resistance.

Four posts, four charts:

| Chart | Post | Question the chart answers |
|---|---|---|
| E | 7 December 2026 | How many cycles does a 90 minute orbit accumulate, next to one cycle a day and one cycle a lunar day? |
| F | 14 December 2026 | Why does the surface film thicken with the square root of time, and how cold slows that? |
| G | 21 December 2026 | Where does radiation sit, if it is not a term in the rate? |
| H | 28 December 2026 | At three depths of discharge, what is left, and why is Opportunity's clock not an orbit? |

### What is being conserved

A cell stores lithium. Discharge moves it from the graphite to the positive electrode. Charge moves it back. Anything that locks lithium into a side product removes it from that shuttle. The surface film on the graphite, the solid-electrolyte interphase, is that side product. Forming it consumes lithium and a little solvent. A stable film is what lets the cell cycle. A film that keeps breaking and regrowing keeps consuming lithium.

Two conservations, and one conversion between them.

**Charge.** Current is charge per time. One lithium ion carries one elementary charge, so the molar rate tied to a current density \(j\) (amperes per square metre of graphite surface) is

\[
\dot n = \frac{-j}{F}
\]

when \(j\) is negative for a reduction. \(F\) is the Faraday constant, 96485.3321 C/mol, from `common/constants.py`. Integrated and converted to ampere-hours,

\[
Q_\text{loss} = \frac{n_\text{Li} F}{3600}.
\]

That is `capacity_loss_Ah`.

**Mass.** Solvent diffuses through the film and is reduced at the graphite. Each mole of film has a volume \(V_\text{bar}\) (m³/mol), the partial molar volume. If \(z\) moles of lithium are locked per mole of film, a thickness increase \(\Delta L\) on one square metre locks

\[
n_\text{Li} = \frac{z\,\Delta L}{V_\text{bar}}
\]

moles. That is `lithium_per_area_mol_m2`. \(z\) in this parameter set is 1. Ploehn, Ramadass and White describe a two-electron reduction of the solvent. This model does not replace the 1 with a 2. PyBaMM's solvent-diffusion-limited option uses \(z = 1\), and the cross-check is that option. Putting in a 2 would make the cross-check a different equation. The choice is stated here so it is not hidden in the arithmetic.

The initial film, 5 nm in the parameter set, is the formed cell. Its lithium is already absent from Chen's initial concentrations. Only thickness grown after \(t = 0\) is new loss.

### Fick's law, and why the film goes as the square root of time

Take the film as a slab of thickness \(L\). Solvent concentration is \(c\) at the outer face (the electrolyte side) and, if the reaction at the graphite is fast, about zero at the inner face. Fick's law for a linear profile and a constant diffusivity \(D\) gives the molar flux

\[
N = \frac{D\,c}{L}.
\]

PyBaMM writes the reduction current that belongs to that flux as

\[
j = -\frac{D\,c\,F}{L}
\]

and the thickness rate as

\[
\frac{dL}{dt} = -\frac{V_\text{bar}\,j}{F z} = \frac{V_\text{bar}\,D\,c}{z\,L}.
\]

Multiply through by \(L\):

\[
L\,dL = k\,dt, \qquad k = \frac{V_\text{bar}\,D\,c}{z}.
\]

Integrate from the initial thickness \(L_0\) at \(t = 0\):

\[
L(t) = \sqrt{L_0^2 + 2kt}.
\]

That is `thickness_m`. Plot \(L^2\) against \(t\) and the slope is \(2k\). Chart F's right-hand panel is that line. The left-hand panel is \(L\) itself, which rises quickly and then slows, because a thicker film is a longer diffusion path.

\(D\) carries the Arrhenius factor already used in November:

\[
\frac{D(T)}{D(T_\text{ref})} = \exp\left[\frac{E_a}{R}\left(\frac{1}{T_\text{ref}} - \frac{1}{T}\right)\right].
\]

\(E_a\) is 38000 J/mol in the OKane2022 set. At 0 °C the factor is about a quarter of its value at 25 °C, so the cold curve on chart F sits under the warm one. Same function as `Cell.arrhenius`. `arrhenius_factor` and `growth_constant_m2_s` are this paragraph.

O'Kane et al. (2022) use this diffusion-limited form and show that changing \(D\) by an order of magnitude moves the capacity loss more than switching from one film layer to two. Ploehn, Ramadass and White (2004) are the continuum paper that obtained the square-root thickness and checked it against storage data. Wang, Kadam, Li, Shi and Qi (2018) review the film models this sits among. The digits for \(D\), \(c\), \(V_\text{bar}\), \(z\), \(L_0\), the resistivity and \(E_a\) are the OKane2022 values shipped in PyBaMM 25.8.0. PyBaMM's own note says they were fitting values, not a claim about one commercial cell. A test compares our copies to that parameter object.

### Symbols in the film model

| Symbol | Code | Unit | Meaning |
|---|---|---|---|
| \(L\) | `thickness_m` | m | Film thickness. |
| \(L_0\) | `SeiKnobs.initial_thickness_m` | m | Formed-film thickness, 5 nm. |
| \(D\) | `solvent_diffusivity_m2_s` | m²/s | Solvent diffusivity in the film at the reference temperature, \(2.5 \times 10^{-22}\). |
| \(c\) | `solvent_concentration_mol_m3` | mol/m³ | Solvent concentration at the outer face, 2636. |
| \(V_\text{bar}\) | `partial_molar_volume_m3_mol` | m³/mol | Volume of film per mole, \(9.585 \times 10^{-5}\). |
| \(z\) | `lithium_per_sei_mole` | 1 | Lithium moles per mole of film. 1 in this set. |
| \(E_a\) | `activation_energy_J_mol` | J/mol | 38000. |
| \(T_\text{ref}\) | `reference_temperature_K` | K | 298.15, shared with November. |
| \(\rho\) | `resistivity_ohm_m` | Ω·m | 200000. Film resistance uses the grown thickness only. |
| \(k\) | `growth_constant_m2_s` | m²/s | The constant in \(L\,dL = k\,dt\). |
| \(A\) | `Cell.negative_surface_area_m2` | m² | Graphite particle surface. About 3.36 m² for this cell. |
| \(Q\) | `capacity_loss_Ah` | Ah | Lithium loss, Faraday's law. |

### Cycles, and why depth of discharge appears at all

The diffusion law above does not know the depth of discharge. A cell on the shelf and a cell being cycled grow the same film if the only process is solvent diffusion through an intact layer. Depth of discharge enters as mechanical damage.

Schweidler et al. (2018) measured a 13.2% volume expansion of graphite from empty graphite to LiC₆. Call that \(\varepsilon_\text{full} = 0.132\). A cycle that uses a depth of discharge \(\delta\) (a fraction of the nameplate, between 0 and 1) is taken to strain the particle by

\[
\varepsilon = \varepsilon_\text{full}\,\delta.
\]

The linear map is an assumption. The 13.2% is a crystal volume, not a measured thickness change of this LG M50 electrode.

Elastic energy density goes as \(\varepsilon^2\). The fraction of surface that cracks on a cycle is taken to scale the same way, and to equal an assumed fraction \(f_\text{full}\) when the particle is fully lithiated:

\[
f = f_\text{full}\left(\frac{\varepsilon}{\varepsilon_\text{full}}\right)^2 = f_\text{full}\,\delta^2.
\]

`crack_area_fraction` is that line. \(f_\text{full}\) is an assumption, swept from 0.002 to 0.05. The curves are drawn at 0.02. It is not a measured crack area. The low end of the sweep is where cracking barely adds to the diffusion loss. The high end consumes a large part of the nameplate on the 16-cycle-a-day clock. Chart H's shaded band is that sweep on the 40% curve. Read the band before reading any one line as a life prediction.

On the cracked fraction, a new skin has to form. Formation up to \(L_0\) is the fast step. Diffusion limits only the later thickening. Each full cycle therefore adds the lithium in a film of thickness \(L_0\) on area fraction \(f\),

\[
\Delta n_\text{rebuild} = f\,\frac{z L_0}{V_\text{bar}},
\]

plus the diffusion increment on the intact area and on the fresh patch. `_step_thickness` advances those two populations by one period. `fade_history` charges the rebuild once per completed cycle. A sample that falls inside a cycle sees diffusion only for the stub, so a rebuild is not counted twice. With \(f_\text{full} = 0\) the thickness matches the closed form. A test checks that.

The nameplate stays 5 Ah. Remaining fraction is \(1 - Q_\text{loss}/Q_\text{nameplate}\), and it is not allowed to go negative. A curve that sits on zero has consumed the nameplate inventory under this assumption. It is not a cell that was integrated down to 2.5 V.

### The orbit clock

NASA Glenn's description of an LEO test (NTRS 20050192209) is an orbit of about 90 minutes: 55 minutes of charge in sunlight, 35 minutes of discharge in eclipse. A later status paper (NTRS 20080008855) uses the same split and a 40% depth of discharge. Dividing a civil day by 90 minutes is exactly 16. `cycles_per_earth_day` is that division. Nothing is fitted.

The same 2005 note sets the goal as 5 years of life, or 30,000 cycles. 30,000 / 16 = 1,875 days, which is a bit over five calendar years. The paper treats them as one goal. The 2008 paper reports that the batteries under test had passed 12,000 cycles and were still above the failure voltage. Chart E marks 12,000. It does not mark a completed total the paper does not give.

On this 5 Ah cell, 40% of the nameplate in 35 minutes is \(0.4 \times 5 / (35/60) = 3.4\) A, and the same 40% put back in 55 minutes is 2.2 A. `current_A` is ampere-hours over hours. Those currents are what this cell would need to follow the published timing. They are not the 12.5 A and 17 A of the 25 Ah batteries in the 2008 paper.

A lunar day on the chart doubles the 354 hour night, so sunlit hours equal the night. The ratio is an assumption swept from 0.8 to 1.2, drawn at 1. One cycle per lunar day is then about 12 cycles a year. That line sits on the axis of chart E on purpose.

### Radiation, labelled and not integrated

Ratnakumar, Smart, Whitcanack, Davies, Chin, Deligiannis and Surampudi (J. Electrochem. Soc. 151, 2004, A652) irradiated aerospace lithium-ion cells to cumulative doses up to 25 Mrad. The abstract's context for Jupiter and its moons is about 4 Mrad. They report only a marginal capacity decline and no significant change in the later fade rate, and they say that study had no unirradiated control. An electric vehicle does not see that dose. This model does not turn Mrad into a capacity loss. There is no dose-to-fade equation here because I do not have one I am willing to treat as this cell's rate.

Chart G draws radiation in a separate box. The assumption sweep is a set of multipliers on solvent diffusivity: 1, 2 and 5. `assumption_multipliers` returns them. `FADE_DIFFUSIVITY_MULTIPLIER` is 1. Charts E, F and H, and the feed into the cold model, use 1. A test checks that a multiplier of 2 does thicken the film faster, and that the fade summary records 1.

### How ageing changes the November cell

`aged_state_from_params` runs the 40% LEO duty for `feed_age_years` (an assumption, swept from 0.25 to 5 years, drawn at 1). `apply_fade` then does two things.

1. **Inventory.** The lost moles are removed from the graphite concentration:

\[
\Delta c_- = \frac{n_\text{Li}}{\epsilon_\text{active}\,L_-\,A_\text{electrode}}.
\]

`Cell.initial_negative` falls by \(\Delta c_-\). The nameplate capacity is not rescaled. A 1-hour discharge is still 5 A, defined on the fresh 5 Ah, and the aged cell runs out of graphite lithium sooner. That is the capacity the cold discharge sees.

2. **Resistance.** O'Kane write the film overpotential as \(\eta = \rho L j\), with \(j = I / A\). The extra series resistance is \(\rho L_\text{grown} / A\). `Cell.ohmic_resistance` adds it only when the grown thickness is positive. A fresh cell, and a state with zero growth, returns the November resistance exactly. A test checks the equality.

`run_scenario` applies that cell before the discharge, and multiplies the night's stored watt-hours by the remaining fraction. Charts A to D do not go through this path. They call `cell_from_params` and leave the three new `Cell` fields at zero. The regression test recomputes the 25 °C discharge energy, the −20 °C C/2 plated milliampere-hours, and the heater-energy ends, and compares them to the November digits.

### Opportunity, as a case rather than a fit

NASA's end-of-mission release says Opportunity was designed to last 90 Martian days and exceeded that life by 60 times, and that the mission was almost 15 years. The end-of-mission report (NTRS 20200000214) says the last communication was on sol 5111, 10 June 2018, after more than fourteen years. 60 × 90 = 5,400 sols, which is not 5,111. Both wordings are NASA's. Chart H marks 90 sols and sol 5111. It does not replace 5111 with 5400.

A mean sol is 24 hours, 39 minutes and 35.244 seconds (NASA GISS Mars24). The code adds those three parts. It does not use a rounded "1.027 days" typed in by hand.

The 2004 MER battery workshop slides (NTRS 20080015793) say the depth of discharge was typically 60–70% through sol 54. The 60% curve is the lower end of that range. It is early-mission telemetry, not a depth measured on every one of the 5,111 sols. One cycle per sol is an assumption, swept from 0.5 to 1.5, drawn at 1, because those slides show a charge and a discharge against sol number. It is not a counted total for the whole mission.

The dashed line is that cadence at 60% depth. The solid orange line is the same depth on the 16-cycle-a-day clock. The lesson the chart is allowed to carry: a rover that cycles about once a sol does not accumulate the crack damage of an LEO battery, so a 90 sol design can still be a full cell years later under this assumption. It is not a prediction of Opportunity's ampere-hours. Those cells are not this LG M50 parameter set. No capacity-retention number from the mission is used, because the public figures I could pin down do not include one I have read in a table.

### Where each new function lives

`lunar_power/ageing/orbit.py`

- `cycles_per_earth_day` divides 1440 by the orbit period.
- `earth_days_for_cycles` divides a cycle count by that rate.
- `current_A` is depth of discharge times nameplate, divided by the duration in hours.
- `lunar_day_hours` is the night times one plus the day-to-night ratio.
- `sol_seconds` and `sol_in_earth_days` add the GISS parts and divide by 86400.
- `profile_from_params` reads the book and returns the dict chart E prints.

`lunar_power/ageing/sei.py`

- `SeiKnobs` and `knobs_from_params` are the film digits. No defaults.
- `arrhenius_factor` is the temperature quotient.
- `growth_constant_m2_s` is \(k\), including an optional diffusivity multiplier.
- `thickness_m` is the closed form.
- `lithium_per_area_mol_m2` is \(z \Delta L / V_\text{bar}\).
- `capacity_loss_Ah` is Faraday's law.
- `storage_loss` is the open-circuit case: no cycles, so the closed form is the whole answer.

`lunar_power/ageing/fade.py`

- `crack_area_fraction` is \(f_\text{full}\delta^2\), clipped to the range 0 to 1.
- `_step_thickness` advances the intact film and the fresh patch by one interval.
- `fade_history` walks whole cycles up to the last sample time and records thickness, loss and remaining fraction.
- `pure_diffusion_thickness_m` is the grey dashed line on chart H.
- `duty_from_params` reads the three depths, the sweep and the two cadences.
- `FadeResult` is the record those functions return.

`lunar_power/ageing/radiation.py`

- `FADE_DIFFUSIVITY_MULTIPLIER` is 1.
- `assumption_multipliers` reads the swept 1, 2 and 5.
- `paper_doses_Mrad` reads the 4 Mrad and 25 Mrad context numbers for the diagram only.

`lunar_power/ageing/feed.py`

- `AgeingState` is the lithium, the grown thickness and the remaining fraction.
- `state_at` lifts one sample of a `FadeResult` into that state. Moles are recovered from ampere-hours by \(n = Q \times 3600 / F\).
- `apply_fade` returns a new `Cell`. It raises if the loss would empty the graphite.
- `aged_state_from_params` is the one-year LEO feed the scenario uses.

`lunar_power/ageing/pybamm_sei.py`

- `_solve_rest` builds an isothermal single-particle model with `"SEI": "solvent-diffusion limited"` and the OKane2022 set, and rests it.
- `smoke_thickness_m` rests for 10 minutes. CI uses it to prove the option imports and steps.
- `build_cache` writes rests of 1, 4, 24 and 72 hours at 0 °C and 25 °C to `sei_cache.json`.
- `load_cache` reads that file. Chart F plots the points. A test checks each point against `storage_loss`.

`lunar_power/scenario.py`

- `Layers` and `parse_layers` turn a comma-separated list into switches.
- `FUTURE_LAYERS` is `safety`, `pack`, `variation`, `mission`. Switching one on raises `NotImplementedError`. They are named so the later months have a place to land. They are not empty physics pretending to run.
- `run_scenario` runs ageing first, then a 25 °C and a 0 °C discharge of the cell that produced, then the keep-warm night with the stored energy scaled by the remaining fraction.
- `fresh_discharge_energy_Wh` forces ageing off. The regression test uses it.

`lunar_power/charts/december.py` is `figure_e`, `figure_f`, `figure_g`, `figure_h` and `generate`. `lunar_power/run.py` is the command. `Cell.ohmic_resistance` is the November sum plus the film term described above.

### How to read the December charts

**E — 7 December. Sixteen cycles a day.** The left bar is one orbit: 55 minutes of charge, 35 minutes of discharge, with the current this 5 Ah cell would need to move 40% of its nameplate in each window. The right-hand panel counts cycles against Earth years. The orange line is 16 a day. The blue line is one a day. The green line is one a lunar day, and it barely leaves the axis. The dashed line is NASA's 30,000 cycle goal. The dotted line is the "over 12,000" status in the 2008 paper. Takeaway: a low-Earth-orbit battery lives a whole automotive life every few months, because the orbit is short, not because the cell is asked for a deep cycle.

**F — 14 December. The invisible skin.** Left: film thickness in nanometres against days on the shelf, at 25 °C and at 0 °C. The markers are PyBaMM rests using the same equation. Right: thickness squared, which is a straight line. The title states the milliampere-hours consumed in 120 days at 25 °C. Takeaway: the film protects the graphite by growing, and the growth slows itself; cold slows it further, by the same Arrhenius factor as the November kinetics.

**G — 21 December. Radiation.** Two boxes. The left box is what the rate actually integrates: heat, time, depth of discharge. The right box is radiation, with the 2004 paper's doses and its own caveat about the missing control. Under the boxes, the diffusivity multipliers are written out and labelled as not applied. Takeaway: radiation is a real extra stress for a spacecraft and not for an EV, and this model draws it instead of inventing a fade law.

**H — 28 December. Three depths, and Opportunity's clock.** Solid lines are 20%, 40% and 60% depth, all at 16 cycles a day. The shade is the crack-fraction sweep on the 40% line. The grey dashed line is the film with no cracking, the same for every depth. The orange dotted line is 60% depth at one cycle a sol. The vertical marks are the 90 sol design life and sol 5111. Takeaway: under this assumption a deeper cycle rebuilds more film, and a rover's once-a-sol clock does not pile that damage up the way an orbit does. The line that reaches zero has spent the nameplate. The shade says how far that conclusion moves when the crack fraction moves.

### Validation

- 1440 / 90 = 16 exactly. 55 + 35 = 90. 30,000 / 16 = 1,875 days.
- The closed-form thickness matches a numerical cycle history with the crack fraction set to zero.
- Against the cached PyBaMM rests, thickness agrees to better than 0.1% relative (the largest gap in the cache is a few parts in 10,000). Capacity loss, which is the small difference \(L - L_0\), agrees to within about 1%. The test allows 0.2% on thickness and 2% on ampere-hours.
- A fresh cell's ohmic resistance and graphite concentration match the November cell. An aged cell has a higher resistance and returns less charge and less energy on the same discharge function.
- The November anchors are unchanged: 17.30 Wh at 25 °C on a 1-hour discharge, about 125 mAh plated at −20 °C on a 2-hour charge, and the heater-energy ends on the equatorial night.

### Limitations

- The film parameters are fitting values from OKane2022, not a measured diffusivity of this cell, and not a space cell.
- \(z = 1\) follows that parameter set. A two-electron stoichiometry would double the lithium loss. It is not what the cross-check solves.
- \(f_\text{full}\) and the linear strain map are assumptions. The shaded band is the honest range. A single curve inside it is not a measured life.
- The fade chart is an inventory count. It does not run the single-particle model for 30,000 cycles, and it does not grow the film inside a cold charge. The feed is one age, applied as a new initial state, and then the November discharge runs.
- Radiation is not in the rate. The 2004 paper's "marginal decline" had no unirradiated control. No percent from that paper is used.
- Opportunity's depth is the early-mission 60% end of "60–70% through sol 54". The once-a-sol cadence is an assumption. No mission capacity-retention number is plotted.
- The 20% and 40% depths are NASA test conditions. The fade at those depths is this model, not a trace digitised from the NASA papers.
- Reaching zero remaining capacity means the assumed crack term has consumed 5 Ah. It is not a voltage-cutoff prediction and not a statement that an LEO cell dies on that day.

### What to try next

- Replace \(f_\text{full}\) with a cited crack-area measurement, and narrow the band.
- Run the single-particle model for a few hundred LEO cycles with the film resistance updated each cycle, and see whether the inventory shortcut still holds.
- Repeat chart H at 0 °C, where the Arrhenius factor slows the film and the November plating limit starts to matter on charge.
- Read a later LEO status paper that states a completed cycle count past 12,000, and move the dotted line only if the sentence is in the paper.
- When the safety layer is added, the film resistance should be the same object the thermal-runaway heat already sees. The switch is `safety` on the scenario runner. It raises until that month.

### Questions someone will ask about this layer

**Sixteen cycles a day sounds like a slogan. Where is the 16?** 24 hours is 1440 minutes. The NASA orbit is 90 minutes. 1440 / 90 = 16. The 55 and 35 are the sunlight and eclipse split in the same notes. The 16 is arithmetic.

**Is 30,000 cycles something a battery achieved, or a target?** In the note I used, it is the goal: "5 years of life, or 30,000 cycles." The 2008 status had passed 12,000 cycles without hitting the failure voltage. Chart E draws both, and it does not call 30,000 a completed test.

**Your film model matches PyBaMM. Does that mean the life is right?** It means the square-root equation is the equation PyBaMM integrates on a rest, for this parameter set. The diffusivity is a fitting value. Matching the solver is not a measurement of a cell on orbit.

**Why does depth of discharge do so much on chart H when the film equation does not contain it?** Because of the crack term, and that term is an assumption. Turn \(f_\text{full}\) down to the bottom of the sweep and the three solid lines collapse toward the grey dashed line, which is pure diffusion and has no depth in it. The shade is that statement, drawn.

**You show Opportunity still holding most of its capacity. Did you fit the rover?** No. The dashed line is this LG M50 parameter set, at 60% depth, at one assumed cycle per sol, with the assumed crack fraction. The rover's cells are a different product. The marks at 90 sols and sol 5111 are NASA's dates. There is no mission ampere-hour on the axis.

**Chart H hits zero. Are you saying an LEO cell is dead at 13 years?** I am saying that at 60% depth, 16 cycles a day, and a crack fraction of 0.02, the inventory count reaches 5 Ah. Change the fraction inside the sweep and the zero moves or disappears. It is not a pack that was discharged to its cutoff on that day.

**Why is radiation a picture and not a curve?** Because the public cell result I could read is qualitative, the study says it had no control, and I will not invent a percent loss per Mrad. The multipliers under the picture are labelled as an assumption and are not in the fade.

**Does the cold model actually feel the ageing?** Yes, on the scenario path. `apply_fade` lowers the graphite concentration and adds \(\rho L / A\) to the ohmic resistance, and the night's stored watt-hours are scaled by what remains. Charts A to D are the fresh cell, so the November posts do not move. A test discharges both cells and checks that the aged one returns less.

## December gaps

- The solvent diffusivity \(2.5 \times 10^{-22}\) m²/s and the other film digits are locked to PyBaMM 25.8.0's OKane2022 object. The papers those digits were taken from were not re-read table by table. PyBaMM says they are fitting values.
- Ploehn's two-electron stoichiometry was not substituted for \(z = 1\).
- No completed LEO test total above the 2008 paper's "over 12,000" is cited. The 30,000 is the goal.
- No public cycle-by-cycle capacity for Opportunity is used. A seminar slide that quotes a later depth of discharge and a cycle count was not used, because I did not read it as a paper with a table. The early-mission "typically 60–70% through sol 54" is the depth that is used, and only the 60% end of it.
- The 2004 radiation paper's abstract is the whole of the quantitative claim: marginal decline, no significant change in the later fade rate, no unirradiated control, doses of about 4 Mrad and up to 25 Mrad. A follow-up paper with control cells was not used for a percent, because that percent was not read out of it.
- \(f_\text{full}\), the day-to-night ratio, the cycles per sol, the feed age, and the diffusivity multipliers are assumptions. The ranges are in the YAML notes.
