import osmnx as ox
import networkx as nx
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def generate_distance_matrix(G, customer_locations, depot_location):
    """
    Generate the distance matrix for route optimization.
    """
    nearest_nodes = [ox.distance.nearest_nodes(G, lon, lat) for lat, lon in customer_locations]
    depot_node = ox.distance.nearest_nodes(G, depot_location[1], depot_location[0])
    nodes = [depot_node] + nearest_nodes

    distance_matrix = []
    for node_u in nodes:
        row = []
        for node_v in nodes:
            try:
                length = nx.shortest_path_length(G, source=node_u, target=node_v, weight='length')
            except nx.NetworkXNoPath:
                length = float('inf')
            row.append(length)
        distance_matrix.append(row)

    return distance_matrix, nodes

def optimize_routes(brukare_df, medarbetare_df, G, depot_location):
    """
    Optimizes routes for medarbetare to visit brukare based on constraints and distance.
    """
    customer_locations = list(zip(brukare_df['Latitude'], brukare_df['Longitude']))
    distance_matrix, nodes = generate_distance_matrix(G, customer_locations, depot_location)
    num_vehicles = len(medarbetare_df)
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), num_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 30

    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        return parse_solution(manager, routing, solution)
    else:
        print("No solution found!")
        return None

def parse_solution(manager, routing, solution):
    """
    Parses the solution from the route optimization.
    """
    total_distance = 0
    routes = {}
    for vehicle_id in range(routing.vehicles()):
        index = routing.Start(vehicle_id)
        route = []
        route_distance = 0
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)
        routes[f"Vehicle {vehicle_id + 1}"] = route
        total_distance += route_distance
    return routes
