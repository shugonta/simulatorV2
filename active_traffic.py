from traffic import Traffic
from link import Link


class ActiveTraffic:
    def __init__(self, end_time, actual_holding_time, traffic, routes):
        """

        :type end_time: int
        :type actual_holding_time: int
        :type traffic: Traffic
        :type routes: list[dict[(int,int),Link]]
        """
        self.end_time = end_time
        self.actual_holding_time = actual_holding_time
        self.traffic = traffic
        self.routes = routes
