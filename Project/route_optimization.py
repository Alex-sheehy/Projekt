import osmnx as ox
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# Function to generate the time and distance matrix using distance and speed
def generate_matrices(G, customer_locations, depot_location, default_speed_kph=50):
    # Find the nearest nodes for the depot and customer locations
    nearest_nodes = [ox.distance.nearest_nodes(G, lon, lat) for lat, lon in customer_locations]
    depot_node = ox.distance.nearest_nodes(G, depot_location[1], depot_location[0])
    nodes = [depot_node] + nearest_nodes

    time_matrix = []
    distance_matrix = []
    
    for node_u in nodes:
        time_row = []
        distance_row = []
        for node_v in nodes:
            if node_u == node_v:
                time_row.append(0)  # No travel time for the same node
                distance_row.append(0)  # No distance for the same node
            else:
                try:
                    # Find the shortest path between nodes and get the total distance
                    path_length = nx.shortest_path_length(G, source=node_u, target=node_v, weight='length')
                    
                    # Get the edges along the shortest path
                    path_edges = zip(nx.shortest_path(G, source=node_u, target=node_v, weight='length'),
                                     nx.shortest_path(G, source=node_u, target=node_v, weight='length')[1:])
                    
                    # Calculate total time and distance using distance / speed limit for each edge
                    total_time = 0
                    total_distance = 0
                    for u, v in path_edges:
                        edge_data = G.get_edge_data(u, v)[0]
                        distance = edge_data['length']  # Length of the edge in meters
                        speed_kph = edge_data.get('maxspeed', default_speed_kph)  # Speed limit in kph
                        
                        # Handle different cases for speed_kph (convert to float)
                        if isinstance(speed_kph, list):
                            speed_kph = speed_kph[0]  # Take the first value if it's a list
                        try:
                            speed_kph = float(speed_kph)  # Try converting to float
                        except (ValueError, TypeError):
                            # If conversion fails, fallback to default speed
                            speed_kph = default_speed_kph
                        
                        # Convert speed to m/s and calculate time for this edge
                        speed_mps = speed_kph * 1000 / 3600  # Convert kph to m/s
                        time = distance / speed_mps  # Time = distance / speed
                        total_time += time
                        total_distance += distance
                    
                    time_row.append(total_time)
                    distance_row.append(total_distance)
                except nx.NetworkXNoPath:
                    time_row.append(float('inf'))  # If no path exists, set a high penalty time
                    distance_row.append(float('inf'))  # If no path exists, set a high penalty distance
        time_matrix.append(time_row)
        distance_matrix.append(distance_row)

    return time_matrix, distance_matrix, nodes


# Function to determine vehicle compatibility with customer requirements
def vehicle_service_compatibility(vehicle_services, customer_services):
    return all(service in vehicle_services for service in customer_services)

PENALTIES = {
    'license': 100,      # High penalty for lack of license
    'smoker': 10,        # Lower penalty for smoker presence
    'dog': 20,           # Penalty for dogs
    'cat': 20,           # Penalty for cats
    '>18': 50,           # Penalty if employee is not >18
    'man': 70,           # High penalty for gender requirement not met
    'woman': 70,         # High penalty for gender requirement not met
    'medication': 80,    # High penalty for missing medication requirement
    'insulin': 80,       # High penalty for missing insulin requirement
    'stoma': 80,         # High penalty for missing stoma requirement
    'double_staffing': 90, # High penalty for double staffing not met
    'shower': 60,        # Penalty for unmet shower requirements
    'activation': 40     # Penalty for unmet activation requirements
}

def calculate_penalty(unmet_constraints):
    """
    Calculates the total penalty based on unmet constraints.
    """
    return sum(PENALTIES.get(constraint, 0) for constraint in unmet_constraints)



# Main function to perform route optimization
def optimize_routes(brukare_df, medarbetare_df, G, depot_location):
    """
    Optimizes routes for vehicles to visit customers, ensuring proper time windows and vehicle distribution.
    """
    # Generate customer locations from brukare data
    customer_locations = list(zip(brukare_df['Latitude'], brukare_df['Longitude']))
    time_windows = brukare_df['time_windows'].tolist()  # Extract the time windows

    # Generate the time and distance matrices based on distance / speed calculations
    time_matrix, distance_matrix, nodes = generate_matrices(G, customer_locations, depot_location)

    num_vehicles = len(medarbetare_df)
    depot_index = 0

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(time_matrix), num_vehicles, depot_index)

    # Create the routing model
    routing = pywrapcp.RoutingModel(manager)

    # Define the time callback function
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(time_matrix[from_node][to_node])

    # Define the distance callback function
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    # Register the time and distance callbacks
    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    distance_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Set the cost of travel (objective is to minimize total time)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add time window constraints for each location except depot
    time = "Time"
    routing.AddDimension(
        transit_callback_index,
        30,  # allow waiting time
        1440,  # maximum time per vehicle (1440 minutes = 24 hours)
        False,  # Don't force start cumul to zero.
        time,
    )

    time_dimension = routing.GetDimensionOrDie(time)

    # Adjust time windows for each location (offsetting by 480 minutes for an 8:00 start)
    for location_idx, time_window in enumerate(time_windows):
        if location_idx == depot_index:
            continue
        index = manager.NodeToIndex(location_idx)
        start, end = time_window
        adjusted_start = start + 480  # Offset by 480 minutes (8:00 AM)
        adjusted_end = end + 480      # Offset by 480 minutes (start of working day)
        time_dimension.CumulVar(index).SetRange(adjusted_start, adjusted_end)

    # Add time window constraints for each vehicle start node (depot)
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(480, 1320)  # Vehicles can start between 8:00 and 22:00

    # Add capacity constraints to balance work among vehicles
    def demand_callback(from_index):
        # Each customer is counted as 1 unit of demand (adjust as necessary)
        return 1

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    # Set vehicle capacities (assuming each vehicle can visit up to 10 customers)
    vehicle_capacities = [10] * num_vehicles
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,    # Demand callback
        0,                        # No slack
        vehicle_capacities,       # Vehicle capacities
        True,                     # Start cumul to zero
        "Capacity"
    )

    # Define search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.time_limit.seconds = 30

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    # Output the solution if found
    if solution:
        total_time = 0
        total_distance = 0
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            plan_output = f"Route for vehicle {vehicle_id + 1}:\n"
            route_time = 0
            route_distance = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                # Get the time dimension for this node
                time_var = time_dimension.CumulVar(index)
                arrival_time = solution.Min(time_var)
                # Add 8 hours (480 minutes) to display the time correctly
                corrected_time = arrival_time + 480
                plan_output += f" {node_index} (Arrival: {arrival_time // 60}:{arrival_time % 60:02d}) ->"
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_time += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
                route_distance += distance_callback(previous_index, index)
            plan_output += f" {manager.IndexToNode(index)}\n"
            plan_output += f"Time of the route: {route_time} seconds\n"
            plan_output += f"Distance of the route: {route_distance} meters\n"
            print(plan_output)
            total_time += route_time
            total_distance += route_distance
        print(f"Total time of all routes: {total_time} seconds")
        print(f"Total distance of all routes: {total_distance} meters")
        print(f"Average speed: {total_distance/total_time * 3.6}")
    else:
        print("No solution found!")


