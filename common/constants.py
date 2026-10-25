"""CODATA 2018 constants, written out so every later formula can point here.

The 2019 SI revision makes the Boltzmann constant exact. The gas constant is
then exactly Avogadro's number times that value. The Faraday constant is a
measured product of the elementary charge and Avogadro's number, quoted to the
CODATA 2018 digits. The Stefan-Boltzmann constant is derived from k, h and c.

Sources (NIST CODATA):
- F: https://physics.nist.gov/cgi-bin/cuu/Value?f
- R: https://physics.nist.gov/cgi-bin/cuu/Value?r
- k: https://physics.nist.gov/cgi-bin/cuu/Value?k
- sigma: https://physics.nist.gov/cgi-bin/cuu/Value?sigma
"""

# Exact since the 2019 SI revision: 1.380649e-23 J/K.
BOLTZMANN_J_PER_K = 1.380649e-23

# Exact: N_A * k, with N_A = 6.02214076e23 mol^-1.
GAS_J_PER_MOL_K = 8.314462618

# CODATA 2018 value, C/mol. Not exact.
FARADAY_C_PER_MOL = 96485.3321

# Derived constant, W/(m^2 K^4): 2 * pi**5 * k**4 / (15 * c**2 * h**3).
STEFAN_BOLTZMANN_W_PER_M2_K4 = 5.670374419e-8

# Short names used in the equations in EXPLAINED.md.
BOLTZMANN = BOLTZMANN_J_PER_K
GAS = GAS_J_PER_MOL_K
FARADAY = FARADAY_C_PER_MOL
STEFAN_BOLTZMANN = STEFAN_BOLTZMANN_W_PER_M2_K4
