import gurobipy as grb
from route_calc_variables import RouteCalcVariables


class Solution:
    def __init__(self):
        self.optimal_key = 0
        self.status = 0
        self.optimal_value = 0
        self.variables = {}

    def setValues(self, model, variables, optimal_key):
        """
                :type model: grb.Model
                :type variables: RouteCalcVariables
                :type optimal_key: int
                """
        self.optimal_key = optimal_key
        if optimal_key != 0:
            self.status = model.getAttr("Status")
            if self.status == grb.GRB.OPTIMAL:
                self.optimal_value = model.ObjVal
                self.variables = {"x": {}, "y": {}, "b": {}, "z": {}}
                for link, capacity in variables.x.items():
                    self.variables["x"][link] = capacity.X
                for link, capacity in variables.y.items():
                    self.variables["y"][link] = capacity.X
                for link, capacity in variables.b.items():
                    self.variables["b"][link] = capacity.X
                for link, capacity in variables.z.items():
                    self.variables["z"][link] = capacity.X
            else:
                self.variables = None
        else:
            self.variables = None

    def isOptimized(self):
        if self.optimal_key != 0:
            if self.status == grb.GRB.OPTIMAL:
                return self.optimal_key
            else:
                return False
        else:
            return False

    def copy(self, targetObject):
        """

        :type targetObject: Solution
        :return:
        """
        targetObject.optimal_value = self.optimal_value
        targetObject.status = self.status
        targetObject.optimal_key = self.optimal_key
        if self.variables is not None:
            targetObject.variables = {"x": {}, "y": {}, "b": {}, "z": {}}
            for link, capacity in self.variables["x"].items():
                targetObject.variables["x"][link] = capacity
            for link, capacity in self.variables["y"].items():
                targetObject.variables["y"][link] = capacity
            for link, capacity in self.variables["b"].items():
                targetObject.variables["b"][link] = capacity
            for link, capacity in self.variables["z"].items():
                targetObject.variables["z"][link] = capacity
