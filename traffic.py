class Traffic:
    def __init__(self, id, start_node, end_node, holding_time=0, bandwidth=0, quality=0):
        self.id = id
        self.start_node = start_node
        self.end_node = end_node
        self.holding_time = holding_time
        self.bandwidth = bandwidth
        self.quality = quality
        self.total_data = 0
