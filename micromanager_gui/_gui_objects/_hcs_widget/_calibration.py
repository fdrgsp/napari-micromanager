from typing import Tuple

from sympy import Eq, solve, symbols

a = (-2.0, 2.0)
b = (5.0, 1.0)
c = (-2.0, -6.0)


def get_round_well_center(
    a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
):
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


xc, yc = get_round_well_center(a, b, c)
print(xc, yc)
