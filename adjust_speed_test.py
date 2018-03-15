# Gurobi パッケージを grb という名前で import
import gurobipy as grb
import time
import math
import sys

f = open('topology.txt', 'r')
line = f.readline()  # 1行を文字列として読み込む(改行文字も含まれる)
node_count = int(line)
# リンク集合
links = []
distance = {}
capacity = {}
reliability = {}
# ノード集合
nodes = range(1, node_count + 1)
line = f.readline()

while line:
    data = line[:-1].split(' ')
    if len(data) == 3 and data[0].isdigit() and data[1].isdigit() and data[2].isdigit():
        links.append((int(data[0]), int(data[1])))
        distance[(int(data[0]), int(data[1]))] = int(data[2])
        capacity[(int(data[0]), int(data[1]))] = 10
        # reliability[(int(data[0]), int(data[1]))] = 0.9
    line = f.readline()
f.close()

p = 1  # 起点
q = 5  # 終点

M = 3  # 経路数
K = range(1, M + 1)

required_capacity = 50
quality = 1
c_max = 13

cost_function_granularity = 10
N = range(0, cost_function_granularity + 1)
link_used_cost = {}
link_used_cost_threshold = {}


def LinkUsedCostFunc(x):
    return 2 * pow(x, 2)


for n in N:
    link_used_cost_threshold[n] = n / cost_function_granularity
    link_used_cost[n] = LinkUsedCostFunc(link_used_cost_threshold[n])


