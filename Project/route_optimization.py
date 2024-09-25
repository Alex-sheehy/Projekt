import osmnx as ox
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

# Function to generate the distance matrix
def generate_distance_matrix(G, customer_locations, depot_location):
    nearest_nodes = [ox.distance.nearest_nodes(G, lon, lat) for lat, lon in customer_locations]
    depot_node = ox.distance.nearest_nodes(G, depot_location[1], depot_location[0])
    nodes = [depot_node] + nearest_nodes

    distance_matrix = []
    for node_u in nodes:
        row = []
        for node_v in nodes:
            try:
                # Try to find the shortest path length, otherwise assign a high penalty value
                length = nx.shortest_path_length(G, source=node_u, target=node_v, weight='length')
            except nx.NetworkXNoPath:
                length = float('inf')  # Represent an unreachable path
            row.append(length)
        distance_matrix.append(row)

    return distance_matrix, nodes


# Penalty values for unmet constraints
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

# Function to calculate penalty based on unmet constraints
def calculate_penalty(unmet_constraints):
    """
    Calculates the total penalty based on unmet constraints.
    """
    return sum(PENALTIES.get(constraint, 0) for constraint in unmet_constraints)

# Function to determine vehicle compatibility with customer requirements
def vehicle_service_compatibility(vehicle_services, customer_services):
    """
    Checks if a vehicle can serve a customer based on service requirements.
    """
    return all(service in vehicle_services for service in customer_services)

# Main function to perform route optimization
def optimize_routes(brukare_df, medarbetare_df, G, depot_location):
    """
    Optimizes routes for medarbetare to visit brukare considering constraints and penalties.
    """
    # Extract customer locations from brukare data
    customer_locations = list(zip(brukare_df['Latitude'], brukare_df['Longitude']))

    # Generate the distance matrix
    distance_matrix, nodes = generate_distance_matrix(G, customer_locations, depot_location)

    # Define the number of vehicles and the depot index
    num_vehicles = len(medarbetare_df)
    depot_index = 0  # First node is the depot

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot_index)

    # Create the routing model
    routing = pywrapcp.RoutingModel(manager)

    # Define distance callback function
    def distance_callback(from_index, to_index):
        """Returns the distance between two nodes."""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    # Register the distance callback
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Set the cost of travel (objective is to minimize the total distance)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Apply constraints based on customer and vehicle capabilities
    for node_index in range(1, len(customer_locations) + 1):
        customer_id = node_index  # Assuming customer IDs start from 1
        allowed_vehicles = []
        unmet_constraints = []

        # Retrieve the specific constraints from brukare (example logic)
        customer_services = brukare_df.loc[node_index - 1, 'Constraints'].split(',')  # Example: "medication,smoker"
        
        # Check compatibility for each vehicle
        for vehicle_id in range(num_vehicles):
            vehicle_services = medarbetare_df.loc[vehicle_id, 'Capabilities'].split(',')  # Example: "medication,license"
            
            if vehicle_service_compatibility(vehicle_services, customer_services):
                allowed_vehicles.append(vehicle_id)
            else:
                unmet_constraints = [service for service in customer_services if service not in vehicle_services]

        # Apply penalties if no vehicles can fully serve the customer
        if not allowed_vehicles:
            penalty = calculate_penalty(unmet_constraints)
            routing.AddDisjunction([manager.NodeToIndex(node_index)], penalty)
        else:
            # Set allowed vehicles for this customer node
            routing.VehicleVar(manager.NodeToIndex(node_index)).SetValues(allowed_vehicles)

    # Optional: Add a dimension to limit the number of stops for each vehicle
    max_stops = 10  # Example limit on stops per vehicle
    stops_per_vehicle = [max_stops] * num_vehicles
    demand_evaluator_index = routing.RegisterUnaryTransitCallback(lambda index: 1)

    routing.AddDimensionWithVehicleCapacity(
        demand_evaluator_index,
        0,  # No slack
        stops_per_vehicle,  # Vehicle capacities
        True,  # Start cumul to zero
        "Stops"
    )

    # Define search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = 30  # Set a time limit for the solver

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    # Output the solution if found
    if solution:
        total_distance = 0
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            plan_output = f"Route for vehicle {vehicle_id + 1}:\n"
            route_distance = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                plan_output += f" {node_index} ->"
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
            plan_output += f" {manager.IndexToNode(index)}\n"
            plan_output += f"Distance of the route: {route_distance} meters\n"
            print(plan_output)
            total_distance += route_distance
        print(f"Total distance of all routes: {total_distance} meters")
    else:
        print("No solution found!")
