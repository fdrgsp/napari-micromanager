from typing import Tuple

from sympy import Eq, solve, symbols

a = (-2.0, 2.0)
b = (5.0, 1.0)
c = (-2.0, -6.0)


def get_center_of_round_well(
    a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
) -> Tuple[float, float]:
    """Find the center of a round well given 3 edge points"""
    # eq circle (x - x1)^2 + (y - y1)^2 = r^2
    # for point a: (x - ax)^2 + (y - ay)^2 = r^2
    # for point b: = (x - bx)^2 + (y - by)^2 = r^2
    # for point c: = (x - cx)^2 + (y - cy)^2 = r^2

    x, y = symbols("x y")

    eq1 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - b[0]) ** 2 + (y - b[1]) ** 2)
    eq2 = Eq((x - a[0]) ** 2 + (y - a[1]) ** 2, (x - c[0]) ** 2 + (y - c[1]) ** 2)

    dict_center = solve((eq1, eq2), (x, y))
    xc = dict_center[x]
    yc = dict_center[y]
    return xc, yc


xc, yc = get_center_of_round_well(a, b, c)
print(xc, yc)


a = (0.0, 2.0)
b = (7.0, 5.0)
c = (8, 4)
d = (7, 0)


def get_center_of_squared_well(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
) -> Tuple[float, float]:
    """Find the center of a square well given 4 edge points"""
    x_list = [x[0] for x in [a, b, c, d]]
    y_list = [y[1] for y in [a, b, c, d]]

    x_max, x_min = (max(x_list), min(x_list))
    y_max, y_min = (max(y_list), min(y_list))

    xc = (x_max - x_min) / 2
    yc = (y_max - y_min) / 2

    return xc, yc


xc, yc = get_center_of_squared_well(a, b, c, d)
print(xc, yc)
