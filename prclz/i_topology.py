import numpy as np 
import igraph 
from itertools import combinations, chain, permutations
from functools import reduce 
import pickle 

def igraph_steiner_tree(G, terminal_vertices, weight='weight'):
    '''
    terminal_nodes is List of igraph.Vertex
    '''

    # Build closed graph of terminal_vertices where each weight is the shortest path distance
    H = PlanarGraph()
    for u,v in combinations(terminal_vertices, 2):
        path_idxs = G.get_shortest_paths(u, v, weights='weight', output='epath')
        path_edges = G.es[path_idxs[0]]
        path_distance = reduce(lambda x,y : x+y, map(lambda x: x['weight'], path_edges))
        kwargs = {'weight':path_distance, 'path':path_idxs[0]}
        H.add_edge(u['name'], v['name'], **kwargs)

    # Now get the MST of that complete graph of only terminal_vertices
    mst_edge_idxs = H.spanning_tree(weights='weight', return_tree=False)

    # Now, we join the paths for all the mst_edge_idxs
    steiner_edge_idxs = list(chain.from_iterable(H.es[i]['path'] for i in mst_edge_idxs))

    return steiner_edge_idxs

def distance(a0, a1):

    if not isinstance(a0, np.ndarray):
        a0 = np.array(a0)
    if not isinstance(a1, np.ndarray):
        a1 = np.array(a1)

    return np.sqrt(np.sum((a0-a1)**2))

def min_distance_from_point_to_line(coords, edge_tuple):
    '''
    Just returns the min distance from the edge to the node

    Inputs:
        - coords (tuple) coordinate pair
        - edge_tuple (tuple of tuples) or coordinate end points defining a line
    '''
    x1,y1 = edge_tuple[0]
    x2,y2 = edge_tuple[1]
    x0,y0 = coords 

    num = np.abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
    den = np.sqrt((y2-y1)**2 + (x2-x1)**2)

    return num/den     

def node_on_edge(edge_tuple, coords):
    '''
    Because line segments are finite, when calculating min distance from edge
    to a point we need to check whether the projection onto the LINE defined by
    the edge is in fact on the edge or outside of it
    
    Inputs:
        - coords (tuple) coordinate pair
        - edge_tuple (tuple of tuples) or coordinate end points defining a line
    '''

    mid_x = (edge_tuple[0][0]+edge_tuple[1][0]) / 2.
    mid_y = (edge_tuple[0][1]+edge_tuple[1][1]) / 2.
    mid_coords = (mid_x, mid_y)

    # NOTE: the distance from the midpoint of the edge to any point on the edge
    #       cannot be greater than the dist to the end points
    np_coords = np.array(coords)
    np_mid_coords = np.array(mid_coords)

    max_distance = distance(np.array(edge_tuple[0]), np_mid_coords)
    qc0 = distance(np_mid_coords, np.array(edge_tuple[0]))
    qc1 = distance(np_mid_coords, np.array(edge_tuple[1]))
    assert np.sum(np.abs(qc0-qc1)) < 10e-4, "NOT TRUE MIDPOINT"

    node_distance = distance(np_coords, np_mid_coords)

    if node_distance > max_distance:
        return False
    else:
        return True 

def vector_projection(edge_tuple, coords):
    '''
    Returns the vector projection of node onto the LINE defined
    by the edge
    https://en.wikipedia.org/wiki/Vector_projection
    https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
    '''
    a_vector = np.array(coords)

    b_vector = np.array(edge_tuple[0]) - np.array(edge_tuple[1])

    b_unit = b_vector / np.linalg.norm(b_vector)

    b_normal = np.array([-b_unit[1], b_unit[0]])

    if not(np.abs(np.sum(b_normal*b_unit)) < 10e-4):
        print()
        print("a_vector = ", a_vector)
        print("b_vector = ", b_vector)
        print("b_normal = ", b_normal)
        print("b_unit = ", b_unit)
        print()

    assert np.abs(np.sum(b_normal*b_unit)) < 10e-4, "b_normal and b_unit are not orthog"

    #min_distance = self.min_distance_to_node(node)
    min_distance = min_distance_from_point_to_line(coords, edge_tuple)

    # Depending on the ordering the +/- can get reversed so this is 
    # just a little hacky workaround to make it 100% robust
    proj1 = a_vector + min_distance * b_normal
    proj2 = a_vector - min_distance * b_normal

    if min_distance_from_point_to_line(proj1, edge_tuple) < 10e-4:
        return (proj1[0], proj1[1])
    elif min_distance_from_point_to_line(proj2, edge_tuple) < 10e-4:
        return (proj2[0], proj2[1])
    else:
        assert False, "Vector projection failed"


