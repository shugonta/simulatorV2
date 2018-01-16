import random as rnd
import math
import sys
import numpy
import pickle
import copy
import gurobipy as grb
import time as tm

from numba.tests.test_utils import D

from link import Link
from traffic import Traffic
from define import Define
from active_traffic import ActiveTraffic

# Define
LOG_FILE = "log.txt"
LOG_FILE2 = "log2.txt"
LOG_FILE3 = "log3.txt"
RESULT_FILE = "result.txt"
CPLEX_PATH = "cplex"
CPLEX_LP = "cplex.lp"
CPLEX_SCRIPT = "cplex.txt"


def write_log(msg):
    return
    f = open(LOG_FILE, 'a')
    f.write(msg)
    f.close()


def write_log2(msg):
    return
    f = open(LOG_FILE2, 'a')
    f.write(msg)
    f.close()


def write_log3(msg):
    return
    f = open(LOG_FILE3, 'a')
    f.write(msg)
    f.close()


def is_failure(p_failure_rate):
    random = rnd.random()
    return p_failure_rate > random


def is_repaired(p_ave_repaired_time, p_failure_time):
    repaire_probability = 1.0 - math.exp(-1.0 * (1.0 / p_ave_repaired_time) * p_failure_time)
    random = rnd.random()
    return repaire_probability > random


def show_links(p_link_list):
    """

    :param p_link_list:
    :type p_link_list: dict[(int, int),Link]
    """
    bandwidth_str = ""
    for key, link in p_link_list.items():
        if type(link) == Link and link.failure_status == 0:
            bandwidth_str += "%d %d %d\n" % (key[0], key[1], link.bandwidth)

    return bandwidth_str


def show_links_wR(p_link_list, p_traffic_item):
    """

    :param p_traffic_item:
    :type p_traffic_item: Traffic
    :param p_link_list:
    :type p_link_list: dict[(int, int),Link]
    """
    bandwidth_str = ""
    for key, link in p_link_list.items():
        if type(link) == Link and link.failure_status == 0:
            bandwidth_str += "%d %d %d %f\n" % (
                key[0], key[1], link.bandwidth, link.calculate_reliability(p_traffic_item.holding_time))

    return bandwidth_str


def get_failure_rate_rand():
    i = rnd.randint(0, 2)
    if i == 0:
        return 0.01
    if i == 1:
        return 0.03
    if i == 2:
        return 0.05
    else:
        return 0.01


def get_shape():
    return 5


def get_scale_rand():
    return 20
    # i = rnd.randint(0, 2)
    # if i == 0:
    #     return 100
    # if i == 1:
    #     return 33
    # if i == 2:
    #     return 20
    # else:
    #     return 100


start_time = tm.time()

# ファイルからオブジェクト読み込み
with open('define.dat', 'rb') as f:
    define = pickle.load(f)  # type: Define
    if type(define) is not Define:
        print("define.dat is invalid.")
        exit(-1)

with open('link_list.dat', 'rb') as f:
    link_list = pickle.load(f)  # type: dict[tuple[int, int], Link]
    if type(link_list) is not dict:
        print("link_list.dat is invalid.")
        exit(-1)

with open('traffic_list.dat', 'rb') as f:
    traffic_list = pickle.load(f)  # type: list[list[Traffic]]
    if type(traffic_list) is not list:
        print("traffic_list.dat is invalid.")
        exit(-1)

TOTAL_TRAFFIC = define.total_traffic
MAX_ROUTE = define.max_route
AVERAGE_REPAIRED_TIME = define.avg_repaired_time

total_requested_bandwidth = 0
for traffic_sec_list in traffic_list:
    for traffic_item in traffic_sec_list:  # type: Traffic
        total_requested_bandwidth += traffic_item.bandwidth

print(total_requested_bandwidth)

active_traffic_list = []  # type: list[ActiveTraffic]
active_traffic_list2 = []  # type: list[ActiveTraffic]
active_traffic_list3 = []  # type: list[ActiveTraffic]
current_link_list = copy.deepcopy(link_list)
current_link_list2 = copy.deepcopy(link_list)
current_link_list3 = copy.deepcopy(link_list)

node_size = define.node_size

