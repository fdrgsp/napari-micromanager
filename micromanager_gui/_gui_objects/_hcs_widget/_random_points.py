import math
import random

import matplotlib.pyplot as plt
import numpy as np

circlular = True
# circlular = False

# well diameter
well_size_x = 15
well_size_y = 15
# radius of the circle
area_size_x = 13
area_size_y = 13
# center of the circle (x, y)
center_x = 0
center_y = 0
# number of points
n_points = 10

fig, ax = plt.subplots()

if circlular:
    well_circle = plt.Circle((0, 0), well_size_x, color="m", fill=False)
    circle = plt.Circle((0, 0), area_size_x, color="m", fill=False)
    ax.add_patch(well_circle)
    ax.add_patch(circle)

    for _ in range(n_points):
        # random angle
        alpha = 2 * math.pi * random.random()
        # random radius
        r = area_size_x * math.sqrt(random.random())
        # calculating coordinates
        x = r * math.cos(alpha) + center_x
        y = r * math.sin(alpha) + center_y

        # print("Random point", (x, y))
        ax.plot(x, y, marker="o", markersize=10, color="k")


else:
    well_square = plt.Rectangle(
        (-well_size_x, well_size_y),
        well_size_x * 2,
        -well_size_y * 2,
        color="g",
        fill=False,
    )
    square = plt.Rectangle(
        (-area_size_x, area_size_y),
        area_size_x * 2,
        -area_size_y * 2,
        color="g",
        fill=False,
    )
    ax.add_patch(well_square)
    ax.add_patch(square)

    a = area_size_x  # upper bound
    b = -area_size_x  # lower bound
    # Random coordinates [b,a) uniform distributed
    coordy = (b - a) * np.random.random_sample((n_points,)) + a  # generate random y
    coordx = (b - a) * np.random.random_sample((n_points,)) + a  # generate random x

    for i in range(len(coordx)):
        ax.plot(coordx[i], coordy[i], marker="o", markersize=10, color="b")

plt.show()
