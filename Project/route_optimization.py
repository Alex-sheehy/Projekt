import osmnx as ox
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import numpy as np
import os
import random



def save_matrices(time_matrix, distance_matrix, nodes, time_file="time_matrix.npy", distance_file="distance_matrix.npy", nodes_file="nodes.npy"):
    np.save(time_file, time_matrix)
    np.save(distance_file, distance_matrix)
    np.save(nodes_file, nodes)

def load_matrices(time_file="time_matrix.npy", distance_file="distance_matrix.npy", nodes_file="nodes.npy"):
    time_matrix = np.load(time_file)
    distance_matrix = np.load(distance_file)
    nodes = np.load(nodes_file)
    return time_matrix, distance_matrix, nodes



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
                        total_time += time * 1.20
                        total_distance += distance
                    
                    time_row.append(total_time + 2 * 60)
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
        'license': 1000,      # High penalty for lack of license
        'smoker': 100,        # Lower penalty for smoker presence
        'dog': 200,           # Penalty for dogs
        'cat': 200,           # Penalty for cats
        '>18': 5000,           # Penalty if employee is not >18
        'man': 7000,           # High penalty for gender requirement not met
        'woman': 7000,         # High penalty for gender requirement not met
        'medication': 8000,    # High penalty for missing medication requirement
        'insulin': 8000,       # High penalty for missing insulin requirement
        'stoma': 800,         # High penalty for missing stoma requirement
        'double_staffing': 900, # High penalty for double staffing not met
        'shower': 600,        # Penalty for unmet shower requirements
        'activation': 400     # Penalty for unmet activation requirements
    }
    return sum(PENALTIES.get(constraint, 0) for constraint in unmet_constraints)



