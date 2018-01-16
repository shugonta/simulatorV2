import sys

f = open('topology_route.txt', 'w')
route_cnt = sys.stdin.readline()
f.write(str(int(route_cnt) + 2) + "\n")
for i in range(2, int(route_cnt) + 2):
    f.write("%d %d %d\n" % (1, i, 10))
    f.write("%d %d %d\n" % (i, int(route_cnt) + 2, 10))
