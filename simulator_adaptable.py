import random as rnd
import math
import sys
import numpy
import pickle
import copy
import gurobipy as grb
import time as tm
import route_calc_variables

from numba.tests.test_utils import D

from link import Link
from traffic import Traffic
from traffic import RouteCalcType
from define import Define
from active_traffic import ActiveTraffic
from solution import Solution

# Define
LOG_FILE = "log.txt"
LOG_FILE2 = "log2.txt"
LOG_FILE3 = "log3.txt"
LOG_FILE4 = "log4.txt"
RESULT_FILE = "result.txt"
CPLEX_PATH = "cplex"
CPLEX_LP = "cplex.lp"
CPLEX_SCRIPT = "cplex.txt"


def write_log(msg):
    try:
        f = open(LOG_FILE, 'a')
        f.write(msg)
        f.close()
    except IOError as e:
        print('except: Cannot open "{0}"'.format(LOG_FILE), file=sys.stderr)
        print('  errno: [{0}] msg: [{1}]'.format(e.errno, e.strerror), file=sys.stderr)
        write_log(msg)


def write_log2(msg):
    # return
    try:
        f = open(LOG_FILE2, 'a')
        f.write(msg)
        f.close()
    except IOError as e:
        print('except: Cannot open "{0}"'.format(LOG_FILE2), file=sys.stderr)
        print('  errno: [{0}] msg: [{1}]'.format(e.errno, e.strerror), file=sys.stderr)
        write_log2(msg)


def write_log3(msg):
    # return
    try:
        f = open(LOG_FILE3, 'a')
        f.write(msg)
        f.close()
    except IOError as e:
        print('except: Cannot open "{0}"'.format(LOG_FILE3), file=sys.stderr)
        print('  errno: [{0}] msg: [{1}]'.format(e.errno, e.strerror), file=sys.stderr)
        write_log3(msg)


def write_log4(msg):
    # return
    try:
        f = open(LOG_FILE4, 'a')
        f.write(msg)
        f.close()
    except IOError as e:
        print('except: Cannot open "{0}"'.format(LOG_FILE4), file=sys.stderr)
        print('  errno: [{0}] msg: [{1}]'.format(e.errno, e.strerror), file=sys.stderr)
        write_log4(msg)


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


def show_links_wR(p_link_list, holding_time):
    """

    :param holding_time:
    :type holding_time: int
    :param p_link_list:
    :type p_link_list: dict[(int, int),Link]
    """
    bandwidth_str = ""
    for key, link in p_link_list.items():
        if type(link) == Link and link.failure_status == 0:
            bandwidth_str += "%d %d %d %f\n" % (
                key[0], key[1], link.bandwidth, link.calculate_reliability(holding_time))

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
active_traffic_list4 = []  # type: list[ActiveTraffic]
current_link_list = copy.deepcopy(link_list)
current_link_list2 = copy.deepcopy(link_list)
current_link_list3 = copy.deepcopy(link_list)
current_link_list4 = copy.deepcopy(link_list)

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
blocked_bandwidth4 = 0
blocked_demand4 = 0
request_achieved_demand4 = 0
total_expected_bandwidth4 = 0
total_requested_expected_bandwidth4 = 0
total_data_achieved_demand = 0
total_data_achieved_demand2 = 0
total_data_achieved_demand3 = 0
total_data_achieved_demand4 = 0

