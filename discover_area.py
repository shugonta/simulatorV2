import math


# 値の存在する範囲確認
def getCost(x):
    if x <= 0:
        return None
    elif 0 < x <= 0:
        return (x - 5000) ^ 2
    else:
        return None


cost_mem = {}


def doCalc(delta, min_val, max_val, min_noval_upper, max_noval_lower):
    # 範囲最小値
    for x in range(max_noval_lower, min_val, delta):
        if x not in cost_mem:
            cost_mem[x] = getCost(x)
        if cost_mem[x] is not None:
            if x < min_val:
                min_val = x
                break
            if x > max_val:
                max_val = x
        else:
            if max_val < x < min_noval_upper and min_val < x:
                min_noval_upper = x
            if max_noval_lower < x < min_val and max_val > x:
                max_noval_lower = x

    # 範囲最大値
    for x in range(max_val, min_noval_upper, delta):
        if x not in cost_mem:
            cost_mem[x] = getCost(x)
        if cost_mem[x] is not None:
            if x > max_val:
                max_val = x
        else:
            if max_val < x < min_noval_upper and min_val < x:
                min_noval_upper = x
                break

    if delta == 1:
        return [min_val, max_val]
    else:
        return doCalc(math.ceil(delta / 2), min_val, max_val, min_noval_upper, max_noval_lower)


min_range = 0
max_range = 10000 + 1
delta = math.ceil((max_range - min_range) / 2)
result = doCalc(delta, max_range, min_range, max_range, min_range)
print("min %d max %d" % (result[0], result[1]))