time = 0
blocked_bandwidth = 0
blocked_demand = 0
request_achieved_demand = 0
total_expected_bandwidth = 0
total_requested_expected_bandwidth = 0
blocked_bandwidth2 = 0
blocked_demand2 = 0
request_achieved_demand2 = 0
total_expected_bandwidth2 = 0
total_requested_expected_bandwidth2 = 0
blocked_bandwidth3 = 0
blocked_demand3 = 0
request_achieved_demand3 = 0
total_expected_bandwidth3 = 0
total_requested_expected_bandwidth3 = 0
total_data_achieved_demand = 0
total_data_achieved_demand2 = 0
total_data_achieved_demand3 = 0

while True:
    write_log("\nSimulation Time: %d\n" % time)
    write_log2("\nSimulation Time: %d\n" % time)
    write_log3("\nSimulation Time: %d\n" % time)

    # リンク障害判定
    for link_item_key, link_item in current_link_list.items():
        if link_item is not None:
            if link_item.failure_status == 0:
                # リンク故障していないとき
                # リンク故障率更新
                link_item.update_link_failure_rate()
                # if link_item_key[0] == 1 and link_item_key[1] == 2:
                #     print("age:%d, failure_rate:%f" % (link_item.age, link_item.failure_rate))

                if is_failure(link_item.failure_rate):
                    # リンク故障判定
                    link_item.failure_status += 1
                    write_log("[Link failed] %d->%d\n" % (link_item_key[0], link_item_key[1]))
                    current_link_list2[(link_item_key[0], link_item_key[1])].failure_status += 1
                    write_log2("[Link failed] %d->%d\n" % (link_item_key[0], link_item_key[1]))
                    current_link_list3[(link_item_key[0], link_item_key[1])].failure_status += 1
                    write_log3("[Link failed] %d->%d\n" % (link_item_key[0], link_item_key[1]))
                    # 使用中リンクのダウン設定(期待値型ルーティング)
                    for active_traffic_item in active_traffic_list:
                        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
                        total_bandwidth = 0
                        for route in active_traffic_item.routes[:]:
                            del_flag = False
                            route_bandwidth = 0
                            for route_link_key, route_link_item in route.items():
                                route_bandwidth = route_link_item.bandwidth
                                if link_item_key[0] == route_link_key[0] and link_item_key[1] == route_link_key[1]:
                                    for failed_route_link_key, failed_route_link in route.items():
                                        # 故障したリンクの存在するルートのすべてのリンクの使用を中断、使用帯域幅解放
                                        current_link_list[(failed_route_link_key[0], failed_route_link_key[1])].bandwidth += failed_route_link.bandwidth
                                        write_log("Link %d->%d add bandwidth: %d\n" % (failed_route_link_key[0], failed_route_link_key[1], failed_route_link.bandwidth))
                                    del_flag = True
                                    break
                            if del_flag:
                                active_traffic_item.routes.remove(route)
                            else:
                                total_bandwidth += route_bandwidth
                                # if total_bandwidth < expected_bandwidth:
                                #     write_log("[Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d\n"
                                #               % (active_traffic_item.traffic.id, active_traffic_item.traffic.start_node,
                                #                  active_traffic_item.traffic.end_node, active_traffic_item.traffic.bandwidth,
                                #                  active_traffic_item.traffic.quality, total_bandwidth))

                    # 使用中リンクのダウン設定(最小費用流)
                    for active_traffic_item in active_traffic_list2:
                        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
                        total_bandwidth = 0
                        for route in active_traffic_item.routes[:]:
                            del_flag = False
                            route_bandwidth = 0
                            for route_link_key, route_link_item in route.items():
                                route_bandwidth = route_link_item.bandwidth
                                if link_item_key[0] == route_link_key[0] and link_item_key[1] == route_link_key[1]:
                                    for failed_route_link_key, failed_route_link in route.items():
                                        # 故障したリンクの存在するルートのすべてのリンクの使用を中断、使用帯域幅解放
                                        current_link_list2[(failed_route_link_key[0], failed_route_link_key[1])].bandwidth += failed_route_link.bandwidth
                                        write_log2("Link %d->%d add bandwidth: %d\n" % (failed_route_link_key[0], failed_route_link_key[1], failed_route_link.bandwidth))
                                    del_flag = True
                                    break
                            if del_flag:
                                active_traffic_item.routes.remove(route)
                            else:
                                total_bandwidth += route_bandwidth
                                # if total_bandwidth < expected_bandwidth:
                                #     write_log2("[Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d\n" % (
                                #         active_traffic_item.traffic.id, active_traffic_item.traffic.start_node, active_traffic_item.traffic.end_node, active_traffic_item.traffic.bandwidth,
                                #         active_traffic_item.traffic.quality, total_bandwidth))

                    # 使用中リンクのダウン設定(バックアップ)
                    for active_traffic_item in active_traffic_list3:
                        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
                        total_bandwidth = 0
                        for route in active_traffic_item.routes[:]:
                            del_flag = False
                            route_bandwidth = 0
                            for route_link_key, route_link_item in route.items():
                                route_bandwidth = route_link_item.bandwidth
                                if link_item_key[0] == route_link_key[0] and link_item_key[1] == route_link_key[1]:
                                    for failed_route_link_key, failed_route_link in route.items():
                                        # 故障したリンクの存在するルートのすべてのリンクの使用を中断、使用帯域幅解放
                                        current_link_list3[(failed_route_link_key[0], failed_route_link_key[1])].bandwidth += failed_route_link.bandwidth
                                        write_log3("Link %d->%d add bandwidth: %d\n" % (
                                            failed_route_link_key[0], failed_route_link_key[1],
                                            failed_route_link.bandwidth))
                                    del_flag = True
                                    break
                            if del_flag:
                                active_traffic_item.routes.remove(route)
                            else:
                                total_bandwidth += route_bandwidth
                                # if total_bandwidth < expected_bandwidth:
                                #     write_log3("[Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d\n"
                                #                % (
                                #                    active_traffic_item.traffic.id, active_traffic_item.traffic.start_node,
                                #                    active_traffic_item.traffic.end_node,
                                #                    active_traffic_item.traffic.bandwidth,
                                #                    active_traffic_item.traffic.quality, total_bandwidth))
                else:
                    # 年齢加算
                    link_item.add_age()
            else:
                # リンク故障しているとき
                if is_repaired(AVERAGE_REPAIRED_TIME, link_item.failure_status):
                    new_shape = get_shape()
                    new_scale = get_scale_rand()
                    # 復旧(使用帯域幅解放は実行済み)
                    # リンク故障率再設定
                    write_log("[Link repaired] %d->%d\n" % (link_item_key[0], link_item_key[1]))
                    link_item.reset(new_shape, new_scale)
                    write_log2("[Link repaired] %d->%d\n" % (link_item_key[0], link_item_key[1]))
                    current_link_list2[(link_item_key[0], link_item_key[1])].reset(new_shape, new_scale)
                    write_log3("[Link repaired] %d->%d\n" % (link_item_key[0], link_item_key[1]))
                    current_link_list3[(link_item_key[0], link_item_key[1])].reset(new_shape, new_scale)
                else:
                    link_item.failure_status += 1
                    current_link_list2[(link_item_key[0], link_item_key[1])].failure_status += 1
                    current_link_list3[(link_item_key[0], link_item_key[1])].failure_status += 1

    # 使用可能容量加算
    for active_traffic_item in active_traffic_list[:]:
        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
        total_bandwidth = 0
        for route in active_traffic_item.routes[:]:
            for route_link_key, route_link_item in route.items():
                total_bandwidth += route_link_item.bandwidth
                break
        active_traffic_item.traffic.total_data += total_bandwidth
        write_log("[Total Data(%d)] %d->%d %d\n" % (
            active_traffic_item.traffic.id, active_traffic_item.traffic.start_node, active_traffic_item.traffic.end_node, active_traffic_item.traffic.total_data))

    for active_traffic in active_traffic_list[:]:
        if active_traffic.end_time <= time:
            # 回線使用終了
            expected_bandwidth = active_traffic.traffic.bandwidth * active_traffic.traffic.quality
            total_bandwidth = 0
            for route in active_traffic.routes:
                for used_link_key, used_link_item in route.items():
                    current_link_list[(used_link_key[0], used_link_key[1])].bandwidth += used_link_item.bandwidth
                    total_bandwidth += used_link_item.bandwidth
                    write_log("Link %d->%d add bandwidth: %d\n" % (
                        used_link_key[0], used_link_key[1], used_link_item.bandwidth))

            if total_bandwidth >= expected_bandwidth:
                request_achieved_demand += 1
                write_log("[End(%d)] %d->%d (%d, %f), %d\n" % (
                    active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality, active_traffic.end_time))
            else:
                write_log("[End with Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d, %d\n" % (
                    active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality, total_bandwidth,
                    active_traffic.end_time))
            if active_traffic.traffic.total_data >= active_traffic.traffic.bandwidth * active_traffic.traffic.quality * active_traffic.traffic.holding_time:
                total_data_achieved_demand += 1
            else:
                write_log("[Achieve Total Data Failed(%d)] %d->%d (%d, %f, %d) %d\n" % ( active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality, active_traffic.traffic.holding_time, total_bandwidth))
            active_traffic_list.remove(active_traffic)
    write_log(show_links(current_link_list))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:
            if traffic_item.id % (TOTAL_TRAFFIC / 100) == 0:
                print(traffic_item.id)

            M = MAX_ROUTE  # 経路数
            p = traffic_item.start_node  # 起点
            q = traffic_item.end_node  # 終点
            required_capacity = traffic_item.bandwidth
            quality = traffic_item.quality

            K = range(1, M + 1)
            nodes = range(1, node_size + 1)
            bandwidth_max = 0

            # print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
            m = grb.Model()
            m.setParam('OutputFlag', 0)
            # 変数は辞書型変数に格納
            x = {}
            y = {}
            b = {}

            # 変数追加
            current_available_link_list = []  # type: list[tuple[int, int]]
            for (i, j), link_item in current_link_list.items():
                if link_item.failure_status == 0:
                    bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                    current_available_link_list.append((i, j))
                    for k in K:
                        x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                        y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="y_{%d,%d,%d}" % (k, i, j))
            for k in K:
                b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

            m.update()  # モデルに変数が追加されたことを反映させる

            # 目的関数を設定し，最小化を行うことを明示する
            m.setObjective(grb.quicksum(
                grb.quicksum(y[k, i, j] * current_link_list[(i, j)].bandwidth for (i, j) in current_available_link_list)
                for k in K),
                grb.GRB.MINIMIZE)  # 目的関数
            # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

            # 制約追加
            for i in nodes:
                if i == p:
                    for k in K:
                        m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in current_available_link_list) \
                                    - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in current_available_link_list) \
                                    == 1, name="flow reservation at node %d route %d" % (i, k))
                if i != p and i != q:
                    for k in K:
                        m.addConstr(grb.quicksum(x[k, i, j] for j in nodes if (i, j) in current_available_link_list) \
                                    - grb.quicksum(x[k, j, i] for j in nodes if (j, i) in current_available_link_list) \
                                    == 0, name="flow reservation at node %d route %d" % (i, k))

            for (i, j) in current_available_link_list:
                m.addConstr(
                    0 <= grb.quicksum(y[k, i, j] for k in K) <= min(current_link_list[(i, j)].bandwidth,
                                                                    required_capacity),
                    name="capacity requirement at (%d, %d)" % (i, j))

            m.addConstr(grb.quicksum(b[k] for k in K) >= required_capacity, name="required capacity requirement")
            m.addConstr(grb.quicksum(b[k] for k in K) \
                        - grb.quicksum(
                grb.quicksum(
                    (1 - current_link_list[(i, j)].calculate_reliability(traffic_item.holding_time)) *
                    y[k, i, j] \
                    for (i, j) in current_available_link_list) for k in \
                K) >= quality * required_capacity,
                        name="expected capacity requirement")

            for k in K:
                for (i, j) in current_available_link_list:
                    m.addConstr(y[k, i, j] >= b[k] + (bandwidth_max * (x[k, i, j] - 1)),
                                name="st1 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(y[k, i, j] <= current_link_list[(i, j)].bandwidth * x[k, i, j],
                                name="st2 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

            # モデルに制約条件が追加されたことを反映させる
            m.update()
            # 最適化を行い，結果を表示させる
            # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

            m.optimize()

            if m.getAttr("Status") == grb.GRB.OPTIMAL:
                routes = [{} for i in range(MAX_ROUTE)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if b[k].X != 0:
                        for (i, j) in current_available_link_list:
                            if y[(k, i, j)].X != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list[(i, j)].distance,
                                                             y[(k, i, j)].X,
                                                             current_link_list[(i, j)].failure_rate,
                                                             0)
                total_requested_expected_bandwidth += traffic_item.bandwidth * traffic_item.quality
                write_log("[Accepted(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + traffic_item.holding_time, copy.copy(traffic_item), [])
                for route in routes:
                    route_reliability = 1
                    if len(route) > 0:
                        route_cnt += 1
                        route_bandwidth = 0
                        for (i, j), link in route.items():
                            route_bandwidth = link.bandwidth
                            current_link_list[(i, j)].bandwidth -= link.bandwidth
                            route_reliability *= current_link_list[(i, j)].calculate_reliability(
                                traffic_item.holding_time)
                            write_log("Link %d->%d remove bandwidth: %d\n" % (i, j, link.bandwidth))
                        active_traffic.routes.append(route)
                        total_expected_bandwidth += route_reliability * route_bandwidth
                active_traffic_list.append(active_traffic)
            else:
                # 最適解なし
                # print("Blocked")
                write_log(show_links_wR(current_link_list, traffic_item))
                write_log("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth += traffic_item.bandwidth
                blocked_demand += 1

    # 使用可能容量加算
    for active_traffic_item in active_traffic_list2[:]:
        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
        total_bandwidth = 0
        for route in active_traffic_item.routes[:]:
            for route_link_key, route_link_item in route.items():
                total_bandwidth += route_link_item.bandwidth
                break
        active_traffic_item.traffic.total_data += total_bandwidth
        write_log2("[Total Data(%d)] %d->%d %d\n" % (
            active_traffic_item.traffic.id, active_traffic_item.traffic.start_node, active_traffic_item.traffic.end_node, active_traffic_item.traffic.total_data))


    # 回線使用終了判定(最小費用)
    for active_traffic in active_traffic_list2[:]:
        if active_traffic.end_time <= time:
            # 回線使用終了
            expected_bandwidth = active_traffic.traffic.bandwidth * active_traffic.traffic.quality
            total_bandwidth = 0
            for route in active_traffic.routes:
                for used_link_key, used_link_item in route.items():
                    current_link_list2[
                        (used_link_key[0], used_link_key[1])].bandwidth += used_link_item.bandwidth
                    total_bandwidth += used_link_item.bandwidth
                    write_log2("Link %d->%d add bandwidth: %d\n" % (
                        used_link_key[0], used_link_key[1], used_link_item.bandwidth))

            if total_bandwidth >= expected_bandwidth:
                request_achieved_demand2 += 1
                write_log2("[End(%d)] %d->%d (%d, %f), %d\n" % (
                    active_traffic.traffic.id,
                    active_traffic.traffic.start_node,
                    active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality,
                    active_traffic.end_time))
            else:
                write_log2("[End with Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d, %d\n" % (
                    active_traffic.traffic.id,
                    active_traffic.traffic.start_node,
                    active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality, total_bandwidth,
                    active_traffic.end_time))
            if active_traffic.traffic.total_data >= active_traffic.traffic.bandwidth * active_traffic.traffic.quality * active_traffic.traffic.holding_time:
                total_data_achieved_demand2 += 1
            active_traffic_list2.remove(active_traffic)
    write_log2(show_links(current_link_list2))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:
            M = MAX_ROUTE  # 経路数
            p = traffic_item.start_node  # 起点
            q = traffic_item.end_node  # 終点
            required_capacity = traffic_item.bandwidth
            quality = traffic_item.quality

            K = range(1, M + 1)
            nodes = range(1, node_size + 1)
            bandwidth_max = 0

            # print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
            m = grb.Model()
            m.setParam('OutputFlag', 0)
            # 変数は辞書型変数に格納
            x = {}
            y = {}
            b = {}

            # 変数追加
            current_available_link_list = []  # type: list[tuple[int, int]]
            for (i, j), link_item in current_link_list2.items():
                if link_item.failure_status == 0:
                    bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                    current_available_link_list.append((i, j))
                    for k in K:
                        x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                        y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER,
                                              name="y_{%d,%d,%d}" % (k, i, j))
            for k in K:
                b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

            m.update()  # モデルに変数が追加されたことを反映させる

            # 目的関数を設定し，最小化を行うことを明示する
            m.setObjective(grb.quicksum(
                grb.quicksum(y[k, i, j] * current_link_list2[(i, j)].bandwidth for (i, j) in
                             current_available_link_list)
                for k in K),
                grb.GRB.MINIMIZE)  # 目的関数
            # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

            # 制約追加
            for i in nodes:
                if i == p:
                    for k in K:
                        m.addConstr(
                            grb.quicksum(x[k, i, j] for j in nodes if (i, j) in current_available_link_list) \
                            - grb.quicksum(
                                x[k, j, i] for j in nodes if (j, i) in current_available_link_list) \
                            == 1, name="flow reservation at node %d route %d" % (i, k))
                if i != p and i != q:
                    for k in K:
                        m.addConstr(
                            grb.quicksum(x[k, i, j] for j in nodes if (i, j) in current_available_link_list) \
                            - grb.quicksum(
                                x[k, j, i] for j in nodes if (j, i) in current_available_link_list) \
                            == 0, name="flow reservation at node %d route %d" % (i, k))

            for (i, j) in current_available_link_list:
                m.addConstr(
                    0 <= grb.quicksum(y[k, i, j] for k in K) <= min(current_link_list2[(i, j)].bandwidth,
                                                                    required_capacity),
                    name="capacity requirement at (%d, %d)" % (i, j))

            for k in K:
                m.addConstr(b[k] <= required_capacity, name="route %d requirement" % k)

            m.addConstr(grb.quicksum(b[k] for k in K) >= required_capacity,
                        name="required capacity requirement")

            for k in K:
                for (i, j) in current_available_link_list:
                    m.addConstr(y[k, i, j] >= b[k] + (bandwidth_max * (x[k, i, j] - 1)),
                                name="st1 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(y[k, i, j] <= current_link_list2[(i, j)].bandwidth * x[k, i, j],
                                name="st2 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

            # モデルに制約条件が追加されたことを反映させる
            m.update()
            # 最適化を行い，結果を表示させる
            # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

            m.optimize()

            if m.getAttr("Status") == grb.GRB.OPTIMAL:
                routes = [{} for i in range(MAX_ROUTE)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if b[k].X != 0:
                        for (i, j) in current_available_link_list:
                            if y[(k, i, j)].X != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list2[(i, j)].distance,
                                                             y[(k, i, j)].X,
                                                             current_link_list2[(i, j)].failure_rate,
                                                             0)
                total_requested_expected_bandwidth2 += traffic_item.bandwidth * traffic_item.quality
                write_log2("[Accepted(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + traffic_item.holding_time, copy.copy(traffic_item), [])
                for route in routes:
                    route_reliability = 1
                    if len(route) > 0:
                        route_cnt += 1
                        route_bandwidth = 0
                        for (i, j), link in route.items():
                            route_bandwidth = link.bandwidth
                            current_link_list2[(i, j)].bandwidth -= link.bandwidth
                            route_reliability *= current_link_list2[(i, j)].calculate_reliability(
                                traffic_item.holding_time)
                            write_log2("Link %d->%d remove bandwidth: %d\n" % (i, j, link.bandwidth))
                        active_traffic.routes.append(route)
                        total_expected_bandwidth2 += route_reliability * route_bandwidth
                active_traffic_list2.append(active_traffic)
            else:
                # 最適解なし
                # print("Blocked2")
                write_log2(show_links_wR(current_link_list, traffic_item))
                write_log2("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth2 += traffic_item.bandwidth
                blocked_demand2 += 1

    # 使用可能容量加算
    for active_traffic_item in active_traffic_list3[:]:
        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
        total_bandwidth = 0
        for route in active_traffic_item.routes[:]:
            for route_link_key, route_link_item in route.items():
                total_bandwidth += route_link_item.bandwidth
                break
        active_traffic_item.traffic.total_data += total_bandwidth
        write_log3("[Total Data(%d)] %d->%d %d\n" % (
            active_traffic_item.traffic.id, active_traffic_item.traffic.start_node, active_traffic_item.traffic.end_node, active_traffic_item.traffic.total_data))

    # 回線使用終了判定(バックアップ)
    for active_traffic in active_traffic_list3[:]:
        if active_traffic.end_time <= time:
            # 回線使用終了
            expected_bandwidth = active_traffic.traffic.bandwidth * active_traffic.traffic.quality
            total_bandwidth = 0
            for route in active_traffic.routes:
                for used_link_key, used_link_item in route.items():
                    current_link_list3[
                        (used_link_key[0], used_link_key[1])].bandwidth += used_link_item.bandwidth
                    total_bandwidth += used_link_item.bandwidth
                    write_log3("Link %d->%d add bandwidth: %d\n" % (
                        used_link_key[0], used_link_key[1], used_link_item.bandwidth))

            if total_bandwidth >= expected_bandwidth:
                request_achieved_demand3 += 1
                write_log3("[End(%d)] %d->%d (%d, %f), %d\n" % (
                    active_traffic.traffic.id, active_traffic.traffic.start_node,
                    active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality,
                    active_traffic.end_time))
            else:
                write_log3("[End with Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d, %d\n" % (
                    active_traffic.traffic.id, active_traffic.traffic.start_node,
                    active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality, total_bandwidth,
                    active_traffic.end_time))
            if active_traffic.traffic.total_data >= active_traffic.traffic.bandwidth * active_traffic.traffic.quality * active_traffic.traffic.holding_time:
                total_data_achieved_demand3 += 1
            active_traffic_list3.remove(active_traffic)
    write_log3(show_links(current_link_list3))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:

            M = 2  # 経路数
            p = traffic_item.start_node  # 起点
            q = traffic_item.end_node  # 終点
            required_capacity = traffic_item.bandwidth
            quality = traffic_item.quality

            K = range(1, M + 1)
            nodes = range(1, node_size + 1)
            bandwidth_max = 0

            # print "%s:\t%8.4f" % (x[i, j].VarName, x[i, j].X)
            m = grb.Model()
            m.setParam('OutputFlag', 0)
            # 変数は辞書型変数に格納
            x = {}
            y = {}
            b = {}

            # 変数追加
            current_available_link_list = []  # type: list[tuple[int, int]]
            for (i, j), link_item in current_link_list3.items():
                if link_item.failure_status == 0:
                    bandwidth_max = max([link_item.bandwidth, bandwidth_max])
                    current_available_link_list.append((i, j))
                    for k in K:
                        x[k, i, j] = m.addVar(vtype=grb.GRB.BINARY, name="x_{%d,%d,%d}" % (k, i, j))
                        y[k, i, j] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER,
                                              name="y_{%d,%d,%d}" % (k, i, j))
            for k in K:
                b[k] = m.addVar(lb=0.0, vtype=grb.GRB.INTEGER, name="b_{%d}" % k)

            m.update()  # モデルに変数が追加されたことを反映させる

            # 目的関数を設定し，最小化を行うことを明示する
            m.setObjective(grb.quicksum(
                grb.quicksum(y[k, i, j] * current_link_list3[(i, j)].bandwidth for (i, j) in
                             current_available_link_list)
                for k in K),
                grb.GRB.MINIMIZE)  # 目的関数
            # m.setAttr("ModelSense", grb.GRB.MINIMIZE)

            # 制約追加
            for i in nodes:
                if i == p:
                    for k in K:
                        m.addConstr(
                            grb.quicksum(
                                x[k, i, j] for j in nodes if (i, j) in current_available_link_list) - grb.quicksum(
                                x[k, j, i] for j in nodes if (j, i) in current_available_link_list) == 1,
                            name="flow reservation at node %d route %d" % (i, k))
                if i != p and i != q:
                    for k in K:
                        m.addConstr(
                            grb.quicksum(x[k, i, j] for j in nodes if (i, j) in current_available_link_list) \
                            - grb.quicksum(
                                x[k, j, i] for j in nodes if (j, i) in current_available_link_list) \
                            == 0, name="flow reservation at node %d route %d" % (i, k))

            for (i, j) in current_available_link_list:
                m.addConstr(
                    0 <= grb.quicksum(y[k, i, j] for k in K) <= min(current_link_list3[(i, j)].bandwidth,
                                                                    required_capacity),
                    name="capacity requirement at (%d, %d)" % (i, j))

            m.addConstr(b[1] >= required_capacity, name="main route capacity requirement")

            for k in K:
                if k != 1:
                    m.addConstr(b[k] >= traffic_item.quality * traffic_item.bandwidth,
                                name="backup route capacity requirement")

            for (i, j) in current_available_link_list:
                for k1 in K:
                    for k2 in K:
                        if k1 != k2:
                            m.addConstr(x[k1, i, j] + x[k2, i, j] <= 1,
                                        name="disjoint requirement at (%d, %d) for route %d, %d" % (i, j, k1, k2))

            for k in K:
                for (i, j) in current_available_link_list:
                    m.addConstr(y[k, i, j] >= b[k] + (bandwidth_max * (x[k, i, j] - 1)),
                                name="st1 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(y[k, i, j] <= current_link_list3[(i, j)].bandwidth * x[k, i, j],
                                name="st2 at (%d, %d) route %d" % (i, j, k))
                    m.addConstr(y[k, i, j] >= 0, name="st3 at (%d, %d) route %d" % (i, j, k))

            # モデルに制約条件が追加されたことを反映させる
            m.update()
            # 最適化を行い，結果を表示させる
            # m.write("mincostflow.lp")  # mincostflow.lp というファイルに定式化されたモデルを出力する

            m.optimize()

            if m.getAttr("Status") == grb.GRB.OPTIMAL:
                routes = [{} for i in range(MAX_ROUTE)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if b[k].X != 0:
                        for (i, j) in current_available_link_list:
                            if y[(k, i, j)].X != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list3[(i, j)].distance,
                                                             y[(k, i, j)].X,
                                                             current_link_list3[(i, j)].failure_rate,
                                                             0)
                total_requested_expected_bandwidth3 += traffic_item.bandwidth * traffic_item.quality
                write_log3("[Accepted(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + traffic_item.holding_time, copy.copy(traffic_item), [])
                for route in routes:
                    route_reliability = 1
                    if len(route) > 0:
                        route_cnt += 1
                        route_bandwidth = 0
                        for (i, j), link in route.items():
                            route_bandwidth = link.bandwidth
                            current_link_list3[(i, j)].bandwidth -= link.bandwidth
                            route_reliability *= current_link_list3[(i, j)].calculate_reliability(
                                traffic_item.holding_time)
                            write_log3("Link %d->%d remove bandwidth: %d\n" % (i, j, link.bandwidth))
                        active_traffic.routes.append(route)
                        total_expected_bandwidth3 += route_reliability * route_bandwidth
                active_traffic_list3.append(active_traffic)
            else:
                # 最適解なし
                # print("Blocked3")
                write_log3(show_links_wR(current_link_list, traffic_item))
                write_log3("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth3 += traffic_item.bandwidth
                blocked_demand3 += 1

    time += 1
    if len(traffic_list) > 0:
        traffic_list.pop(0)

    if (len(traffic_list) == 0 and len(active_traffic_list) == 0 and len(active_traffic_list2) == 0 and len(
            active_traffic_list3) == 0):
        break

write_log(
    "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\n"
    % (blocked_demand, blocked_demand * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth,
       request_achieved_demand,
       (request_achieved_demand * 100 / (TOTAL_TRAFFIC - blocked_demand) if TOTAL_TRAFFIC - blocked_demand != 0 else 0),
       total_expected_bandwidth, total_requested_expected_bandwidth))

write_log2(
    "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\n"
    % (blocked_demand2, blocked_demand2 * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth2,
       request_achieved_demand2, request_achieved_demand2 * 100 / (TOTAL_TRAFFIC - blocked_demand2),
       total_expected_bandwidth2, total_requested_expected_bandwidth2))
write_log3(
    "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\n"
    % (blocked_demand3, blocked_demand3 * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth3,
       request_achieved_demand3, request_achieved_demand3 * 100 / (TOTAL_TRAFFIC - blocked_demand3),
       total_expected_bandwidth3, total_requested_expected_bandwidth3))

with open(RESULT_FILE, "a") as f:
    f.write("\n")
    f.write("Condition: Traffic demand: %d, Holding time: %d, Total traffic: %d, Max route: %d, Avg repair time: %d\n"
            % (define.traffic_demand, define.holding_time, define.total_traffic, define.max_route,
               define.avg_repaired_time))
    f.write("Propose\n")
    f.write(
        "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d(%d%%)\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\nTotal data achieved demand: %d\n"
        % (blocked_demand, blocked_demand * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth,
           blocked_bandwidth / total_requested_bandwidth * 100,
           request_achieved_demand, (request_achieved_demand * 100 / (
            TOTAL_TRAFFIC - blocked_demand) if TOTAL_TRAFFIC - blocked_demand != 0 else 0),
           total_expected_bandwidth, total_requested_expected_bandwidth, total_data_achieved_demand))
    f.write("MinCostFlow\n")
    f.write(
        "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d(%d%%)\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\nTotal data achieved demand: %d\n"
        % (blocked_demand2, blocked_demand2 * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth2,
           blocked_bandwidth2 / total_requested_bandwidth * 100,
           request_achieved_demand2, request_achieved_demand2 * 100 / (TOTAL_TRAFFIC - blocked_demand2),
           total_expected_bandwidth2, total_requested_expected_bandwidth2, total_data_achieved_demand2))
    f.write("Backup\n")
    f.write(
        "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d(%d%%)\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\nTotal data achieved demand: %d\n"
        % (blocked_demand3, blocked_demand3 * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth3,
           blocked_bandwidth3 / total_requested_bandwidth * 100,
           request_achieved_demand3, request_achieved_demand3 * 100 / (TOTAL_TRAFFIC - blocked_demand3),
           total_expected_bandwidth3, total_requested_expected_bandwidth3, total_data_achieved_demand3))

end_time = tm.time()

print('Elapsed Time: %f' % (end_time - start_time))