while True:
    write_log("\nSimulation Time: %d\n" % time)
    write_log2("\nSimulation Time: %d\n" % time)
    write_log3("\nSimulation Time: %d\n" % time)
    write_log4("\nSimulation Time: %d\n" % time)

    # リンク障害判定
    Link.process_link_status(current_link_list, current_link_list2, current_link_list3, current_link_list4,
                             active_traffic_list, active_traffic_list2, active_traffic_list3, active_traffic_list4,
                             AVERAGE_REPAIRED_TIME)

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
                write_log("[Achieve Total Data Failed(%d)] %d->%d (%d, %f, %d) %d\n" % (active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                                                                                        active_traffic.traffic.bandwidth, active_traffic.traffic.quality, active_traffic.traffic.holding_time,
                                                                                        total_bandwidth))
            active_traffic_list.remove(active_traffic)
    write_log(show_links(current_link_list))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:
            if traffic_item.id % (TOTAL_TRAFFIC / 100) == 0:
                print(traffic_item.id)

            model_list = {}
            variable_list = {}
            solution = Solution()
            current_available_link_list = []  # type: list[tuple[int, int]]
            K = range(1, MAX_ROUTE + 1)

            # ルート計算
            actual_holding_time = traffic_item.CalcRoute(solution, RouteCalcType.ExpectedCapacityGuarantee, MAX_ROUTE, node_size, current_link_list, current_available_link_list)
            if not actual_holding_time:
                print("Undefined route calculation type\n")
                exit(-1)

            if solution.isOptimized():
                routes = [{} for i in range(MAX_ROUTE)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if solution.variables["b"][k] != 0:
                        for (i, j) in current_available_link_list:
                            if solution.variables["y"][(k, i, j)] != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list[(i, j)].distance, solution.variables["y"][(k, i, j)], current_link_list[(i, j)].failure_rate, 0)
                total_requested_expected_bandwidth += traffic_item.bandwidth * traffic_item.quality
                write_log("[Accepted(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + actual_holding_time, actual_holding_time, copy.copy(traffic_item), [])
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
                write_log(show_links_wR(current_link_list, actual_holding_time))
                write_log("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth += traffic_item.bandwidth
                blocked_demand += 1
    # 期待値保証型処理完了

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
            else:
                write_log2("[Achieve Total Data Failed(%d)] %d->%d (%d, %f, %d) %d\n" % (active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                                                                                         active_traffic.traffic.bandwidth, active_traffic.traffic.quality, active_traffic.traffic.holding_time,
                                                                                         total_bandwidth))
            active_traffic_list2.remove(active_traffic)
    write_log2(show_links(current_link_list2))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:
            solution = Solution()
            current_available_link_list = []  # type: list[tuple[int, int]]
            K = range(1, MAX_ROUTE + 1)

            # ルート計算
            actual_holding_time = traffic_item.CalcRoute(solution, RouteCalcType.MinCostFlow, MAX_ROUTE, node_size, current_link_list2, current_available_link_list)
            if not actual_holding_time:
                print("Undefined route calculation type\n")
                exit(-1)

            if solution.isOptimized():
                routes = [{} for i in range(MAX_ROUTE)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if solution.variables["b"][k] != 0:
                        for (i, j) in current_available_link_list:
                            if solution.variables["y"][(k, i, j)] != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list2[(i, j)].distance, solution.variables["y"][(k, i, j)], current_link_list2[(i, j)].failure_rate, 0)
                total_requested_expected_bandwidth2 += traffic_item.bandwidth * traffic_item.quality
                write_log2("[Accepted(%d)] %d->%d (%d, %f)\n" % (traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth, traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + actual_holding_time, actual_holding_time, copy.copy(traffic_item), [])
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
                write_log2(show_links_wR(current_link_list, actual_holding_time))
                write_log2("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth2 += traffic_item.bandwidth
                blocked_demand2 += 1
    # 最小費用流処理完了

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
            else:
                write_log3("[Achieve Total Data Failed(%d)] %d->%d (%d, %f, %d) %d\n" % (active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                                                                                         active_traffic.traffic.bandwidth, active_traffic.traffic.quality, active_traffic.traffic.holding_time,
                                                                                         total_bandwidth))
            active_traffic_list3.remove(active_traffic)
    write_log3(show_links(current_link_list3))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:
            solution = Solution()
            current_available_link_list = []  # type: list[tuple[int, int]]
            K = range(1, 2 + 1)

            # ルート計算
            actual_holding_time = traffic_item.CalcRoute(solution, RouteCalcType.Backup, 2, node_size, current_link_list3, current_available_link_list)
            if not actual_holding_time:
                print("Undefined route calculation type\n")
                exit(-1)

            if solution.isOptimized():
                routes = [{} for i in range(2)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if solution.variables["b"][k] != 0:
                        for (i, j) in current_available_link_list:
                            if solution.variables["y"][(k, i, j)] != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list3[(i, j)].distance,
                                                             solution.variables["y"][(k, i, j)],
                                                             current_link_list3[(i, j)].failure_rate,
                                                             0)
                total_requested_expected_bandwidth3 += traffic_item.bandwidth * traffic_item.quality
                write_log3("[Accepted(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + actual_holding_time, actual_holding_time, copy.copy(traffic_item), [])
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
                write_log3(show_links_wR(current_link_list, actual_holding_time))
                write_log3("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth3 += traffic_item.bandwidth
                blocked_demand3 += 1
    # バックアップ処理完了

    # 使用可能容量加算
    for active_traffic_item in active_traffic_list4[:]:
        expected_bandwidth = active_traffic_item.traffic.bandwidth * active_traffic_item.traffic.quality  # 帯域幅期待値
        total_bandwidth = 0
        for route in active_traffic_item.routes[:]:
            for route_link_key, route_link_item in route.items():
                total_bandwidth += route_link_item.bandwidth
                break
        active_traffic_item.traffic.total_data += total_bandwidth
        write_log4("[Total Data(%d)] %d->%d %d\n" % (
            active_traffic_item.traffic.id, active_traffic_item.traffic.start_node, active_traffic_item.traffic.end_node, active_traffic_item.traffic.total_data))

    # 回線使用終了判定(アダプタブル期待値保証型)
    for active_traffic in active_traffic_list4[:]:
        if active_traffic.end_time <= time:
            # 回線使用終了
            expected_bandwidth = active_traffic.traffic.bandwidth * active_traffic.traffic.quality
            total_bandwidth = 0
            for route in active_traffic.routes:
                for used_link_key, used_link_item in route.items():
                    current_link_list4[(used_link_key[0], used_link_key[1])].bandwidth += used_link_item.bandwidth
                    total_bandwidth += used_link_item.bandwidth
                    write_log4("Link %d->%d add bandwidth: %d\n" % (used_link_key[0], used_link_key[1], used_link_item.bandwidth))

            if total_bandwidth >= expected_bandwidth:
                request_achieved_demand4 += 1
                write_log4("[End(%d)] %d->%d (%d, %f), %d\n" % (
                    active_traffic.traffic.id, active_traffic.traffic.start_node,
                    active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality,
                    active_traffic.end_time))
            else:
                write_log4("[End with Bandwidth Lowering(%d)] %d->%d (%d, %f)->%d, %d\n" % (
                    active_traffic.traffic.id, active_traffic.traffic.start_node,
                    active_traffic.traffic.end_node,
                    active_traffic.traffic.bandwidth, active_traffic.traffic.quality, total_bandwidth,
                    active_traffic.end_time))
            if active_traffic.traffic.total_data >= active_traffic.traffic.bandwidth * active_traffic.traffic.quality * active_traffic.traffic.holding_time:
                total_data_achieved_demand4 += 1
            else:
                write_log4("[Achieve Total Data Failed(%d)] %d->%d (%d, %f, %d) %d\n" % (active_traffic.traffic.id, active_traffic.traffic.start_node, active_traffic.traffic.end_node,
                                                                                         active_traffic.traffic.bandwidth, active_traffic.traffic.quality, active_traffic.traffic.holding_time,
                                                                                         total_bandwidth))
            active_traffic_list4.remove(active_traffic)
    write_log4(show_links(current_link_list4))
    if len(traffic_list) > 0:
        for traffic_item in traffic_list[0]:
            solution = Solution()
            current_available_link_list = []  # type: list[tuple[int, int]]
            K = range(1, MAX_ROUTE + 1)

            # ルート計算
            actual_holding_time = traffic_item.CalcRoute(solution, RouteCalcType.AdaptableExpectedCapacityGurantee, MAX_ROUTE, node_size, current_link_list4, current_available_link_list)
            if not actual_holding_time:
                print("Undefined route calculation type\n")
                exit(-1)

            if solution.isOptimized():
                routes = [{} for i in range(MAX_ROUTE)]  # type: list[dict[tuple[int, int], Link]]
                for k in K:
                    if solution.variables["b"][k] != 0:
                        for (i, j) in current_available_link_list:
                            if solution.variables["y"][(k, i, j)] != 0:
                                routes[k - 1][(i, j)] = Link(current_link_list4[(i, j)].distance,
                                                             solution.variables["y"][(k, i, j)],
                                                             current_link_list4[(i, j)].failure_rate,
                                                             0)
                total_requested_expected_bandwidth4 += traffic_item.bandwidth * traffic_item.quality
                write_log4("[Accepted(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                # ルート使用処理
                route_cnt = 0
                active_traffic = ActiveTraffic(time + actual_holding_time, actual_holding_time, copy.copy(traffic_item), [])
                for route in routes:
                    route_reliability = 1
                    if len(route) > 0:
                        route_cnt += 1
                        route_bandwidth = 0
                        for (i, j), link in route.items():
                            route_bandwidth = link.bandwidth
                            current_link_list4[(i, j)].bandwidth -= link.bandwidth
                            route_reliability *= current_link_list4[(i, j)].calculate_reliability(
                                traffic_item.holding_time)
                            write_log4("Link %d->%d remove bandwidth: %d\n" % (i, j, link.bandwidth))
                        active_traffic.routes.append(route)
                        total_expected_bandwidth4 += route_reliability * route_bandwidth
                active_traffic_list4.append(active_traffic)
            else:
                # 最適解なし
                # print("Blocked4")
                write_log4(show_links_wR(current_link_list, actual_holding_time))
                write_log4("[Blocked(%d)] %d->%d (%d, %f)\n" % (
                    traffic_item.id, traffic_item.start_node, traffic_item.end_node, traffic_item.bandwidth,
                    traffic_item.quality))
                blocked_bandwidth4 += traffic_item.bandwidth
                blocked_demand4 += 1
    # アダプタブル期待値保証型処理完了

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
write_log4(
    "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\n"
    % (blocked_demand4, blocked_demand4 * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth4,
       request_achieved_demand4, request_achieved_demand4 * 100 / (TOTAL_TRAFFIC - blocked_demand4),
       total_expected_bandwidth4, total_requested_expected_bandwidth4))

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
    f.write("Adaptable\n")
    f.write(
        "Blocked demand:%d(%d%%)\nTotal bandwidth: %d\nBlocked bandwidth: %d(%d%%)\nBandwidth achieved demand: %d(%d%%)\nTotal expected bandwidth: %d\nTotal requested expected bandwidth: %d\nTotal data achieved demand: %d\n"
        % (blocked_demand4, blocked_demand4 * 100 / TOTAL_TRAFFIC, total_requested_bandwidth, blocked_bandwidth4,
           blocked_bandwidth4 / total_requested_bandwidth * 100,
           request_achieved_demand4, request_achieved_demand4 * 100 / (TOTAL_TRAFFIC - blocked_demand4),
           total_expected_bandwidth4, total_requested_expected_bandwidth4, total_data_achieved_demand4))

end_time = tm.time()

print('Elapsed Time: %f' % (end_time - start_time))
