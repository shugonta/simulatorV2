import gurobipy as grb
import sys
import math
from enum import Enum
from route_calc_variables import RouteCalcVariables
from solution import Solution


class RouteCalcType(Enum):
    MinCostFlow = 1
    Backup = 2
    ExpectedCapacityGuarantee = 3
    AdaptableExpectedCapacityGurantee = 4


class Traffic:
    COST_FUNCTION_GRANULARITY = 10

    def __init__(self, id, start_node, end_node, holding_time=0, bandwidth=0, quality=0):
        self.id = id
        self.start_node = start_node
        self.end_node = end_node
        self.holding_time = holding_time
        self.bandwidth = bandwidth
        self.quality = quality
        self.total_data = 0

    def LinkUsedCostFunc(self, x):
        return pow(x, 2)

    def AdaptiveOptimize(self, solution, link_list, available_link_list, assigned_capacity, t, K, p, q, nodes, quality):
        m = grb.Model()
        variables = RouteCalcVariables()
        m.setParam('OutputFlag', False)
        bandwidth_max = 0
        N = range(0, self.COST_FUNCTION_GRANULARITY + 1)
        link_used_cost = {}
        link_used_cost_threshold = {}

        max_link_length = 0
        for (i, j), link_item in link_list.items():
            if max_link_length < link_item.distance:
                max_link_length = link_item.distance

        for n in N:
            link_used_cost_threshold[n] = n / self.COST_FUNCTION_GRANULARITY
            link_used_cost[n] = max_link_length * assigned_capacity * t * self.LinkUsedCostFunc(link_used_cost_threshold[n])

        # 変数追加
        for (i, j), link_item in link_list.items():
            if link_item.failure_status == 0:
                bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                available_link_list.append((i, j))
                for k in K:
                    variables.x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                    variables.y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="y_{%d,%d,%d}" % (k, i, j))
                for n in N:
                    variables.z[n, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="z_{%d,%d,%d}" % (n, i, j))
        for k in K:
            variables.b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)
        m.update()  # モデルに変数が追加されたことを反映させる

        # 目的関数を設定し，最小化を行うことを明示する
        m.setObjective(
            grb.quicksum(grb.quicksum(variables.y[k, i, j] * link_list[i, j].distance * t for (i, j) in available_link_list) for k in K)
            + grb.quicksum(grb.quicksum(variables.z[n, i, j] * link_used_cost[n] for n in N) for (i, j) in available_link_list),
            grb.GRB.MINIMIZE)  # 目的関数
        # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

        # 制約追加
        for i in nodes:
            if i == p:
                for k in K:
                    m.addConstr(grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                                - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list)
                                == 1, name="flow reservation at node %d route %d" % (i, k))
            if i != p and i != q:
                for k in K:
                    m.addConstr(grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                                - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list)
                                == 0, name="flow reservation at node %d route %d" % (i, k))

        for (i, j) in available_link_list:
            m.addConstr(
                0 <= grb.quicksum(variables.y[k, i, j] for k in K) <= link_list[(i, j)].bandwidth, name="capacity requirement at (%d, %d)" % (i, j))
            m.addConstr(grb.quicksum(variables.z[n, i, j] for n in N) == 1, name="restrict link used cost func for link (%d, %d)" % (i, j))
            if link_list[i, j].bandwidth != 0:
                for n in N:
                    m.addConstr(grb.quicksum(variables.y[k, i, j] for k in K) / link_list[i, j].bandwidth * variables.z[n, i, j] <= link_used_cost_threshold[n],
                                name="link occupation rate for link (%d, %d) at cost %d" % (i, j, n))

        m.addConstr(grb.quicksum(variables.b[k] for k in K) >= assigned_capacity, name="required capacity requirement")
        m.addConstr(grb.quicksum(variables.b[k] for k in K) - grb.quicksum(
            grb.quicksum(
                (1 - link_list[(i, j)].calculate_reliability(t)) * variables.y[k, i, j] for (i, j) in available_link_list) for k in K) >= quality * assigned_capacity,
                    name="expected capacity requirement")

        for k in K:
            for (i, j) in available_link_list:
                m.addConstr(variables.y[k, i, j] >= variables.b[k] + (bandwidth_max * (variables.x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
                m.addConstr(variables.y[k, i, j] <= link_list[(i, j)].bandwidth * variables.x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
                m.addConstr(variables.y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

        # モデルに制約条件が追加されたことを反映させる
        m.update()
        # print("elapsed_time for modeling %.5f sec" % (stop - start))

        # 最適化を行い，結果を表示させる
        # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

        m.optimize()
        solution.setValues(m, variables, t)

        return m

    # 範囲確認
    def doCalcRange(self, solution_list, required_total_capacity, link_list, available_link_list, delta, min_val, max_val, min_noval_upper, max_noval_lower, K, p, q, nodes, quality):
        """
             :type solution_list: dict[int, Solution]
             :type required_total_capacity: int
             :type link_list
             :type link_list: dict[tuple[int, int], Link]
             :type available_link_list: list[tuple[int, int]]
             :type delta: int
             :type min_val: int
             :type max_val: int
             :type min_noval_upper: int
             :type max_noval_lower: int
             :return: list[int,int]
             """

        # 範囲最小値
        for t in range(max_noval_lower, min_val, delta):
            if t not in solution_list:
                solution_list[t] = Solution()
                self.AdaptiveOptimize(solution_list[t], link_list, available_link_list, required_total_capacity / t, t, K, p, q, nodes, quality)
            if solution_list[t].isOptimized():
                if t < min_val:
                    min_val = t
                    break
                if t > max_val:
                    max_val = t
            else:
                if max_val < t < min_noval_upper and min_val < t:
                    min_noval_upper = t
                if max_noval_lower < t < min_val and max_val > t:
                    max_noval_lower = t

        # 範囲最大値
        for t in range(max_val, min_noval_upper, delta):
            if t not in solution_list:
                solution_list[t] = Solution()
                self.AdaptiveOptimize(solution_list[t], link_list, available_link_list, required_total_capacity / t, t, K, p, q, nodes, quality)
            if solution_list[t].isOptimized():
                if t > max_val:
                    max_val = t
            else:
                if max_val < t < min_noval_upper and min_val < t:
                    min_noval_upper = t
                    break

        if delta == 1:
            return [min_val, max_val]
        else:
            return self.doCalcRange(solution_list, required_total_capacity, link_list, available_link_list, int(math.ceil(delta / 2)), min_val, max_val, min_noval_upper, max_noval_lower,
                                    K, p, q, nodes, quality)

    def GetObjVal(self, solution_list, link_list, available_link_list, required_total_capacity, t, K, p, q, nodes, quality, minimum_time, maximum_time, direction=0):
        """

        :param solution_list: dict[int, Solution]
        :param link_list:
        :param available_link_list:
        :param required_total_capacity:
        :param t:
        :param K:
        :param p:
        :param q:
        :param nodes:
        :param quality:
        :param minimum_time:
        :param maximum_time:
        :param direction:
        :return:
        """
        assigned_capacity = required_total_capacity / t
        if t not in solution_list:
            solution_list[t] = Solution()
            self.AdaptiveOptimize(solution_list[t], link_list, available_link_list, assigned_capacity, t, K, p, q, nodes, quality)

        if solution_list[t].isOptimized():
            print("t: %d, optimal value:\t%8.4f" % (t, solution_list[t].optimal_value))
            return solution_list[t].optimal_value, t
        else:
            # 上
            if direction >= 0:
                if t + 1 <= maximum_time:
                    print("shifted to %d" % (t + 1))
                    return self.GetObjVal(solution_list, link_list, available_link_list, required_total_capacity, t + 1, K, p, q, nodes, quality, minimum_time, maximum_time, 1)
            # 下
            if direction <= 0:
                if minimum_time <= t - 1:
                    print("shifted to %d" % (t - 1))
                    return self.GetObjVal(solution_list, link_list, available_link_list, required_total_capacity, t - 1, K, p, q, nodes, quality, minimum_time, maximum_time, -1)
            return False

    def CalcRoute(self, solution, routing_type, max_route_num, node_size, link_list, available_link_list):
        """

        :type solution: Solution
        :type routing_type: RouteCalcType
        :type max_route_num: int
        :type node_size: int
        :type link_list: dict[tuple[int, int], Link]
        :type available_link_list: list[tuple[int, int]]
        :return:
        """
        M = max_route_num  # 経路数
        p = self.start_node  # 起点
        q = self.end_node  # 終点
        required_capacity = self.bandwidth
        quality = self.quality

        K = range(1, M + 1)
        nodes = range(1, node_size + 1)
        bandwidth_max = 0

        # print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
        if routing_type == RouteCalcType.ExpectedCapacityGuarantee:
            m = grb.Model()
            variables = RouteCalcVariables()
            m.setParam('OutputFlag', 0)

            # 変数追加
            for (i, j), link_item in link_list.items():
                if link_item.failure_status == 0:
                    bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                    available_link_list.append((i, j))
                    for k in K:
                        variables.x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                        variables.y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="y_{%d,%d,%d}" % (k, i, j))
            for k in K:
                variables.b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

            m.update()  # モデルに変数が追加されたことを反映させる

            # 目的関数を設定し，最小化を行うことを明示する
            m.setObjective(grb.quicksum(
                grb.quicksum(variables.y[k, i, j] * link_list[(i, j)].distance for (i, j) in available_link_list)
                for k in K),
                grb.GRB.MINIMIZE)  # 目的関数
            # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

            # 制約追加
            for i in nodes:
                if i == p:
                    for k in K:
                        m.addConstr(grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                                    - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list)
                                    == 1, name="flow reservation at node %d route %d" % (i, k))
                if i != p and i != q:
                    for k in K:
                        m.addConstr(grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                                    - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list)
                                    == 0, name="flow reservation at node %d route %d" % (i, k))

            for (i, j) in available_link_list:
                m.addConstr(
                    0 <= grb.quicksum(variables.y[k, i, j] for k in K) <= min(link_list[(i, j)].bandwidth, required_capacity), name="capacity requirement at (%d, %d)" % (i, j))

            m.addConstr(grb.quicksum(variables.b[k] for k in K) >= required_capacity, name="required capacity requirement")
            m.addConstr(grb.quicksum(variables.b[k] for k in K) - grb.quicksum(
                grb.quicksum(
                    (1 - link_list[(i, j)].calculate_reliability(self.holding_time)) * variables.y[k, i, j] for (i, j) in available_link_list) for k in K) >= quality * required_capacity,
                        name="expected capacity requirement")

            for k in K:
                for (i, j) in available_link_list:
                    m.addConstr(variables.y[k, i, j] >= variables.b[k] + (bandwidth_max * (variables.x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(variables.y[k, i, j] <= link_list[(i, j)].bandwidth * variables.x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(variables.y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

            # モデルに制約条件が追加されたことを反映させる
            m.update()
            # 最適化を行い，結果を表示させる
            # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

            m.optimize()
            solution.setValues(m, variables, self.holding_time)
        elif routing_type == RouteCalcType.MinCostFlow:
            m = grb.Model()
            variables = RouteCalcVariables()
            m.setParam('OutputFlag', 0)

            for (i, j), link_item in link_list.items():
                if link_item.failure_status == 0:
                    bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                    available_link_list.append((i, j))
                    for k in K:
                        variables.x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                        variables.y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER,
                                                        name="y_{%d,%d,%d}" % (k, i, j))
            for k in K:
                variables.b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

            m.update()  # モデルに変数が追加されたことを反映させる

            # 目的関数を設定し，最小化を行うことを明示する
            m.setObjective(grb.quicksum(grb.quicksum(variables.y[k, i, j] * link_list[(i, j)].distance for (i, j) in available_link_list) for k in K), grb.GRB.MINIMIZE)  # 目的関数
            # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

            # 制約追加
            for i in nodes:
                if i == p:
                    for k in K:
                        m.addConstr(
                            grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                            - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list) == 1, name="flow reservation at node %d route %d" % (i, k))
                if i != p and i != q:
                    for k in K:
                        m.addConstr(
                            grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                            - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list) == 0, name="flow reservation at node %d route %d" % (i, k))

            for (i, j) in available_link_list:
                m.addConstr(0 <= grb.quicksum(variables.y[k, i, j] for k in K) <= min(link_list[(i, j)].bandwidth, required_capacity), name="capacity requirement at (%d, %d)" % (i, j))

            for k in K:
                m.addConstr(variables.b[k] <= required_capacity, name="route %d requirement" % k)
                m.addConstr(grb.quicksum(variables.b[k] for k in K) >= required_capacity, name="required capacity requirement")
            for k in K:
                for (i, j) in available_link_list:
                    m.addConstr(variables.y[k, i, j] >= variables.b[k] + (bandwidth_max * (variables.x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(variables.y[k, i, j] <= link_list[(i, j)].bandwidth * variables.x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(variables.y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

            # モデルに制約条件が追加されたことを反映させる
            m.update()
            # 最適化を行い，結果を表示させる
            # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

            m.optimize()
            solution.setValues(m, variables, self.holding_time)
        elif routing_type == RouteCalcType.Backup:
            m = grb.Model()
            variables = RouteCalcVariables()
            m.setParam('OutputFlag', 0)

            for (i, j), link_item in link_list.items():
                if link_item.failure_status == 0:
                    bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                    available_link_list.append((i, j))
                    for k in K:
                        variables.x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                        variables.y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="y_{%d,%d,%d}" % (k, i, j))
            for k in K:
                variables.b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

            m.update()  # モデルに変数が追加されたことを反映させる

            # 目的関数を設定し，最小化を行うことを明示する
            m.setObjective(grb.quicksum(grb.quicksum(variables.y[k, i, j] * link_list[(i, j)].distance for (i, j) in available_link_list) for k in K), grb.GRB.MINIMIZE)  # 目的関数
            # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

            # 制約追加
            for i in nodes:
                if i == p:
                    for k in K:
                        m.addConstr(grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                                    - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list) == 1, name="flow reservation at node %d route %d" % (i, k))
                if i != p and i != q:
                    for k in K:
                        m.addConstr(grb.quicksum(variables.x[k, i, j] for j in nodes if (i, j) in available_link_list)
                                    - grb.quicksum(variables.x[k, j, i] for j in nodes if (j, i) in available_link_list) == 0, name="flow reservation at node %d route %d" % (i, k))

            for (i, j) in available_link_list:
                m.addConstr(0 <= grb.quicksum(variables.y[k, i, j] for k in K) <= min(link_list[(i, j)].bandwidth, required_capacity), name="capacity requirement at (%d, %d)" % (i, j))

            m.addConstr(variables.b[1] >= required_capacity, name="main route capacity requirement")

            for k in K:
                if k != 1:
                    m.addConstr(variables.b[k] >= self.quality * self.bandwidth,
                                name="backup route capacity requirement")

            for (i, j) in available_link_list:
                for k1 in K:
                    for k2 in K:
                        if k1 != k2:
                            m.addConstr(variables.x[k1, i, j] + variables.x[k2, i, j] <= 1, name="disjoint requirement at (%d, %d) for route %d, %d" % (i, j, k1, k2))

            for k in K:
                for (i, j) in available_link_list:
                    m.addConstr(variables.y[k, i, j] >= variables.b[k] + (bandwidth_max * (variables.x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(variables.y[k, i, j] <= link_list[(i, j)].bandwidth * variables.x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(variables.y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))
            # モデルに制約条件が追加されたことを反映させる
            m.update()
            # 最適化を行い，結果を表示させる
            # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

            m.optimize()
            solution.setValues(m, variables, self.holding_time)
        elif routing_type == RouteCalcType.AdaptableExpectedCapacityGurantee:
            solution_list = {}  # type: dict[int, Solution]
            minimum_cost = sys.maxsize
            optimal_time = 0
            start_time = 1
            required_total_capacity = self.bandwidth * self.holding_time
            end_time = required_total_capacity
            delta = math.ceil((end_time - start_time) / 2)
            if delta == 0:
                delta = 1
            result = self.doCalcRange(solution_list, required_total_capacity, link_list, available_link_list, delta, end_time + 1, start_time, end_time + 1, start_time, K, p, q, nodes,
                                      quality)
            print("min %d max %d" % (result[0], result[1]))

            start_time_sol = result[0]
            end_time_sol = result[1]

            if start_time_sol > end_time_sol:
                # 解なし
                print("No Optimal")
                solution_list[end_time_sol].copy(solution)
                return end_time_sol
            # else:
            #     center_time = math.ceil((start_time_sol + end_time_sol) / 2)
            #     left_time = start_time_sol
            #     right_time = end_time_sol
            #     delta = math.ceil((start_time_sol + end_time_sol) / 4)
            #     shift_direction = 0
            #     left_val = 0
            #     center_val = 0
            #     right_val = 0
            #     while delta > 0:
            #         # 左側
            #         if left_val == 0:
            #             t = max(center_time - delta, start_time_sol)
            #             print("left")
            #             objVal = self.GetObjVal(solution_list, link_list, available_link_list, required_total_capacity, t, K, p, q, nodes, quality, start_time_sol, center_time)
            #             if objVal:
            #                 left_val = objVal[0]
            #                 left_time = objVal[1]
            #             else:
            #                 optimal_time = -1
            #                 break
            #         if center_val == 0:
            #             t = center_time
            #             print("center")
            #             objVal = self.GetObjVal(solution_list, link_list, available_link_list, required_total_capacity, t, K, p, q, nodes, quality, left_time, right_time)
            #             if objVal:
            #                 center_val = objVal[0]
            #                 center_time = objVal[1]
            #             else:
            #                 optimal_time = -1
            #                 break
            #
            #                 #
            #                 # assigned_capacity = required_total_capacity / t
            #                 # if t not in model_list:
            #                 #     model_list[t] = grb.Model()
            #                 #     variable_list[t] = RouteCalcVariables()
            #                 #     model_list[t] = self.AdaptiveOptimize(model_list[t], variable_list[t], link_list, available_link_list, assigned_capacity, t, K, p, q, nodes, quality)
            #                 #
            #                 # if model_list[t].getAttr("Status") == grb.GRB.OPTIMAL:
            #                 #     print("center t: %d, optimal value:\t%8.4f" % (t, model_list[t].ObjVal))
            #                 #     f = open("adjust_speed_slope.csv", 'a')
            #                 #     f.write("%d %f\n" % (t, model_list[t].ObjVal))
            #                 #     for k in K:
            #                 #         for (i, j) in link_list:
            #                 #             if variable_list[t].y[k, i, j].x != 0:
            #                 #                 f.write("%s:\t%8.4f\n" % (variable_list[t].y[k, i, j].VarName, variable_list[t].y[k, i, j].X))
            #                 #     f.write("\n\n")
            #                 #     f.close()
            #                 #     center_val = model_list[t].ObjVal
            #                 # else:
            #                 #     optimal_time = -1
            #                 #     break
            #
            #         if right_val == 0:
            #             t = min(center_time + delta, end_time_sol)
            #             print("right")
            #             objVal = self.GetObjVal(solution_list, link_list, available_link_list, required_total_capacity, t, K, p, q, nodes, quality, center_time, end_time_sol)
            #             if objVal:
            #                 right_val = objVal[0]
            #                 right_time = objVal[1]
            #             else:
            #                 optimal_time = -1
            #                 break
            #
            #         if left_val <= center_val <= right_val:
            #             # 単調増加
            #             shift_direction = -1
            #         elif left_val > center_val > right_val:
            #             # 単調減少
            #             shift_direction = 1
            #         elif left_val == center_val or center_val == right_val:
            #             shift_direction = 0
            #         elif left_val > center_val and right_val > center_val:
            #             shift_direction = 0
            #
            #         if shift_direction == 1:
            #             if center_time + delta >= end_time_sol:
            #                 # 関数全体が単調減少
            #                 minimum_cost = right_val
            #                 optimal_time = end_time_sol
            #                 break
            #             center_time = right_time
            #             left_val = center_val
            #             center_val = right_val
            #             right_val = 0
            #         elif shift_direction == -1:
            #             if center_time - delta <= start_time_sol:
            #                 # 関数全体が単調増加
            #                 minimum_cost = left_val
            #                 optimal_time = start_time_sol
            #                 break
            #             center_time = left_time
            #             right_val = center_val
            #             center_val = left_val
            #             left_val = 0
            #         elif shift_direction == 0:
            #             left_val = 0
            #             right_val = 0
            #             delta = math.floor(delta / 2)
            #             minimum_cost = center_val
            #             optimal_time = center_time

            optimal_time = -1
            if optimal_time == -1:
                minimum_val = sys.maxsize
                # どうにもならないときに線形探索
                print("Liner Discovery")
                for t in range(start_time_sol, end_time_sol + 1):
                    objVal = self.GetObjVal(solution_list, link_list, available_link_list, required_total_capacity, t, K, p, q, nodes, quality, t, t)
                    if objVal:
                        if objVal[0] < minimum_val:
                            minimum_val = objVal[0]
                            optimal_time = objVal[1]
                if optimal_time == -1:
                    print("No Optimal")
                    solution_list[end_time_sol].copy(solution)
                    return end_time_sol
                else:
                    print("Optimal Found: %d" % optimal_time)
                    solution_list[optimal_time].copy(solution)
                    return optimal_time
            else:
                solution_list[optimal_time].copy(solution)
                print("minimum cost %.5f time: %d" % (minimum_cost, optimal_time))
                return optimal_time
        else:
            return False

        return self.holding_time