# Main function to perform route optimization
def optimize_routes(brukare_df, medarbetare_df, G, depot_location, antal_medarbetare, time_file="time_matrix.npy", distance_file="distance_matrix.npy", nodes_file="nodes.npy"):
    """
        if os.path.exists(time_file) and os.path.exists(distance_file) and os.path.exists(nodes_file):
            # Load the saved matrices and nodes using numpy
            time_matrix, distance_matrix, nodes = load_matrices(time_file, distance_file, nodes_file)
            print("Loaded matrices from file.")

            customer_locations = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in nodes[1:]]

        else:
            # Generate customer locations
            customer_locations = list(zip(brukare_df['Latitude'].astype("float"), brukare_df['Longitude'].astype("float")))

            # Generate matrices (this is computationally expensive)
            time_matrix, distance_matrix, nodes = generate_matrices(G, customer_locations, depot_location)

            # Save the matrices for future runs
            save_matrices(time_matrix, distance_matrix, nodes, time_file, distance_file, nodes_file)
            print("Generated and saved matrices.")
    """

    customer_locations = list(zip(brukare_df['Latitude'].astype("float"), brukare_df['Longitude'].astype("float")))

    # Generate matrices (this is computationally expensive)
    time_matrix, distance_matrix, nodes = generate_matrices(G, customer_locations, depot_location)

    num_vehicles = antal_medarbetare
    depot_index = 0

    num_nodes = len(nodes)

    # Initialize the time_windows list
    temp = brukare_df["Tidsfönster"].values
    time_windows = [ ((int(thing[1].split("-")[0])-7) * 3600, (int(thing[1].split("-")[1])-7) * 3600) for thing in temp]
    time_windows.insert(0, (0, 15 * 3600))


    service_times = [0]

    for i in range(1, num_nodes):
        service_times.append(int(brukare_df["Tid"].iloc[i-1]) * 60)

    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(time_matrix), num_vehicles, depot_index)

    # Create the routing model
    routing = pywrapcp.RoutingModel(manager)

    # Set a fixed cost for using each vehicle
    vehicle_fixed_cost = 10000  # Adjust this value as needed

    for vehicle_id in range(num_vehicles):
        routing.SetFixedCostOfVehicle(vehicle_fixed_cost, vehicle_id)

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


    time = "Time"
    routing.AddDimension(
        transit_callback_index,
        int(3600),  # allow waiting time 
        15*3600,  # maximum time per vehicle 
        True,  
        time,
    )
    
    time_dimension = routing.GetDimensionOrDie(time)
    
    # Set a coefficient for the global span to minimize total route time
    time_dimension.SetGlobalSpanCostCoefficient(1)  # Adjust the coefficient as needed
   
    # Add time window constraints for each location except depot.
    for location_idx, time_window in enumerate(time_windows):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

        # Penalize arriving before the start of the time window
        penalty_amount = 1  # Penalty for each unit (e.g., seconds) of early arrival
        time_dimension.SetCumulVarSoftLowerBound(index, time_window[0], penalty_amount)

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
    stops_per_vehicle = 20
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # No slack
        [stops_per_vehicle] * num_vehicles,  # Maximum capacity for each vehicle (adjust as necessary)
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
            print(f"{brukare_df['Individ'].iloc[node_index-1]} has unmet constraints {unmet_constraints}")
            routing.AddDisjunction([manager.NodeToIndex(node_index)], penalty)
        else:
            # Set allowed vehicles for this customer node
            routing.VehicleVar(manager.NodeToIndex(node_index)).SetValues(allowed_vehicles)
    
    # Set the cost of travel (objective is to minimize total time)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Define search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH
    search_parameters.time_limit.seconds = 600  # Increase time limit to 5 minutes
    search_parameters.log_search = True

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    def seconds_to_hhmm(seconds, shift=False):
        """
        Converts seconds to a string in HH:MM format.
        If shift is True, adds a 7-hour shift to the time.
        """
        if shift:
            total_seconds = seconds + 7 * 3600  # Shift by 7 hours
        else:
            total_seconds = seconds
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"

    # Initialize an output string to collect the printouts
    output_string = ""

    if solution:
        total_time = 0  # In seconds
        total_distance = 0  # In meters
        total_travel_time = 0  # In seconds
        total_wait_time = 0  # In seconds
        total_service_time = 0  # In seconds
        active_vehicles = 0  # Count of vehicles with actual routes

        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            if routing.IsEnd(solution.Value(routing.NextVar(index))):
                continue  # Skip vehicles with no assignments
            active_vehicles += 1
            plan_output = f"--- Route for Vehicle {vehicle_id + 1} ---\n"
            route_distance = 0  # In meters
            route_travel_time = 0  # In seconds
            route_wait_time = 0  # In seconds
            route_service_time = 0  # In seconds

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                arrival_time = solution.Value(time_var)
                service_time = service_times[node_index]
                time_window = time_windows[node_index]

                if node_index == 0:
                    individ_name = "Depot"
                else:
                    individ_name = brukare_df['Individ'].iloc[node_index-1]

                plan_output += f" {individ_name}:\n"
                plan_output += f"  Arrival Time      : {seconds_to_hhmm(arrival_time, shift=True)}\n"

                next_index = solution.Value(routing.NextVar(index))

                if not routing.IsEnd(next_index):
                    next_node_index = manager.IndexToNode(next_index)
                    arrival_time_next = solution.Value(time_dimension.CumulVar(next_index))
                    travel_time_matrix = time_matrix[node_index][next_node_index]

                    # Calculate departure time based on next arrival time minus travel time
                    departure_time = arrival_time_next - travel_time_matrix

                    # Ensure departure time is not before service completion
                    earliest_departure = arrival_time + service_time
                    if departure_time < earliest_departure:
                        departure_time = earliest_departure

                    # Calculate wait time
                    wait_time = departure_time - earliest_departure

                    # Travel time to next node
                    travel_time = arrival_time_next - departure_time

                    # Accumulate times
                    route_travel_time += travel_time
                    route_wait_time += wait_time
                    route_service_time += service_time

                    # Distance between current node and next node
                    distance = distance_matrix[node_index][next_node_index]
                    route_distance += distance

                    # Time window formatting
                    time_window_start_formatted = seconds_to_hhmm(time_window[0], shift=True)
                    time_window_end_formatted = seconds_to_hhmm(time_window[1], shift=True)

                    # Append to plan_output
                    plan_output += (
                        f"  Departure Time    : {seconds_to_hhmm(departure_time, shift=True)}\n"
                        f"  Service Time      : {seconds_to_hhmm(service_time)}\n"
                        f"  Time Window       : [{time_window_start_formatted}, {time_window_end_formatted}]\n"
                        f"  Travel Time (to next): {seconds_to_hhmm(travel_time)}\n"
                        f"  Distance (to next)   : {distance:.2f} m\n"
                        f"  Wait Time         : {seconds_to_hhmm(wait_time)}\n\n"
                    )

                else:
                    # At the last node (depot), no next node
                    departure_time = arrival_time + service_time
                    wait_time = 0
                    route_service_time += service_time

                    time_window_start_formatted = seconds_to_hhmm(time_window[0], shift=True)
                    time_window_end_formatted = seconds_to_hhmm(time_window[1], shift=True)

                    plan_output += (
                        f"  Departure Time    : {seconds_to_hhmm(departure_time, shift=True)}\n"
                        f"  Service Time      : {seconds_to_hhmm(service_time)}\n"
                        f"  Time Window       : [{time_window_start_formatted}, {time_window_end_formatted}]\n"
                        f"  Wait Time         : {seconds_to_hhmm(wait_time)}\n\n"
                    )

                index = next_index

            # Compute total route time
            route_total_time_seconds = route_travel_time + route_wait_time + route_service_time

            plan_output += (
                f"--- Route Summary for Vehicle {vehicle_id + 1} ---\n"
                f"Total Route Time : {seconds_to_hhmm(route_total_time_seconds)}\n"
                f"Total Distance    : {route_distance:.0f} meters\n"
                f"Total Travel Time : {seconds_to_hhmm(route_travel_time)}\n"
                f"Total Wait Time   : {seconds_to_hhmm(route_wait_time)}\n"
                f"Total Service Time: {seconds_to_hhmm(route_service_time)}\n\n"
            )
            # Append to the output string instead of printing
            output_string += plan_output

            # Accumulate totals
            total_time += route_total_time_seconds
            total_distance += route_distance
            total_travel_time += route_travel_time
            total_wait_time += route_wait_time
            total_service_time += route_service_time

        # Overall summary
        overall_summary = f"=== Overall Summary ===\n"
        overall_summary += f"Total Active Vehicles  : {active_vehicles}\n"
        overall_summary += f"Total Time of All Routes: {seconds_to_hhmm(total_time)}\n"
        overall_summary += f"Total Distance of All Routes: {total_distance:.0f} meters\n"
        overall_summary += f"Total Travel Time       : {seconds_to_hhmm(total_travel_time)}\n"
        overall_summary += f"Total Wait Time         : {seconds_to_hhmm(total_wait_time)}\n"
        overall_summary += f"Total Service Time      : {seconds_to_hhmm(total_service_time)}\n"
        # Calculate average speed
        if total_travel_time > 0:
            average_speed = (total_distance / total_travel_time) * 3.6  # m/s to km/h
            overall_summary += f"Average Speed           : {average_speed:.2f} km/h\n"
        else:
            overall_summary += "Average Speed           : N/A (No routes found)\n"

        # Append overall summary to the output string
        output_string += overall_summary
    else:
        output_string += "No solution found!\n"

    # Print the output_string to the console (optional)
    print(output_string)
    
    # Write the output_string to a text file
    with open('route_output.txt', 'w') as f:
        f.write(output_string)

