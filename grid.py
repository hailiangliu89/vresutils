import networkx as nx
import numpy as np

from vresutils.graph import OrderedGraph

from . import make_toModDir
toModDir = make_toModDir(__file__)

def penalize(x, n):
    """
    Thumb-rule for the aggregation of cross-border power lines.

    Parameters
    ---------
    x : float
        total line capacity
    n : int
        number of power lines

    Returns
    -------
    c : float
        resulting capacity
    """

    if n == 1:
        return x
    elif n == 2:
        return 5./6. * x
    elif n == 3:
        return 4./6. * x
    else:
        return .5 * x

##
# Functions which provide access to special network data
#

def entsoe_tue():
    return OrderedGraph(nx.read_gpickle(toModDir("data/entsoe_2009_final.gpickle")))

def entsoe_tue_linecaps(with_manual_link=True):
    G = entsoe_tue()

    # Add linecapacities by assuming:
    # - number of circuits is always 2
    # - 380kV if any of the connected nodes are 380kV and 220kV else
    # - 380kV lines have a capacity of 1500MW per circuit
    # - 220kV lines have a capacity of 500MW per circuit.

    voltages = nx.get_node_attributes(G, 'voltage')
    for n1, n2, attr in G.edges_iter(data=True):
        voltage = max(voltages.get(n1, 380), voltages.get(n2, 380))
        capacity = 2. * (1.5 if voltage == 380 else 0.5)
        attr.update(voltage=voltage, capacity=capacity)

    # Add missing link
    if with_manual_link:
        length = node_distance(G, '782', '788')
        X = specific_susceptance * length
        G.add_edge('788', '782',
                   capacity=3.0, X=X, Y=1/X,
                   length=length, limit=0.0, voltage=380)

    return G

# Given by bialek's network
# TODO : replace this by a well founded value from oeding or similar
# as soon as we can switch to a scigrid based network
specific_susceptance = 0.00068768296005101493  # mean of X / L

def node_distance(G, n1, n2):
    """
    A distance measure between two nodes in graph `G` which correlates
    well with what is already present in the length edge attribute in
    the bialek grid.

    Arguments
    ---------
    G : nx.Graph
    n1 : node label 1
    n2 : node label 2

    Returns
    -------
    d : float
        distance
    """
    return 110. * np.sqrt(np.sum((G.node[n1]['pos'] - G.node[n2]['pos'])**2))

def heuristically_extend_edge_attributes(G):
    for n1, n2, d in G.edges_iter(data=True):
        d.setdefault('length', node_distance(G, n1, n2))
        d.setdefault('voltage', 380)
        d.setdefault('X', specific_susceptance * d['length'])
        d.setdefault('Y', 1./d['X'])

    return G

def eu():
    return nx.read_gpickle(toModDir("data/EU.gpickle"))

def read_scigrid(nodes_csv="data/vertices_de_power_150601.csv",
                 links_csv="data/links_de_power_150601.csv"):
    """
    Read SCIGrid output csv files into a NX Graph.
    """
    import pandas as pd

    G = OrderedGraph()

    N = pd.read_csv(toModDir(nodes_csv), delimiter=';', index_col=0)
    N['pos'] = [np.asarray(v) for k,v in N.ix[:,['lon', 'lat']].iterrows()]
    G.add_nodes_from(N.iterrows())

    L = pd.read_csv(toModDir(links_csv), delimiter=';', index_col=0)
    # TODO: for some reason the SCIGrid data is missing impedance
    # values for a third of its lines, although L.x / L.length_m is a
    # constant for each voltage level. For now we just extend these to
    # cover the missing ones as well, but we should rather find out
    # the reason for the NaNs.
    L['X'] = (L.x / L.length_m).groupby(L.voltage).fillna(method='ffill') * L.length_m
    L['Y'] = 1./L['X']
    L['length'] = L['length_m']
    L['voltage'] /= 1000  # voltage in kV for readability
    G.add_edges_from(izip(L.v_id_1, L.v_id_2,
                          imap(itemgetter(1),
                               L.loc[:,['voltage', 'cables', 'wires', 'frequency',
                                        'length', 'geom', 'r', 'x', 'c',
                                        'i_th_max', 'X', 'Y']].iterrows())))

    return G