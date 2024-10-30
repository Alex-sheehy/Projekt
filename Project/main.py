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

    coordinates_df = pd.read_excel("Project/data/Studentuppgift fiktiv planering.xlsx", "Koordinater", header=None)
    coordinates = np.asarray(coordinates_df.iloc[:,1])



    dag = input("Ange dag för schema: ")

    dag = dag.title()

    brukare_dag_df = dataframe_creation(dag) 

    fm_tidsfönster = ["Morgon", "Förmiddag", "Lunch", "Eftermiddag"]
    em_tidsfönster = ["Middag", "Tidig kväll", "Sen kväll"]

    fm_df = brukare_dag_df[brukare_dag_df["Tidsfönster"].apply(lambda x: x[0] in fm_tidsfönster)]
    fm_df = fm_df.reset_index(drop=True)
    em_df = brukare_dag_df[brukare_dag_df["Tidsfönster"].apply(lambda x: x[0] in em_tidsfönster)]
    em_df = em_df.reset_index(drop=True)


    # Create a graph for route optimization using OSMnx
    place_name = "Skellefteå, Sweden"
    G = ox.graph_from_bbox(bbox=coordinates, network_type='drive');
    G = ox.utils_graph.truncate.largest_component(G, strongly=True);

    depot_location = (64.71128317136987, 21.16924807421642)
    temp_index = len(brukare_dag_df) // 2

    fm_df.to_excel("fm.xlsx", index=False)
    em_df.to_excel("em.xlsx", index=False)

    antal_medarbetare = len(medarbetare_df)
    shift_start = 15
    shift_end = 22
    optimize_routes(em_df, medarbetare_df, G, depot_location, antal_medarbetare, shift_start, shift_end)
    ox.plot_graph(G)
if __name__ == '__main__':
    main()