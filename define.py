class Define:
    def __init__(self, traffic_demand: int, holding_time: int, total_traffic: int,
                 max_route: int, avg_repaired_time: int, node_size : int):
        self.traffic_demand = traffic_demand
        self.holding_time = holding_time
        self.total_traffic = total_traffic
        self.max_route = max_route
        self.avg_repaired_time = avg_repaired_time
        self.node_size = node_size
