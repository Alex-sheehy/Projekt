from data_processing import ladda_data, rensa_brukar_data, rensa_medarb_data, read_addresses, assign_addresses_to_brukare
from route_creation import skapa_brukare_dict, skapa_medarbetare_dict, create_weekly_dict
from utils import check_visits
from dataframe_creation import dataframe_creation
from route_optimization import *  # Import the optimize_routes function
import osmnx as ox  # Ensure OSMnx is available for graph creation
import pandas as pd

def main():
    # Load data from Excel file
    data = ladda_data("Project/data/Studentuppgift fiktiv planering.xlsx")
    
    medarbetare_df = rensa_medarb_data(data["medarbetare"])


    brukare_dag_df = dataframe_creation("Måndag") 

    # Create a graph for route optimization using OSMnx
    place_name = "Skellefteå, Sweden"
    coordinates = (64.8402, 64.6462, 21.3169, 20.8486)
    G = ox.graph_from_bbox(bbox=coordinates, network_type='drive');
    G = ox.utils_graph.truncate.largest_component(G, strongly=True);

    depot_location = (64.71128317136987, 21.16924807421642)

    antal_medarbetare = 25

    # Perform route optimization based on the provided brukare and medarbetare data
    optimize_routes(brukare_dag_df, medarbetare_df, G, depot_location, antal_medarbetare)
    print(brukare_dag_df)
if __name__ == '__main__':
    main()