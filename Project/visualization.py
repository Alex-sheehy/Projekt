import osmnx as ox
import matplotlib.pylab as plt

def load_node_map():
    """
    Load and visualize the road network map for Skellefteå Kommun.
    """
    place_name = "Skellefteå, Västerbotten, Sweden"
    G = ox.graph_from_place(place_name, network_type='drive')
    fig, ax = ox.plot_graph(G, node_size=1, edge_color='white', edge_linewidth=0.1)
    plt.show()
