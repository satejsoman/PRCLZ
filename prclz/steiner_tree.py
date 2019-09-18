from itertools import combinations, chain

from networkx.utils import pairwise, not_implemented_for
import networkx as nx
from tqdm import tqdm 

__all__ = ['metric_closure', 'steiner_tree']

# NOTE: this is just source code from networkx, we've copied it here so add progress updates
# SOURCE: https://networkx.github.io/documentation/stable/_modules/networkx/algorithms/approximation/steinertree.html

@not_implemented_for('directed')
def metric_closure(G, weight='weight', verbose=False):
    """  Return the metric closure of a graph.

    The metric closure of a graph *G* is the complete graph in which each edge
    is weighted by the shortest path distance between the nodes in *G* .

    Parameters
    ----------
    G : NetworkX graph

    Returns
    -------
    NetworkX graph
        Metric closure of the graph `G`.

    """
    print("in metric_closure in steiner_tree.py")
    M = nx.Graph()

    Gnodes = set(G)

    # check for connected graph while processing first node
    print("begin dijkistra in metric_closure")
    all_paths_iter = nx.all_pairs_dijkstra(G, weight=weight)
    u, (distance, path) = next(all_paths_iter)
    if Gnodes - set(distance):
        msg = "G is not a connected graph. metric_closure is not defined."
        raise nx.NetworkXError(msg)
    Gnodes.remove(u)

    if verbose:
        print("\nmetric_closure for-loop #1\n")
        for v in tqdm(Gnodes):
            M.add_edge(u, v, distance=distance[v], path=path[v])        
    else:
        for v in Gnodes:
            M.add_edge(u, v, distance=distance[v], path=path[v])

    # first node done -- now process the rest
    if verbose:
        print("\nmetric_closure for-loop #2\n")
        for u, (distance, path) in tqdm(all_paths_iter):
            Gnodes.remove(u)
            for v in Gnodes:
                M.add_edge(u, v, distance=distance[v], path=path[v])

    else:
        for u, (distance, path) in all_paths_iter:
            Gnodes.remove(u)
            for v in Gnodes:
                M.add_edge(u, v, distance=distance[v], path=path[v])

    return M



@not_implemented_for('multigraph')
@not_implemented_for('directed')
def steiner_tree(G, terminal_nodes, weight='weight', verbose=False):
    """ Return an approximation to the minimum Steiner tree of a graph.

    Parameters
    ----------
    G : NetworkX graph

    terminal_nodes : list
         A list of terminal nodes for which minimum steiner tree is
         to be found.

    Returns
    -------
    NetworkX graph
        Approximation to the minimum steiner tree of `G` induced by
        `terminal_nodes` .

    Notes
    -----
    Steiner tree can be approximated by computing the minimum spanning
    tree of the subgraph of the metric closure of the graph induced by the
    terminal nodes, where the metric closure of *G* is the complete graph in
    which each edge is weighted by the shortest path distance between the
    nodes in *G* .
    This algorithm produces a tree whose weight is within a (2 - (2 / t))
    factor of the weight of the optimal Steiner tree where *t* is number of
    terminal nodes.

    """
    # M is the subgraph of the metric closure induced by the terminal nodes of
    # G.
    print("In steiner_tree within steiner_tree.py")
    M = metric_closure(G, weight=weight, verbose=verbose)
    # Use the 'distance' attribute of each edge provided by the metric closure
    # graph.
    H = M.subgraph(terminal_nodes)

    if verbose: print("Begin min span edges")
    mst_edges = nx.minimum_spanning_edges(H, weight='distance', data=True)

    # Create an iterator over each edge in each shortest path; repeats are okay
    if verbose: print("Begin iterator thing")
    edges = chain.from_iterable(pairwise(d['path']) for u, v, d in mst_edges)
    T = G.edge_subgraph(edges)
    return T
