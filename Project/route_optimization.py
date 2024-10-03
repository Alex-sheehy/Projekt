import osmnx as ox
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import random

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


def calculate_penalty(unmet_constraints):
    """
    Calculates the total penalty based on unmet constraints.
    """
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
    return sum(PENALTIES.get(constraint, 0) for constraint in unmet_constraints)



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

    num_nodes = len(nodes)

    time_window_categories = [
        (0 * 3600, 2 * 3600),    # 7:00 - 9:00
        (2 * 3600, 4 * 3600),   # 9:00 - 11:00
        (4 * 3600, 6 * 3600),  # 11:00 - 13:00
        (6 * 3600, 8 * 3600),  # 13:00 - 15:00
        (8 * 3600, 10 * 3600),  # 15:00 - 17:00
        (10 * 3600, 12 * 3600),  # 17:00 - 19:00
        (12 * 3600, 14 * 3600)   # 19:00 - 21:00
    ]
    # Initialize the time_windows list
    time_windows = []

    # Assign time windows to each node, kan använda info från brukare_df istället
    for idx in range(num_nodes):
        if idx == depot_index:
            # Time window for the depot (e.g., open all day)
            time_windows.append((0, 15 * 3600))
        else:
            customer_idx = idx - 1  
            category = customer_idx % len(time_window_categories)
            time_window = time_window_categories[category]
            time_windows.append(time_window)

    service_times = [0]

    for i in range(1,num_nodes):
        service_time_minutes = random.randint(20,40)
        service_times.append(service_time_minutes * 60)

    # Append customer service times from brukare_df
    #service_times.extend(brukare_df['ServiceTime'].tolist())

    # Convert service times from minutes to seconds
    #service_times = [time * 60 for time in service_times]

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(time_matrix), num_vehicles, depot_index)

    # Create the routing model
    routing = pywrapcp.RoutingModel(manager)

    # Define the time callback function
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = int(time_matrix[from_node][to_node])
        service_time = int(service_times[from_node])
        return travel_time + service_time

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

    time = "Time"
    routing.AddDimension(
        transit_callback_index,
        2 * 3600,  # allow waiting time 
        15*3600,  # maximum time per vehicle 
        True,  
        time,
    )
    
    time_dimension = routing.GetDimensionOrDie(time)

    # Add time window constraints for each location except depot.

    for location_idx, time_window in enumerate(time_windows):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Add time window constraints for each vehicle start node.
    for vehicle_id in range(num_vehicles):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(
            time_windows[depot_index][0], time_windows[depot_index][1]  #Depot time window
        )

    for i in range(num_vehicles):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i))
        )
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.End(i)))

    def demand_callback(from_index):
        return 1  # Each customer represents a "load" of 1.


    # Add a demand callback to enforce load balancing
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    # Add dimension to keep track of the load (number of nodes visited)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # No slack
        [10] * num_vehicles,  # Maximum capacity for each vehicle (adjust as necessary)
        True,  # Start cumul to zero
        "Load"
    )


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
    


    # Define search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.time_limit.seconds = 120

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)
    def seconds_to_hhmm(seconds):
        """
        Converts seconds to a string in HH:MM format.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"

    if solution:
        total_time = 0  # In seconds
        total_distance = 0  # In meters
        total_travel_time = 0  # In seconds
        total_wait_time = 0  # In seconds
        active_vehicles = 0  # Count of vehicles with actual routes
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            # Check if the vehicle has any customers assigned
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue  # Skip vehicles with no assignments
            active_vehicles += 1
            plan_output = f"--- Route for Vehicle {vehicle_id + 1} ---\n"
            route_distance = 0  # In meters
            route_travel_time = 0  # In seconds
            route_wait_time = 0  # In seconds
            previous_index = index
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                arrival_time = solution.Min(time_var)
                arrival_time_formatted = seconds_to_hhmm(arrival_time)
                service_time = service_times[node_index]
                service_time_hours = service_time / 3600
                # Get time window for the node and convert to HH:MM
                time_window = time_windows[node_index]
                time_window_start_formatted = seconds_to_hhmm(time_window[0])
                time_window_end_formatted = seconds_to_hhmm(time_window[1])
                # Calculate wait time at current node
                if node_index != depot_index:
                    arrival_before_service = arrival_time - service_time
                    wait_time = max(0, time_window[0] - arrival_before_service)
                else:
                    wait_time = 0  # Typically, no wait time at depot
                wait_time_hours = wait_time / 3600
                route_wait_time += wait_time
                # Calculate travel time from previous node to current node
                if previous_index != index:
                    travel_time = time_matrix[manager.IndexToNode(previous_index)][node_index]
                else:
                    travel_time = 0
                travel_time_hours = travel_time / 3600
                route_travel_time += travel_time
                # Get distance from previous node to current node
                distance = distance_matrix[manager.IndexToNode(previous_index)][node_index]
                distance_meters = distance  # Already in meters
                route_distance += distance_meters
                # Append to plan_output
                plan_output += (
                    f"Node {node_index}:\n"
                    f"  Arrival Time      : {arrival_time_formatted} hrs\n"
                    f"  Service Time      : {service_time_hours:.2f} hrs\n"
                    f"  Time Window       : [{time_window_start_formatted}, {time_window_end_formatted}] hrs\n"
                    f"  Travel Time (Prev): {travel_time_hours:.2f} hrs\n"
                    f"  Distance (Prev)   : {distance_meters} m\n"
                    f"  Wait Time         : {wait_time_hours:.2f} hrs\n\n"
                )
                # Move to next node
                previous_index = index
                index = solution.Value(routing.NextVar(index))
            # Handle the end node (return to depot)
            node_index = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)
            arrival_time = solution.Min(time_var)
            arrival_time_formatted = seconds_to_hhmm(arrival_time)
            # Get time window for the depot node and convert to HH:MM
            time_window = time_windows[node_index]
            time_window_start_formatted = seconds_to_hhmm(time_window[0])
            time_window_end_formatted = seconds_to_hhmm(time_window[1])
            # Calculate wait time at depot if necessary (usually zero)
            wait_time = 0
            wait_time_hours = wait_time / 3600
            route_wait_time += wait_time
            # Calculate travel time from previous node to depot
            travel_time = time_matrix[manager.IndexToNode(previous_index)][node_index]
            travel_time_hours = travel_time / 3600
            route_travel_time += travel_time
            # Get distance from previous node to depot
            distance = distance_matrix[manager.IndexToNode(previous_index)][node_index]
            distance_meters = distance  # Already in meters
            route_distance += distance_meters
            # Append to plan_output
            plan_output += (
                f"Node {node_index} (Return to Depot):\n"
                f"  Arrival Time      : {arrival_time_formatted} hrs\n"
                f"  Time Window       : [{time_window_start_formatted}, {time_window_end_formatted}] hrs\n"
                f"  Travel Time (Prev): {travel_time_hours:.2f} hrs\n"
                f"  Distance (Prev)   : {distance_meters} m\n"
                f"  Wait Time         : {wait_time_hours:.2f} hrs\n\n"
            )
            # Calculate total route time in seconds
            route_total_time_seconds = route_travel_time + route_wait_time
            # Append route summary
            route_time_hours = route_total_time_seconds / 3600
            plan_output += (
                f"--- Route Summary for Vehicle {vehicle_id + 1} ---\n"
                f"Total Route Time : {route_time_hours:.2f} hours\n"
                f"Total Distance    : {route_distance:.0f} meters\n"
                f"Total Travel Time : {route_travel_time / 3600:.2f} hours\n"
                f"Total Wait Time   : {route_wait_time / 3600:.2f} hours\n\n"
            )
            print(plan_output)
            # Accumulate totals
            total_time += route_total_time_seconds
            total_distance += route_distance
            total_travel_time += route_travel_time
            total_wait_time += route_wait_time
        # Convert total_time to HH:MM
        total_time_formatted = seconds_to_hhmm(int(total_time))
        print(f"=== Overall Summary ===")
        print(f"Total Active Vehicles  : {active_vehicles}")
        print(f"Total Time of All Routes: {total_time_formatted} hrs")
        print(f"Total Distance of All Routes: {total_distance:.0f} meters")
        # Calculate average speed in km/h
        if total_time > 0:
            average_speed = (total_distance / total_time) * 3.6  # m/s to km/h
            print(f"Average Speed           : {average_speed:.2f} km/h")
        else:
            print("Average Speed           : N/A (No routes found)")
    else:
        print("No solution found!")

