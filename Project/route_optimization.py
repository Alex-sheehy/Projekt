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

# Main function to perform route optimization
def optimize_routes(brukare_df, medarbetare_df, G, depot_location):
    """
    Optimizes routes for vehicles to visit customers, calculating travel times and distances dynamically.
    """
    # Generate customer locations from brukare data
    customer_locations = list(zip(brukare_df['Latitude'], brukare_df['Longitude']))
    
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
        time = int(time_matrix[from_node][to_node])
        return time

    # Define the distance callback function
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        distance = int(distance_matrix[from_node][to_node])
        return distance

    # Register the time callback
    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    
    # Register the distance callback (if you need to optimize based on distance)
    distance_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Set the cost of travel (objective is to minimize total time)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Define search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
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
                plan_output += f" {node_index} ->"
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
