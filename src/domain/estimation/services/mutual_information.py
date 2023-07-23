import warnings

import numpy as np
from sklearn.metrics import mutual_info_score, normalized_mutual_info_score

__all__ = (
    "mutual_information",
    "norm_mutual_information",
    "calc_MI",
    "computeMI",
)


def mutual_information(x, y):
    warnings.filterwarnings("ignore")
    return mutual_info_score(x, y)


def norm_mutual_information(x, y):
    warnings.filterwarnings("ignore")
    return normalized_mutual_info_score(x, y)


def calc_MI(x, y, bins):
    c_xy = np.histogram2d(x, y, bins)[0]
    mi = mutual_info_score(None, None, contingency=c_xy)
    return mi


def computeMI(x, y):
    sum_mi = 0.0
    x_value_list = np.unique(x)
    y_value_list = np.unique(y)
    Px = np.array(
        [len(x[x == xval]) / float(len(x)) for xval in x_value_list]
    )  # P(x)
    Py = np.array(
        [len(y[y == yval]) / float(len(y)) for yval in y_value_list]
    )  # P(y)
    for i in range(len(x_value_list)):
        if Px[i] == 0.0:
            continue
        sy = y[x == x_value_list[i]]
        if len(sy) == 0:
            continue
        pxy = np.array(
            [len(sy[sy == yval]) / float(len(y)) for yval in y_value_list]
        )  # p(x,y)
        t = pxy[Py > 0.0] / Py[Py > 0.0] / Px[i]  # log(P(x,y)/( P(x)*P(y))
        sum_mi += sum(
            pxy[t > 0] * np.log2(t[t > 0])
        )  # sum ( P(x,y)* log(P(x,y)/( P(x)*P(y)) )
    return sum_mi
