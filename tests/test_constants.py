"""Lock the CODATA digits so a later edit cannot quietly change Faraday."""

from common.constants import BOLTZMANN, FARADAY, GAS, STEFAN_BOLTZMANN


def test_codata_2018_values():
    assert BOLTZMANN == 1.380649e-23
    assert GAS == 8.314462618
    assert FARADAY == 96485.3321
    assert STEFAN_BOLTZMANN == 5.670374419e-8
