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
""""Unit tests for MatchingGraph classes in matching.py.

The networkx implementation is used as a reference.
"""
import itertools as it
from copy import deepcopy

import numpy as np
import pytest
import networkx as nx

from flamingpy.codes.surface_code import SurfaceCode
from flamingpy.cv.ops import CVLayer
from flamingpy.decoders.decoder import CV_decoder, GKP_binner, assign_weights
from flamingpy.decoders.mwpm.matching import LemonMatchingGraph, NxMatchingGraph, RxMatchingGraph


# Test parameters
matching_graph_types = [LemonMatchingGraph, RxMatchingGraph]
num_nodes = range(4, 24, 4)


@pytest.fixture(scope="module", params=it.product(matching_graph_types, num_nodes))
def matching_graphs(request):
    """Return an instance of the given matching graph type with random weights
    and an edge between each of the num_nodes nodes.

    Also return the same graph as a NxMatchingGraph for comparison.
    """
    MatchingGraphType, num_nodes = request.param
    graph = MatchingGraphType("primal")
    nx_graph = NxMatchingGraph("primal")
    rng = np.random.default_rng()
    for edge in it.combinations(range(num_nodes), r=2):
        weight = rng.integers(0, 10)
        graph.add_edge(edge, weight)
        nx_graph.add_edge(edge, weight)
    return graph, nx_graph


def test_conversion(matching_graphs):
    """Test that different backends return the same graph as networkx."""
    graph, nx_graph = matching_graphs
    assert nx.is_isomorphic(graph.to_nx().graph, nx_graph.graph)


def test_matching_has_same_weight(matching_graphs):
    """Test that different backends return matching similar to networkx."""
    graph, nx_graph = matching_graphs
    matching = graph.min_weight_perfect_matching()
    nx_matching = nx_graph.min_weight_perfect_matching()
    assert graph.total_weight_of(matching) == nx_graph.total_weight_of(nx_matching)
    assert len(matching) == len(nx_matching)
    # assert False


# Test parameters
matching_graph_types = [LemonMatchingGraph]
distances = [3, 5]


@pytest.fixture(scope="module", params=it.product(matching_graph_types, distances))
def code_matching_graphs(request):
    """Return a matching graph type built from a surface code with given distance.

    Also return the corresponding NxMatchingGraph for comparison.
    """
    MatchingGraphType, distance = request.param

    code = SurfaceCode(distance=distance, boundaries="open")

    noise = CVLayer(code.graph, p_swap=0.05)
    cv_noise = {"noise": "grn", "delta": 0.1, "sampling_order": "initial"}
    noise.apply_noise(cv_noise)
    noise.measure_hom("p", code.all_syndrome_inds)
    CV_decoder(code, translator=GKP_binner)

    weight_options = {
        "method": "blueprint",
        "integer": True,
        "multiplier": 100,
        "delta": 0.1,
    }
    assign_weights(code, "MWPM", **weight_options)
    nx_code = deepcopy(code)

    graph = MatchingGraphType("primal", code)
    nx_graph = NxMatchingGraph("primal", nx_code)
    return graph, nx_graph


def test_code_matching_conversion(code_matching_graphs):
    """Test that different backends return the same graph as networkx."""
    graph, nx_graph = code_matching_graphs
    assert nx.is_isomorphic(graph.to_nx().graph, nx_graph.graph)


def test_code_matching_has_same_weight(code_matching_graphs):
    """Test that different backends return a matching similar to networkx."""
    graph, nx_graph = code_matching_graphs
    matching = graph.min_weight_perfect_matching()
    nx_matching = nx_graph.min_weight_perfect_matching()
    assert graph.total_weight_of(matching) == nx_graph.total_weight_of(nx_matching)
    assert len(matching) == len(nx_matching)
