import math


class Link:
    def __init__(self, distance=0,
                 bandwidth=0, failure_rate=0.0, failure_status=0, shape=1, scale=1, age=0):
        """

        :param distance: int
        :param bandwidth: int
        :param failure_rate: float
        :param failure_status: int
        :param shape: int
        :param scale: int
        """
        self.distance = distance
        self.bandwidth = bandwidth
        self.failure_rate = failure_rate
        self.failure_status = failure_status
        self.shape = shape
        self.scale = scale
        self.age = age

    def calculate_reliability(self, holding_time):
        """

        :type holding_time: int
        :return:
        """
        reliability = math.exp(
            (pow(self.age, self.shape) - pow(self.age + holding_time, self.shape)) / pow(self.scale, self.shape))
        return reliability

    def update_link_failure_rate(self):
        """
        :return:
        """
        failure_rate = self.get_weibull_failure_rate(self.shape, self.scale, self.age)
        self.failure_rate = failure_rate

    def add_age(self):
        self.age += 1

    def reset(self, shape=1, scale=1):
        self.shape = shape
        self.scale = scale
        self.failure_rate = 0.0
        self.failure_status = 0
        self.age = 0

    @staticmethod
    def get_weibull_failure_rate(shape, scale, t):
        """

        :param shape: float
        :param scale: float
        :param t: float
        :return: float
        """
        # print("%d:%d:%d\n" %(shape,scale,t))
        failure_rate = ((shape * pow(t, (shape - 1))) / pow(scale, shape))
        return failure_rate
