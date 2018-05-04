import random as rnd
import math
import sys
import numpy
import pickle

from link import Link
from traffic import Traffic
from define import Define


def get_bandwidth_rand():
    i = rnd.randint(0, 2)
    if i == 0:
        return 5
    elif i == 1:
        return 10
    elif i == 2:
        return 20
    # elif i == 3:
    #     return 40
    else:
        return 10


def get_quality_rand():
    return 1


def get_nodes_rand(p_node_size):
    start_node = rnd.randint(1, p_node_size - 1)
    while True:
        end_node = rnd.randint(1, p_node_size - 1)
        if start_node != end_node:
            break
    return [start_node, end_node]
    # return [1, 7]


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
    # i = rnd.randint(0, 2)
    # if i == 0:
    #     return 100
    # if i == 1:
    #     return 33
    # if i == 2:
    #     return 20
    # else:
    #     return 100
    return 10


def get_initial_age(p_scale=0):
    if p_scale == 0:
        p_scale = get_scale_rand()
    age = rnd.randint(0, round(p_scale * numpy.random.weibull(get_shape())))
    # age = rnd.randint(0, scale)
    return age
    # return 0


def load_topology(p_file_path, p_link_list, p_scale=0):
    """

    :param p_file_path:
    :type p_file_path: str
    :param p_link_list:
    :type p_link_list: dict
    :return:
    """
    f = open(p_file_path, 'r')
    line = f.readline()  # 1行を文字列として読み込む(改行文字も含まれる)
    node_count = int(line)
    # ノード集合
    nodes = range(1, node_count + 1)
    line = f.readline()

    while line:
        data = line[:-1].split(' ')
        if len(data) == 3 and data[0].isdigit() and data[1].isdigit() and data[2].isdigit():
            if p_scale == 0:
                p_scale = get_scale_rand()
            p_link_list[(int(data[0]), int(data[1]))] = Link(distance=int(data[2]), bandwidth=100,
                                                             failure_rate=0,
                                                             shape=get_shape(),
                                                             scale=p_scale,
                                                             age=get_initial_age(p_scale))
        line = f.readline()
    f.close()
    return (node_count, p_link_list)


def is_failure(failure_rate):
    return failure_rate > rnd.random()


def is_rapired(p_ave_rapaired_time, p_failure_time):
    repaire_probability = 1.0 - math.exp(-1.0 * (1.0 / p_ave_rapaired_time) * p_failure_time)
    random_val = rnd.random()
    return repaire_probability > random_val


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


TOPOLOGY_FILE = 'topology_nsf.txt'
argv = sys.argv

# 初期設定生成
# リンク条件生成

if len(argv) > 1:
    print("Traffic per second: %d" % int(argv[1]))
else:
    exit(-1)

if len(argv) > 2:
    scale = int(argv[2])
    print("Scale: %d" % int(argv[2]))
else:
    scale = 0

# トポロジー読み込み
link_list = {}
(node_size, link_list) = load_topology(TOPOLOGY_FILE, link_list, scale)

# トラフィック要求発生
TRAFFIC_DEMAND = int(argv[1])  # 一秒当たりの平均トラフィック発生量
HOLDING_TIME = 4  # 平均トラフィック保持時間
TOTAL_TRAFFIC = 1000  # 総トラフィック量
MAX_ROUTE = 3  # 一つの要求に使用される最大ルート数
AVERAGE_REPAIRED_TIME = 5

define = Define(TRAFFIC_DEMAND, HOLDING_TIME, TOTAL_TRAFFIC, MAX_ROUTE, AVERAGE_REPAIRED_TIME, node_size, get_shape(), scale)
# print(show_links(link_list))
traffic_list = []
traffic_count = 0
second = 0

while True:
    traffic_per_second = numpy.random.poisson(TRAFFIC_DEMAND)
    traffic_list.append([])
    for num in range(0, traffic_per_second - 1):
        nodes = get_nodes_rand(node_size)
        traffic_list[second].append(Traffic(
            traffic_count,
            nodes[0],
            nodes[1],
            round(numpy.random.exponential(HOLDING_TIME - 1)) + 1,
            get_bandwidth_rand(), get_quality_rand()))
        traffic_count += 1
        if traffic_count == TOTAL_TRAFFIC:
            break

    second += 1
    if traffic_count >= TOTAL_TRAFFIC:
        break

print("second: %d" % second)

with open('link_list.dat', mode='wb') as f:
    pickle.dump(link_list, f)

with open('traffic_list.dat', mode='wb') as f:
    pickle.dump(traffic_list, f)

with open('define.dat', mode='wb') as f:
    pickle.dump(define, f)
