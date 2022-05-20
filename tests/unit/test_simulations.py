# Copyright 2022 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for Monte Carlo simulations for estimating FT thresholds."""

# pylint: disable=no-self-use,protected-access,too-few-public-methods

import itertools as it

import re
import pytest

from flamingpy.codes import alternating_polarity, SurfaceCode
from flamingpy.noise import CVLayer, CVMacroLayer, IidNoise
from flamingpy.cv.ops import splitter_symp
from flamingpy.simulations import ec_monte_carlo, run_ec_simulation

code_params = it.product([2, 3, 4], ["primal", "dual"], ["open", "periodic"])


@pytest.fixture(scope="module", params=code_params)
def code(request):
    """A SurfaceCode object for use in this module."""
    distance, ec, boundaries = request.param
    surface_code = SurfaceCode(distance, ec, boundaries, alternating_polarity)
    surface_code.graph.index_generator()
    return surface_code


class TestBlueprint:
    """A class with members to test Monte Carlo simulations for FT threshold
    estimations for Xanadu's blueprint architecture."""

    def test_all_GKP_high_squeezing(self, code):
        """Tests Monte Carlo simulations for FT threshold estimation of a
        system with zero swap-out probability and high squeezing."""
        p_swap = 0
        delta = 0.001
        trials = 10
        noise_args = {"delta": delta, "p_swap": p_swap}
        decoder_args = {}
        decoder_args["weight_opts"] = {"method": "blueprint", "integer": False, "multiplier": 1, "delta": noise_args.get("delta")}
        errors_py = ec_monte_carlo(trials, code, CVLayer, noise_args, "MWPM", decoder_args)
        # Check that there are no errors in all-GKP high-squeezing limit.
        assert errors_py == 0


class TestPassive:
    """A class with members to test Monte Carlo simulations for FT threshold
    estimations for Xanadu's passive architecture."""

    def test_all_GKP_high_squeezing(self, code):
        """Tests Monte Carlo simulations for FT threshold estimation of a
        system with zero swap-out probability and high squeezing."""
        p_swap = 0
        delta = 0.001
        trials = 10

        pad_bool = code.bound_str != "periodic"
        # The lattice with macronodes.
        RHG_macro = code.graph.macronize(pad_boundary=pad_bool)
        RHG_macro.index_generator()
        RHG_macro.adj_generator(sparse=True)

        # Define the 4X4 beamsplitter network for a given macronode.
        # star at index 0, planets at indices 1-3.
        bs_network = splitter_symp()
        noise_args = {"delta": delta, "p_swap": p_swap, "macro_graph": RHG_macro, "bs_network": bs_network}
        decoder_args= {"weight_opts": None}
        errors_py = ec_monte_carlo(trials, code, CVMacroLayer, noise_args, "MWPM", decoder_args)
        # Check that there are no errors in all-GKP high-squeezing limit.
        assert errors_py == 0


@pytest.mark.parametrize("passive", [True, False])
@pytest.mark.parametrize("empty_file", [True, False])
@pytest.mark.parametrize("sim", [run_ec_simulation])
def test_simulations_output_file(tmpdir, passive, empty_file, sim):
    """Check the content of the simulation benchmark output file."""

    expected_header = (
        "noise,distance,ec,boundaries,delta,p_swap,p_err,decoder,errors_py,"
        + "trials,current_time,decoding_time,simulation_time"
    )
    dummy_content = "blueprint,3,primal,open,0.04,0.5,0.2,MWPM,2,10,12:34:56,10,20"
    if "benchmark" in sim.__name__:
        expected_header += ",cpp_to_py_speedup"
        dummy_content += ",1"

    f = tmpdir.join("sims_results.csv")
    if not empty_file:
        f.write_text(
            f"{expected_header}\n" + "\n",
            encoding="UTF-8",
        )

    # simulation params
    params = {
        "noise": "blueprint",
        "distance": 3,
        "ec": "primal",
        "boundaries": "open",
        "delta": 0.09,
        "p_swap": 0.25,
        "p_err": 0.1,
        "trials": 100,
        "decoder": "MWPM",
    }

    # The Monte Carlo simulations
    code = SurfaceCode
    code_args = {key: params[key] for key in ["distance", "ec", "boundaries"]}

    noise_dict = {"blueprint": CVLayer, "passive": CVMacroLayer, "iid": IidNoise}
    noise = noise_dict[params["noise"]]
    noise_args = {key: params[key] for key in ["delta", "p_swap", "p_err"]}

    decoder = params["decoder"]
    args = [params["trials"], code, code_args, noise, noise_args, decoder]
    sim(*args, fname=f)

    file_lines = f.readlines()
    # file is created with header and result lines
    assert len(file_lines) > 0

    # contains the expected header
    assert file_lines[0] == expected_header + "\n"

    # contents has the expected number of columns
    assert len(re.split(",", file_lines[-1])) == len(re.split(",", expected_header))
