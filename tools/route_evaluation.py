from langchain.tools import StructuredTool


def evaluate_route(
    time_taken,
    road_information: dict,
    private_or_public: bool,
    carpark_availability: dict = None,
) -> float:
    MAX_SCORE = 100
    MAX_TIME = 120
    MAX_CARPARK_LOTS = 100
    PENALTY_ROADWORK = 10
    PENALTY_INCIDENT = 20
    route_score = 0

    # Time score calculation
    if time_taken >= MAX_TIME:
        time_score = 0
    else:
        time_score = MAX_SCORE * (1 - (time_taken / MAX_TIME))

    # Incident and roadwork score calculation
    incident_score = MAX_SCORE
    for road in road_information.values():
        incident_score -= (
            road["roadworks"] * PENALTY_ROADWORK
            + road["incidents"] * PENALTY_INCIDENT
            + road["breakdowns"] * PENALTY_INCIDENT
        )
    incident_score = max(0, incident_score)

    # Carpark score calculation for private transport
    carpark_score = 0
    if private_or_public and carpark_availability is not None:
        total_lots = sum(
            carpark["availablelots"] for carpark in carpark_availability.values()
        )
        carpark_score = (
            MAX_SCORE
            if total_lots >= MAX_CARPARK_LOTS
            else total_lots / MAX_CARPARK_LOTS * MAX_SCORE
        )

    # Weights and final score calculation
    if private_or_public:
        # For private transport, include carpark score in the final calculation
        time_weight = 0.6
        incident_weight = 0.3
        carpark_weight = 0.1
        route_score = (
            time_weight * time_score
            + incident_weight * incident_score
            + carpark_weight * carpark_score
        )
    else:
        # For public transport, only time and incident scores are considered
        time_weight = 0.7
        incident_weight = 0.3
        route_score = time_weight * time_score + incident_weight * incident_score

    return route_score


def get_top_public_transport_routes(
    routes_with_score: list[float], is_public_transport: list[bool]
) -> str:
    # This function is only for non-drivers
    """
    Get a string describing the top public transport routes based on their scores.
    """
    # Combine each route score with its index and filter for public transport
    public_routes_with_scores = [
        (index + 1, score)
        for index, (score, is_public) in enumerate(
            zip(routes_with_score, is_public_transport)
        )
        if is_public
    ]

    # Sort the public transport routes by score in descending order
    sorted_public_routes = sorted(
        public_routes_with_scores, key=lambda x: x[1], reverse=True
    )

    # Create the formatted output for the top public transport routes
    top_route_strings = []
    route_descriptions = ["Best route", "Second best route", "Third best route"]
    for i, (route_index, score) in enumerate(sorted_public_routes[:3]):
        route_description = (
            route_descriptions[i]
            if i < len(route_descriptions)
            else f"{i + 1}th best route"
        )
        top_route_strings.append(
            f"{route_description} is route {route_index} (score={score:.1f})"
        )

    # Join the route strings with a new line and appropriate heading
    if top_route_strings:
        return "For public transport options,\n" + ".\n".join(top_route_strings) + "."
    else:
        return "No public transport routes available."


def get_top_transport_routes(
    routes_with_score: list[float], is_public_transport: list[bool]
) -> str:
    """
    Get a string describing the top 2 private transport routes and top 1 public transport route based on their scores.

    :param routes_with_score: List of floats, with each float being the score for each route.
    :param is_public_transport: List of booleans, indicating whether each route is a public transport route.
    :return: A formatted string describing the top transport routes.
    """
    # Combine each route score with its index and separate public and private routes
    transport_routes_with_scores = [
        (index + 1, score, is_public)
        for index, (score, is_public) in enumerate(
            zip(routes_with_score, is_public_transport)
        )
    ]

    # Sort the transport routes by score in descending order
    sorted_transport_routes = sorted(
        transport_routes_with_scores, key=lambda x: x[1], reverse=True
    )

    # Split the sorted routes into public and private
    private_routes = [route for route in sorted_transport_routes if not route[2]]
    public_routes = [route for route in sorted_transport_routes if route[2]]

    # Create the formatted output
    top_route_strings = []

    # Get top 2 private routes
    for i, (route_index, score, _) in enumerate(private_routes[:2]):
        position = "Best" if i == 0 else "Second best"
        top_route_strings.append(
            f"{position} private route is route {route_index} (score={score:.1f})"
        )

    # Get top 1 public route if available
    if public_routes:
        route_index, score, _ = public_routes[0]
        top_route_strings.append(
            f"Best public route is route {route_index} (score={score:.1f})"
        )

    # Join the route strings with a new line and appropriate heading
    if top_route_strings:
        return "\n".join(top_route_strings) + "."
    else:
        return "No suitable transport routes available."


evaluate_route_tool = StructuredTool.from_function(
    func=evaluate_route,
    name="RouteEvaluatorTool",
    description="""
    Evaluate routes based on incidents and parking availability near the destination and gives final weighted score.
    
    """,
)

rank_routes_tool = StructuredTool.from_function(
    func=get_top_transport_routes,
    name="RankRoutesTool",
    description="""
    Get a string describing the top public transport routes based on their scores.
    """,
)


# Components:
# - Time score: Scored proportionately to estimated travel time.
# - Road incident score: From maximum score, penalized for each roadwork or breakdown.
# - Carpark score (for private transport): Based on available parking lots.

# Utilize extract_incidents and extract_parking_lots to provide road_information and carpark_availability.
# road_information format:
# {"roadName1": { "incidents": numberOfIncidents, "roadworks": numberOfRoadworks, "breakdowns": numberOfBreakdowns}, ...}
# carpark_availability format:
# {"carpark": {"development": nameOfDevelopment, "availablelots": numberOfAvailableLots}, ...}
# private_or_public: True if taking private transport, False otherwise

# Output is a weighted score for the route, denoting its desirability and ease of use, out of 100.