class PlanarGraph(igraph.Graph):
    def __init__(self):
        super().__init__()

    @staticmethod
    def from_edges(edges):
        graph = PlanarGraph()
        for edge in edges:
            graph.add_edge(edge)
        return graph


    @staticmethod
    def load_planar(file_path):
        '''
        Loads a planar graph from a saved via
        '''

        with open(file_path, 'rb') as file:
            graph = pickle.load(file)
        #graph = igraph.Graph.Read_Pickle(file_path)
        return graph

    def save_planar(self, file_path):
        '''
        Saves planar graph to file via pickle 
        '''

        with open(file_path, 'wb') as file:
            pickle.dump(self, file)
        #super().write_pickle(file_path)

    def add_node(self, coords, terminal=False):
        '''
        Adds coords to the graph but checks if coords are already in
        graph
        '''

        if len(self.vs) == 0:
            self.add_vertex(name=coords, terminal=terminal)
        else:
            seq = self.vs.select(name=coords)
            if len(seq) == 0:
                self.add_vertex(name=coords, terminal=terminal)
            elif len(seq) == 1:
                seq[0]['terminal'] = terminal 
            elif len(seq) > 1:
                assert False, "Hacky error - there are duplicate nodes in graph"

    def add_edge(self, coords0, coords1, terminal0=False, terminal1=False, **kwargs):
        '''
        Adds edge to the graph but checks if edge already exists. Also, if either
        coords is not already in the graph, it adds them
        '''

        # Safely add nodes
        self.add_node(coords0, terminal0)
        self.add_node(coords1, terminal1)

        v0 = self.vs.select(name=coords0)
        v1 = self.vs.select(name=coords1)

        # Safely add edge after checking whether edge exists already
        edge_seq = self.es.select(_between=(v0, v1))
        if len(edge_seq) == 0:
            kwargs['steiner'] = False
            if "weight" not in kwargs.keys():
                kwargs['weight'] = distance(coords0, coords1)
            super().add_edge(v0[0], v1[0], **kwargs)


    def split_edge_by_node(self, edge_tuple, coords, terminal=False):
        '''
        Given an existing edge btwn 2 nodes, and a third unconnected node, 
        replaces the existing edge with 2 new edges with the previously
        unconnected node between the two
        NOTE: if the new node is already one of the edges, we do not create a self-edge

        Inputs:
            - edge_tuple: two coord pairs ex. [(0,1), (1,1)]
            - coords: coord pair ex. (2,2)
        '''
        orig_coords0, orig_coords1 = edge_tuple
        if coords == orig_coords0:
            self.vs.select(name=orig_coords0)['terminal'] = terminal
        elif coords == orig_coords1:
            self.vs.select(name=orig_coords1)['terminal'] = terminal
        else:
            orig_vtx0 = self.vs.select(name=orig_coords0)
            orig_vtx1 = self.vs.select(name=orig_coords1)
            assert len(orig_vtx0) == 1, "Found {} vertices in orig_vtx0".format(len(orig_vtx0))
            assert len(orig_vtx1) == 1, "Found {} vertices in orig_vtx1".format(len(orig_vtx1))
            edge_seq = self.es.select(_between=(orig_vtx0, orig_vtx1))
            super().delete_edges(edge_seq)

            self.add_edge(orig_coords0, coords, terminal1=terminal)
            self.add_edge(coords, orig_coords1, terminal0=terminal)

########################################################################
########################################################################
    @staticmethod
    def closest_point_to_node(edge_tuple, coords):
        '''
        The edge_tuple specifies an edge and this returns the point on that
        line segment closest to 
        '''

        projected_node = vector_projection(edge_tuple, coords)
        if node_on_edge(edge_tuple, projected_node):
            return projected_node
        else:
            dist_node0 = distance(edge_tuple[0], coords)
            dist_node1 = distance(edge_tuple[1], coords)
            if dist_node0 <= dist_node1:
                return edge_tuple[0]
            else:
                return edge_tuple[1]

    def edge_to_coords(self, edge):
        '''
        Given an edge, returns the edge_tuple of
        the corresponding coordinates
        '''
        v0_idx, v1_idx = edge.tuple 
        v0_coords = self.vs[v0_idx]['name']
        v1_coords = self.vs[v1_idx]['name']
        edge_tuple = (v0_coords, v1_coords)

        return edge_tuple 

########################################################################
########################################################################
    def add_node_to_closest_edge(self, coords, terminal=False):
        '''
        Given the input node, this finds the closest point on each edge to that input node.
        It then adds that closest node to the graph. It splits the argmin edge into two
        corresponding edges so the new node is fully connected
        '''
        closest_edge_nodes = []
        closest_edge_distances = []

        for edge in self.es:

            edge_tuple = self.edge_to_coords(edge)

            #Skip self-edges
            if edge.is_loop():
                #print("\nSKIPPING EDGE BC ITS A SELF-EDGE\n")
                continue 

            closest_node = PlanarGraph.closest_point_to_node(edge_tuple, coords)
            closest_distance = distance(closest_node, coords)

            closest_edge_nodes.append(closest_node)
            closest_edge_distances.append(closest_distance)

        argmin = np.argmin(closest_edge_distances)
        closest_node = closest_edge_nodes[argmin]
        closest_edge = self.edge_to_coords(self.es[argmin])

        # Now add it
        self.split_edge_by_node(closest_edge, closest_node, terminal=terminal)

    def steiner_tree_approx(self, verbose=False):
        '''
        All Nodes within the graph have an attribute, Node.terminal, which is a boolean
        denoting whether they should be included in the set of terminal_nodes which
        are connected by the Steiner Tree approximation
        '''
        terminal_nodes = self.vs.select(terminal_eq=True)

        steiner_edge_idxs = igraph_steiner_tree(self, terminal_nodes)
        for i in steiner_edge_idxs:
            self.es[i]['steiner'] = True 


    def plot_reblock(self, output_file):
        
        vtx_color_map = {True: 'red', False: 'blue'}
        edg_color_map = {True: 'red', False: 'blue'}
        visual_style = {}
        visual_style['vertex_color'] = [vtx_color_map[t] for t in self.vs['terminal'] ]
        visual_style['edge_color'] = [edg_color_map[t] for t in self.es['steiner'] ]
        visual_style['layout'] = self.vs['name']
        visual_style['vertex_label'] = [str(x) for x in self.vs['name']]

        igraph.plot(self, output_file, **visual_style)

 
