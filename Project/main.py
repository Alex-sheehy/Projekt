from data_processing import (
    ladda_data,
    rensa_brukar_data,
    rensa_medarb_data,
    read_addresses,
    assign_addresses_to_brukare,
)
from route_creation import (
    skapa_brukare_dict,
    skapa_medarbetare_dict,
    create_weekly_dict,
)
from route_optimization import generate_distance_matrix, optimize_routes
from schedule_optimization import optimize_schedule
from shift_assignment import assign_shifts
import osmnx as ox

def main():
    # Load and clean data
    data = ladda_data("Project/data/Studentuppgift fiktiv planering.xlsx")
    brukare_df = rensa_brukar_data(data["brukare"])
    medarbetare_df = rensa_medarb_data(data["medarbetare"])

    # Assign addresses to brukare
    addresses = read_addresses("Project/data/addresser.txt")
    brukare_df = assign_addresses_to_brukare(brukare_df, addresses)

    # Define time periods and corresponding regex patterns
    tidsperioder = ["Morgon", "Förmiddag", "Lunch", "Eftermiddag", "Middag", "Tidig kväll", "Sen kväll"]
    regex_mönster = [
        r"\b[mM]org\b", r"\b[fF]m\b", r"\b[lL]unch\b", r"\b[eE]m\b",
        r"\b[mM]iddag\b", r"\b[tT]idig kväll\b", r"\b[sS]en kväll\b"
    ]

    # Create dictionaries for brukare and medarbetare schedules
    brukare_dag_dict = skapa_brukare_dict(brukare_df, tidsperioder, regex_mönster)
    medarbetare_dag_dict = skapa_medarbetare_dict(medarbetare_df, tidsperioder, regex_mönster)
    vecko_dict = create_weekly_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict)

    # Create a route graph for distance calculations
    place_name = "Skellefteå, Sweden"
    G = ox.graph_from_place(place_name, network_type="drive")
    G = ox.truncate.largest_component(G, strongly=True)
    depot_location = (64.754, 21.046)  # Example depot coordinates
    customer_locations = list(zip(brukare_df["Latitude"], brukare_df["Longitude"]))
    distance_matrix, nodes = generate_distance_matrix(G, customer_locations, depot_location)

    # Optimize routes for medarbetare
    optimized_routes = optimize_routes(brukare_df, medarbetare_df, G, depot_location)

    # Optimize the schedule
    initial_schedule = optimize_schedule(
        brukare_df, medarbetare_df, distance_matrix, brukare_dag_dict
    )

    # Assign shifts based on the optimized schedule
    final_schedule = assign_shifts(initial_schedule, medarbetare_df, brukare_dag_dict)

    # Display the final schedule
    print("\n=== Final Schedule ===")
    print(final_schedule)

if __name__ == "__main__":
    main()
