"""Factorial probability effects and distances between condition-averaged vectors."""
import math
from .core import distance_matrix


def factorial_cell(p):
    if len(p)!=4 or any(not math.isfinite(v) or not 0<=v<=1 for v in p):raise ValueError('Four valid semantically oriented probabilities required')
    a,b,c,d=p;mean=math.fsum(p)/4
    return {'counterbalanced':mean,'minimum':min(p),'maximum':max(p),'range':max(p)-min(p),'std_population':math.sqrt(math.fsum((x-mean)**2 for x in p)/4),
        'label_effect':(b+d-a-c)/2,'order_effect':(c+d-a-b)/2,'interaction':d-c-b+a}


def factorial_distances(conditions):
    if len(conditions)!=4:raise ValueError('Four conditions required')
    shape=(len(conditions[0]),len(conditions[0][0]))
    if any(len(c)!=shape[0] or any(len(v)!=shape[1] for v in c) for c in conditions):raise ValueError('Mismatched dimensions')
    cb=[[math.fsum(conditions[k][i][j] for k in range(4))/4 for j in range(shape[1])] for i in range(shape[0])]
    ds=[distance_matrix(c) for c in conditions];balanced=distance_matrix(cb)
    avg=[[math.fsum(ds[k][i][j] for k in range(4))/4 for j in range(shape[0])] for i in range(shape[0])]
    if any(balanced[i][j]>avg[i][j]+1e-12 for i in range(shape[0]) for j in range(shape[0])):raise ValueError('Jensen inequality violation')
    return {'condition_sum_l1':ds,'counterbalanced_probabilities':cb,'counterbalanced_sum_l1':balanced,'average_condition_distance_not_primary':avg}
