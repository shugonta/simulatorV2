f = open('topology_nsf.txt', 'r')
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
        reliability[(int(data[0]), int(data[1]))] = 0.9
    line = f.readline()
f.close()

p = 1  # 起点
q = 14  # 終点

M = 3  # 経路数
K = range(1, M + 1)

required_capacity = 12
quality = 1
c_max = 13

# 各リンクの輸送費用
# distance = dict(zip(links, [3, 8, 2, 12, 2, 6]))
# 各リンクの容量
# capacity = dict(zip(links, [5, 13, 10, 9, 10, 10]))
# 各リンクの信頼度
# reliability = dict(zip(links, [0.740818221, 0.990049834, 0.990049834, 0.990049834, 0.990049834, 0.740818221]))

# Gurobi パッケージを grb という名前で import
import gurobipy as grb
import time

# print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
m = grb.Model()
# 変数は辞書型変数に格納
x = {}
y = {}
b = {}

start = time.time()
# 変数追加
for (i, j) in links:
    for k in K:
        x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
        y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="y_{%d,%d,%d}" % (k, i, j))
for k in K:
    b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

m.update()  # モデルに変数が追加されたことを反映させる
print(x)

# 目的関数を設定し，最小化を行うことを明示する
m.setObjective(grb.quicksum(grb.quicksum(y[k, i, j] * distance[i, j] for (i, j) in links) for k in K),
               grb.GRB.MINIMIZE)  # 目的関数
# m.setAttr("ModelSense", grb.GRB.MINIMIZE)

# 制約追加
for i in nodes:
    if i == p:
        for k in K:
            m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in links) \
                        - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in links) \
                        == 1, name="flow reservation at node %d route %d" % (i, k))
    if i != p and i != q:
        for k in K:
            m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in links) \
                        - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in links) \
                        == 0, name="flow reservation at node %d route %d" % (i, k))

for (i, j) in links:
    m.addConstr(0 <= grb.quicksum(y[k, i, j] for k in K) <= min(capacity[i, j], required_capacity),
                name="capacity requirement at (%d, %d)" % (i, j))

m.addConstr(grb.quicksum(b[k] for k in K) >= required_capacity, name="required capacity requirement")
m.addConstr(grb.quicksum(b[k] for k in K) \
            - grb.quicksum(
    grb.quicksum((1 - reliability[i, j]) * y[k, i, j] for (i, j) in links) for k in K) >= quality * required_capacity,
            name="expected capacity requirement")

for k in K:
    for (i, j) in links:
        m.addConstr(y[k, i, j] >= b[k] + (c_max * (x[k, i, j] - 1)), name="st1 at (%d, %d) route %d" % (i, j, k))
        m.addConstr(y[k, i, j] <= capacity[i, j] * x[k, i, j], name="st2 at (%d, %d) route %d" % (i, j, k))
        m.addConstr(y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

# モデルに制約条件が追加されたことを反映させる
m.update()
stop = time.time()
print("elapsed_time for modeling %.5f sec" % (stop - start))

# 最適化を行い，結果を表示させる
# m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

start = time.time()
m.optimize()
stop = time.time()

print("elapsed_time %.5f sec" % (stop - start))
print("optimal value:\t%8.4f" % m.ObjVal)
for k in K:
    for (i, j) in links:
        if y[k, i, j].x != 0:
            print("%s:\t%8.4f" % (y[k, i, j].VarName, y[k, i, j].X))

import cplex

start = time.time()
m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する
cpx = cplex.Cplex("mincostflow.lp")
cpx.solve()
stop = time.time()
print("elapsed_time %.5f sec" % (stop - start))
print("Solution value  = ", cpx.solution.get_objective_value())
