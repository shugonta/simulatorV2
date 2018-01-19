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

required_capacity =250
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


def Optimize(assigned_capacity, t):
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
        for n in N:
            m.addConstr(grb.quicksum(y[k, i, j] for k in K) / capacity[i, j] * z[n, i, j] <= link_used_cost_threshold[n] * z[n, i, j],
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
        for n in N:
            m.addConstr(grb.quicksum(y[k, i, j] for k in K) / capacity[i, j] * z[n, i, j] <= link_used_cost_threshold[n] * z[n, i, j],
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
        print("optimal value:\t%8.4f" % m.ObjVal)
        f = open("adjust_speed.csv", 'a')
        f.write("%d, %f\n" % (t, m.ObjVal))
        f.close()
        # for k in K:
        #     for (i, j) in links:
        #         if y[k, i, j].x != 0:
        #             print("%s:\t%8.4f" % (y[k, i, j].VarName, y[k, i, j].X))
        if m.ObjVal < minimum_cost:
            minimum_cost = m.ObjVal
            optimal_time = t
            # print("elapsed_time %.5f sec" % (stop - start))
            # for k in K:
            #     for (i, j) in links:
            #         if y[k, i, j].x != 0:
            #             print("%s:\t%8.4f" % (y[k, i, j].VarName, y[k, i, j].X))
stop = time.time()
print("minimum cost %.5f time: %d" % (minimum_cost, optimal_time))
print("elapsed_time %.5f sec" % (stop - start))

start = time.time()
minimum_cost = sys.maxsize
optimal_time = 0
start_time = 1
end_time = required_capacity
center_time = math.ceil((start_time + end_time) / 2)
delta = math.ceil((start_time + end_time) / 4)
shift_direction = 0
left_val = 0
center_val = 0
right_val = 0
while delta > 0:
    # 左側
    if left_val == 0:
        t = max(center_time - delta, start_time)
        assigned_capacity = required_capacity / t
        m = Optimize(assigned_capacity, t)

        if m.getAttr("Status") == grb.GRB.OPTIMAL:
            print("left t: %d, optimal value:\t%8.4f" % (t, m.ObjVal))
            f = open("adjust_speed.txt", 'a')
            f.write("%d %f\n" % (t, m.ObjVal))
            f.close()
            left_val = m.ObjVal
        else:
            left_val = -1

    if center_val == 0:
        t = center_time
        assigned_capacity = required_capacity / t
        m = Optimize(assigned_capacity, t)

        if m.getAttr("Status") == grb.GRB.OPTIMAL:
            print("center t: %d, optimal value:\t%8.4f" % (t, m.ObjVal))
            f = open("adjust_speed.txt", 'a')
            f.write("%d %f\n" % (t, m.ObjVal))
            f.close()
            center_val = m.ObjVal
        else:
            center_val = -1

    if right_val == 0:
        t = min(center_time + delta, end_time)
        assigned_capacity = required_capacity / t
        m = Optimize(assigned_capacity, t)

        if m.getAttr("Status") == grb.GRB.OPTIMAL:
            print("right t: %d, optimal value:\t%8.4f" % (t, m.ObjVal))
            f = open("adjust_speed_slope.csv", 'a')
            f.write("%d %f\n" % (t, m.ObjVal))
            f.close()
            right_val = m.ObjVal
        else:
            right_val = -1

    if left_val == -1 and center_val != -1 and right_val != -1 or left_val == -1 and center_val == -1 and right_val != -1 or left_val == -1 and center_val == - -1 and right_val == -1:
        # 左側に解なしが含まれるときはスタート時間を解なし+1に変更
        if right_val == -1:
            start_time = min(center_time + delta + 1, end_time)
        elif center_val == -1:
            start_time = center_time + 1
        elif left_val == -1:
            start_time = max(center_time - delta + 1, start_time + 1)
        print("start time reset : %d" % start_time)
        center_time = math.ceil((start_time + end_time) / 2)
        delta = math.ceil((start_time + end_time) / 4)
        right_val = 0
        center_val = 0
        left_val = 0
        continue
    elif left_val != -1 and center_val != -1 and right_val == -1 or left_val != -1 and center_val == -1 and right_val == -1:
        # 右側に解なしが含まれるときはエンド時間を解なし-1に変更
        if center_val == -1:
            end_time = center_time - 1
        elif right_val == -1:
            end_time = min(center_time + delta - 1, end_time - 1)
        print("end time reset : %d" % end_time)
        center_time = math.ceil((start_time + end_time) / 2)
        delta = math.ceil((start_time + end_time) / 4)
        right_val = 0
        center_val = 0
        left_val = 0
        continue
    elif left_val < center_val < right_val:
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
        if center_time + delta >= end_time:
            # 関数全体が単調減少
            minimum_cost = right_val
            optimal_time = end_time
            break
        center_time = center_time + delta
        left_val = center_val
        center_val = right_val
        right_val = 0
    elif shift_direction == -1:
        if center_time - delta <= start_time:
            # 関数全体が単調増加
            minimum_cost = left_val
            optimal_time = start_time
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
