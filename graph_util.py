"""Contains utility functions"""
import inspect
import random
import sys
from typing import Callable
import torch
from skimage.color import hsv2rgb as sk_hsv2rgb
import numpy as np
try:
    import activation_functions as af
    import fitness_functions as ff
except ModuleNotFoundError:
    import cppn_neat.fitness_functions as ff
    import cppn_neat.activation_functions as af


def is_valid_connection(nodes, key:tuple, config):
    """
    Checks if a connection is valid.
    params:
        from_node: The node from which the connection originates.
        to_node: The node to which the connection connects.
        config: The settings to check against
    returns:
        True if the connection is valid, False otherwise.
    """
    from_node, to_node = key
    from_node, to_node = nodes[from_node], nodes[to_node]
    
    if from_node.layer == to_node.layer:
        return False  # don't allow two nodes on the same layer to connect

    if not config.allow_recurrent and from_node.layer > to_node.layer:
        return False  # invalid

    return True


def name_to_fn(name) -> callable:
    """
    Converts a string to a function.
    params:
        name: The name of the function.
    returns:
        The function.
    """
    if isinstance(name, (Callable,)) or name is None:
        return name
    assert isinstance(name, str), f"name must be a string but is {type(name)}"
    if name == "":
        return None
    fns = inspect.getmembers(sys.modules[af.__name__])
    fns.extend(inspect.getmembers(sys.modules[ff.__name__]))
    return fns[[f[0] for f in fns].index(name)][1]


def choose_random_function(config) -> callable:
    """Chooses a random activation function from the activation function module."""
    random_fn = random.choice(config.activations)
    return random_fn


def get_disjoint_connections(this_cxs, other_innovation):
    """returns connections in this_cxs that do not share an innovation number with a
        connection in other_innovation"""
    if(len(this_cxs) == 0 or len(other_innovation) == 0):
        return []
    return [t_cx for t_cx in this_cxs if\
        (t_cx.key not in other_innovation and t_cx.key < other_innovation[-1])]


def get_excess_connections(this_cxs, other_innovation):
    """returns connections in this_cxs that share an innovation number with a
        connection in other_innovation"""
    if(len(this_cxs) == 0 or len(other_innovation) == 0):
        return []
    return [t_cx for t_cx in this_cxs if\
            (t_cx.key not in other_innovation and t_cx.key > other_innovation[-1])]


def get_matching_connections(cxs_1, cxs_2):
    """returns connections in cxs_1 that share an innovation number with a connection in cxs_2
       and     connections in cxs_2 that share an innovation number with a connection in cxs_1"""

    return sorted([c1 for c1 in cxs_1 if c1.key in [c2.key for c2 in cxs_2]],
                    key=lambda x: x.key),\
                    sorted([c2 for c2 in cxs_2 if c2.key in [c1.key for c1 in cxs_1]],
                    key=lambda x: x.key)


def find_node_with_id(nodes, node_id):
    """Returns the node with the given id from the list of nodes"""
    return nodes[node_id]
    # for node in nodes:
    #     if node.id == node_id:
    #         return node
    # return None

def find_cx_with_innovation(cxs, innovation):
    """Returns the node with the given id from the list of nodes"""
    for cx in cxs:
        if cx.key == innovation:
            return cx
    return None


def get_ids_from_individual(individual):
    """Gets the ids from a given individual

    Args:
        individual (CPPN): The individual to get the ids from.

    Returns:
        tuple: (inputs, outputs, connections) the ids of the CPPN's nodes
    """
    inputs = list(individual.input_nodes().keys())
    outputs = list(individual.output_nodes().keys())
    connections = [c.key
                #    for c in individual.enabled_connections()]
                   for c in individual.connection_genome.values()]
    return inputs, outputs, connections


def get_candidate_nodes(s, connections):
    """Find candidate nodes c for the next layer.  These nodes should connect
    a node in s to a node not in s."""
    return set(b for (a, b) in connections if a in s and b not in s)


def get_incoming_connections(individual, node):
    """Given an individual and a node, returns the connections in individual that end at the node"""
    return list(filter(lambda x, n=node: x.key[1] == n.id,
               individual.enabled_connections()))  # cxs that end here



def hsv2rgb(hsv):
    return torch.tensor(sk_hsv2rgb(hsv))
      


# Functions below are modified from other packages
# This is necessary because AWS Lambda has strict space limits,
# and we only need a few methods, not the entire packages.

###############################################################################################
# Functions below are from the NEAT-Python package https://github.com/CodeReclaimers/neat-python/

# LICENSE:
# Copyright (c) 2007-2011, cesar.gomes and mirrorballu2
# Copyright (c) 2015-2019, CodeReclaimers, LLC
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of
# conditions and the following
# disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list
# of conditions and the following
# disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be
# used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS
# OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
# OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################################


def required_for_output(inputs, outputs, connections):
    """
    Collect the nodes whose state is required to compute the final network output(s).
    :param inputs: list of the input identifiers
    :param outputs: list of the output node identifiers
    :param connections: list of (input, output) connections in the network.
    NOTE: It is assumed that the input identifier set and the node identifier set are disjoint.
    By convention, the output node ids are always the same as the output index.

    Returns a set of identifiers of required nodes.
    From: https://neat-python.readthedocs.io/en/latest/_modules/graphs.html
    """

    required = set(outputs) # outputs always required
    s = set(outputs)
    while 1:
        # Find nodes not in S whose output is consumed by a node in s.
        t = set(a for (a, b) in connections if b in s and a not in s)

        if not t:
            break

        layer_nodes = set(x for x in t if x not in inputs)
        if not layer_nodes:
            break

        required = required.union(layer_nodes)
        s = s.union(t)

    return required


def feed_forward_layers(individual):
    """
    Collect the layers whose members can be evaluated in parallel in a feed-forward network.
    :param inputs: list of the network input nodes
    :param outputs: list of the output node identifiers
    :param connections: list of (input, output) connections in the network.

    Returns a list of layers, with each layer consisting of a set of node identifiers.
    Note that the returned layers do not contain nodes whose output is ultimately
    never used to compute the final network output.

    Modified from: https://neat-python.readthedocs.io/en/latest/_modules/graphs.html
    """

    inputs, outputs, connections = get_ids_from_individual(individual)
    required = required_for_output(inputs, outputs, connections)

    layers = []
    s = set(inputs)
    while 1:

        c = get_candidate_nodes(s, connections)
        # Keep only the used nodes whose entire input set is contained in s.
        t = set()
        for n in c:
            if n in required and all(a in s for (a, b) in connections if b == n):
                t.add(n)
        if not t:
            break

        layers.append(t)
        s = s.union(t)
    return layers