def Optimize(m, assigned_capacity, t):
    for (i, j) in links:
        reliability[i, j] = math.exp(-1 * 0.01 * t)

    # 各リンクの輸送費用
    # distance = dict(zip(links, [3, 8, 2, 12, 2, 6]))
    # 各リンクの容量
    # capacity = dict(zip(links, [5, 13, 10, 9, 10, 10]))
    # 各リンクの信頼度
    # reliability = dict(zip(links, [0.740818221, 0.990049834, 0.990049834, 0.990049834, 0.990049834, 0.740818221]))

    # print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
    m.setParam('OutputFlag', False)
    # 変数は辞書型変数に格納
    x = {}
    y = {}
    b = {}
    z = {}

    # 変数追加
    for (i, j) in links:
        for k in K:
            x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
            y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.CONTINUOUS, name="y_{%d,%d,%d}" % (k, i, j))
        for n in N:
            z[n, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="z_{%d,%d,%d}" % (n, i, j))
    for k in K:
        b[k] = m.addVar(lb=0.0, vtype=grb.GRB.CONTINUOUS, name="b_{%d}" % k)

    m.update()  # モデルに変数が追加されたことを反映させる

    # 目的関数を設定し，最小化を行うことを明示する
    m.setObjective(
        grb.quicksum(grb.quicksum(y[k, i, j] * distance[i, j] * t for (i, j) in links) for k in K) + grb.quicksum(grb.quicksum(z[n, i, j] * link_used_cost[n] for n in N) for (i, j) in links),
        grb.GRB.MINIMIZE)  # 目的関数
    # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

    # 制約追加
    for i in nodes:
        if i == p:
            for k in K:
                m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in links) - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in links) == 1,
                            name="flow reservation at node %d route %d" % (i, k))
        if i != p and i != q:
            for k in K:
                m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in links) - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in links) == 0,
                            name="flow reservation at node %d route %d" % (i, k))

    for (i, j) in links:
        m.addConstr(0 <= grb.quicksum(y[k, i, j] for k in K) <= capacity[i, j], name="capacity requirement at (%d, %d)" % (i, j))
        # m.addConstr(0 <= grb.quicksum(y[k, i, j] for k in K) <= min(capacity[i, j], assigned_capacity), name="capacity requirement at (%d, %d)" % (i, j))
        m.addConstr(grb.quicksum(z[n, i, j] for n in N) == 1, name="restrict link used cost func for link (%d, %d)" % (i, j))
        if capacity[i, j] != 0:
            for n in N:
                m.addConstr(grb.quicksum(y[k, i, j] for k in K) / capacity[i, j] * z[n, i, j] <= link_used_cost_threshold[n],
                            name="link occupation rate for link (%d, %d) at cost %d" % (i, j, n))

    m.addConstr(grb.quicksum(b[k] for k in K) >= assigned_capacity, name="required capacity requirement")
    m.addConstr(grb.quicksum(b[k] for k in K) - grb.quicksum(grb.quicksum((1 - reliability[i, j]) * y[k, i, j] for (i, j) in links) for k in K) >= quality * assigned_capacity,
                name="expected capacity requirement")

    for k in K:
        for (i, j) in links:
            m.addConstr(y[k, i, j] >= b[k] + (c_max * (x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
            m.addConstr(y[k, i, j] <= capacity[i, j] * x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
            m.addConstr(y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

    # モデルに制約条件が追加されたことを反映させる
    m.update()
    # print("elapsed_time for modeling %.5f sec" % (stop - start))

    # 最適化を行い，結果を表示させる
    # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

    m.optimize()

    return m


T = range(1, required_capacity + 1)

start = time.time()
minimum_cost = sys.maxsize
optimal_time = 0
for t in T:
    assigned_capacity = required_capacity / t
    for (i, j) in links:
        reliability[i, j] = math.exp(-1 * 0.01 * t)

    # 各リンクの輸送費用
    # distance = dict(zip(links, [3, 8, 2, 12, 2, 6]))
    # 各リンクの容量
    # capacity = dict(zip(links, [5, 13, 10, 9, 10, 10]))
    # 各リンクの信頼度
    # reliability = dict(zip(links, [0.740818221, 0.990049834, 0.990049834, 0.990049834, 0.990049834, 0.740818221]))

    # print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
    m = grb.Model()
    m.setParam('OutputFlag', False)
    # 変数は辞書型変数に格納
    x = {}
    y = {}
    b = {}
    z = {}

    # 変数追加
    for (i, j) in links:
        for k in K:
            x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
            y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="y_{%d,%d,%d}" % (k, i, j))
        for n in N:
            z[n, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="z_{%d,%d,%d}" % (n, i, j))
    for k in K:
        b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

    m.update()  # モデルに変数が追加されたことを反映させる

    # 目的関数を設定し，最小化を行うことを明示する
    m.setObjective(
        grb.quicksum(grb.quicksum(y[k, i, j] * distance[i, j] * t for (i, j) in links) for k in K) + grb.quicksum(grb.quicksum(z[n, i, j] * link_used_cost[n] for n in N) for (i, j) in links),
        grb.GRB.MINIMIZE)  # 目的関数
    # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

    # 制約追加
    for i in nodes:
        if i == p:
            for k in K:
                m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in links) - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in links) == 1,
                            name="flow reservation at node %d route %d" % (i, k))
        if i != p and i != q:
            for k in K:
                m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in links) - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in links) == 0,
                            name="flow reservation at node %d route %d" % (i, k))

    for (i, j) in links:
        m.addConstr(0 <= grb.quicksum(y[k, i, j] for k in K) <= capacity[i, j], name="capacity requirement at (%d, %d)" % (i, j))
        # m.addConstr(0 <= grb.quicksum(y[k, i, j] for k in K) <= min(capacity[i, j], assigned_capacity), name="capacity requirement at (%d, %d)" % (i, j))
        m.addConstr(grb.quicksum(z[n, i, j] for n in N) == 1, name="restrict link used cost func for link (%d, %d)" % (i, j))
        for n in N:
            if capacity[i, j] != 0:
                m.addConstr(grb.quicksum(y[k, i, j] for k in K) / capacity[i, j] * z[n, i, j] <= link_used_cost_threshold[n],
                            name="link occupation rate for link (%d, %d) at cost %d" % (i, j, n))

    m.addConstr(grb.quicksum(b[k] for k in K) >= assigned_capacity, name="required capacity requirement")
    m.addConstr(grb.quicksum(b[k] for k in K) - grb.quicksum(grb.quicksum((1 - reliability[i, j]) * y[k, i, j] for (i, j) in links) for k in K) >= quality * assigned_capacity,
                name="expected capacity requirement")

    for k in K:
        for (i, j) in links:
            m.addConstr(y[k, i, j] >= b[k] + (c_max * (x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
            m.addConstr(y[k, i, j] <= capacity[i, j] * x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
            m.addConstr(y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

    # モデルに制約条件が追加されたことを反映させる
    m.update()
    # print("elapsed_time for modeling %.5f sec" % (stop - start))

    # 最適化を行い，結果を表示させる
    m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

    m.optimize()
    if m.getAttr("Status") == grb.GRB.OPTIMAL:
        # print("optimal value:\t%8.4f" % m.ObjVal)
        f = open("adjust_speed.csv", 'a')
        f.write("%d, %f\n" % (t, m.ObjVal))
        # for k in K:
        #     for (i, j) in links:
        #         if y[k, i, j].x != 0:
        #             print("%s:\t%8.4f" % (y[k, i, j].VarName, y[k, i, j].X))
        if m.ObjVal < minimum_cost:
            minimum_cost = m.ObjVal
            optimal_time = t
            # print("elapsed_time %.5f sec" % (stop - start))
        for k in K:
            for (i, j) in links:
                if y[k, i, j].x != 0:
                    f.write("%s:\t%8.4f\n" % (y[k, i, j].VarName, y[k, i, j].X))
        f.write("\n\n")
        f.close()
stop = time.time()
print("minimum cost %.5f time: %d" % (minimum_cost, optimal_time))
print("elapsed_time %.5f sec" % (stop - start))


# 範囲確認
def doCalcRange(model, delta, min_val, max_val, min_noval_upper, max_noval_lower):
    # 範囲最小値
    for t in range(max_noval_lower, min_val, delta):
        if t not in model:
            model[t] = grb.Model()
            model[t] = Optimize(model[t], required_capacity / t, t)
        if model[t].getAttr("Status") == grb.GRB.OPTIMAL:
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
        if t not in model:
            model[t] = grb.Model()
            model[t] = Optimize(model[t], required_capacity / t, t)
        if model[t].getAttr("Status") == grb.GRB.OPTIMAL:
            if t > max_val:
                max_val = t
        else:
            if max_val < t < min_noval_upper and min_val < t:
                min_noval_upper = t
                break

    if delta == 1:
        return [min_val, max_val]
    else:
        return doCalcRange(model, math.ceil(delta / 2), min_val, max_val, min_noval_upper, max_noval_lower)

start = time.time()
minimum_cost = sys.maxsize
optimal_time = 0
start_time = 1
end_time = required_capacity

model = {}
delta = math.ceil((end_time - start_time) / 2)
if delta == 0:
    delta = 1
result = doCalcRange(model, delta, end_time + 1, start_time, end_time + 1, start_time)
print("min %d max %d" % (result[0], result[1]))

start_time_sol = result[0]
end_time_sol = result[1]

if start_time_sol > end_time_sol:
    print("no solution")
else:
    center_time = math.ceil((start_time_sol + end_time_sol) / 2)
    delta = math.ceil((start_time_sol + end_time_sol) / 4)
    shift_direction = 0
    left_val = 0
    center_val = 0
    right_val = 0
    while delta > 0:
        # 左側
        if left_val == 0:
            t = max(center_time - delta, start_time_sol)
            assigned_capacity = required_capacity / t
            if t not in model:
                model[t] = grb.Model()
                model[t] = Optimize(model[t], assigned_capacity, t)

            if model[t].getAttr("Status") == grb.GRB.OPTIMAL:
                # print("left t: %d, optimal value:\t%8.4f" % (t, model[t].ObjVal))
                f = open("adjust_speed_slope.csv", 'a')
                f.write("%d %f\n" % (t, model[t].ObjVal))
                f.close()
                left_val = model[t].ObjVal
            else:
                optimal_time = -1
                break

        if center_val == 0:
            t = center_time
            assigned_capacity = required_capacity / t
            if t not in model:
                model[t] = grb.Model()
                model[t] = Optimize(model[t], assigned_capacity, t)

            if model[t].getAttr("Status") == grb.GRB.OPTIMAL:
                # print("center t: %d, optimal value:\t%8.4f" % (t, model[t].ObjVal))
                f = open("adjust_speed_slope.csv", 'a')
                f.write("%d %f\n" % (t, model[t].ObjVal))
                f.close()
                center_val = model[t].ObjVal
            else:
                optimal_time = -1
                break

        if right_val == 0:
            t = min(center_time + delta, end_time_sol)
            assigned_capacity = required_capacity / t
            if t not in model:
                model[t] = grb.Model()
                model[t] = Optimize(model[t], assigned_capacity, t)

            if model[t].getAttr("Status") == grb.GRB.OPTIMAL:
                # print("right t: %d, optimal value:\t%8.4f" % (t, model[t].ObjVal))
                f = open("adjust_speed_slope.csv", 'a')
                f.write("%d %f\n" % (t, model[t].ObjVal))
                f.close()
                right_val = model[t].ObjVal
            else:
                optimal_time = -1
                break

        if left_val < center_val < right_val:
            # 単調増加
            shift_direction = -1
        elif left_val > center_val > right_val:
            # 単調減少
            shift_direction = 1
        elif left_val == center_val or center_val == right_val:
            shift_direction = 0
        elif left_val > center_val and right_val > center_val:
            shift_direction = 0

        if shift_direction == 1:
            if center_time + delta >= end_time_sol:
                # 関数全体が単調減少
                minimum_cost = right_val
                optimal_time = end_time_sol
                break
            center_time = center_time + delta
            left_val = center_val
            center_val = right_val
            right_val = 0
        elif shift_direction == -1:
            if center_time - delta <= start_time_sol:
                # 関数全体が単調増加
                minimum_cost = left_val
                optimal_time = start_time_sol
                break
            center_time = center_time - delta
            right_val = center_val
            center_val = left_val
            left_val = 0
        elif shift_direction == 0:
            left_val = 0
            right_val = 0
            delta = math.floor(delta / 2)
            minimum_cost = center_val
            optimal_time = center_time

stop = time.time()
print("minimum cost %.5f time: %d" % (minimum_cost, optimal_time))
print("elapsed_time %.5f sec" % (stop - start))
