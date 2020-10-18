#!/usr/bin/python3

import json
import math
import argparse
import drawSvg as draw

from tqdm import tqdm

EPSILON = 1e-4


def _distance(p):
    return math.sqrt(p[0]**2 + p[1]**2)


def _radius(area):
    return math.sqrt(abs(area) / math.pi)


def _propose(radius, circles):
    def _intersections(c1, c2):
        x0, y0, r0 = c1
        x1, y1, r1 = c2

        r0 += radius
        r1 += radius

        d = math.sqrt((x1 - x0)**2 + (y1 - y0)**2)

        # no overlap
        if d > r0 + r1:
            return []

        # a contains b
        if d < abs(r0 - r1):
            return []

        # a is b
        if d == 0 and r0 == r1:
            return []

        else:
            a = (r0**2 - r1**2 + d**2) / (2 * d)
            h = math.sqrt(r0**2 - a**2 + EPSILON)
            x2 = x0 + a * (x1 - x0) / d
            y2 = y0 + a * (y1 - y0) / d
            x3 = x2 + h * (y1 - y0) / d
            y3 = y2 - h * (x1 - x0) / d

            x4 = x2 - h * (y1 - y0) / d
            y4 = y2 + h * (x1 - x0) / d

            if abs(_distance((x3, y3)) - _distance((x4, y4))) < EPSILON:
                return [(x3, y3), (x4, y4)]

            return [max(
                [(x3, y3), (x4, y4)],
                key=lambda p: _distance(p),
            )]

    return [
        p for i, c1 in enumerate(circles) for c2 in circles[i:]
        for p in _intersections(c1, c2)
    ]


def _filter(radius, circles, positions):
    def _valid(c1, c2):
        x0, y0, r0 = c1
        x1, y1, r1 = c2

        d = math.sqrt((x1 - x0)**2 + (y1 - y0)**2) + EPSILON

        # collides
        if d < r0 + r1:
            return False

        return True

    result = []
    for p in positions:
        is_valid = True
        for c in reversed(circles):
            if not _valid((p[0], p[1], radius), c):
                is_valid = False
                break
        if is_valid:
            result.append(p)

    return result


def _choose_funder(radius, positions):
    return list(min(
        positions,
        key=lambda p: _distance(p),
    )) + [radius]


def _choose_user(radius, positions, funder):
    return list(
        min(
            positions,
            key=
            lambda p: math.sqrt((p[0] - funder[0])**2 + (p[1] - funder[1])**2),
        )) + [radius]


def calculate(data):
    assert len(data) >= 2

    circles = [
        [0, 0, _radius(data[0][1])],
        [0, _radius(data[0][1]) + _radius(data[1][1]),
         _radius(data[1][1])],
    ]

    last_funder = circles[0]

    for _, area in tqdm(data[2:]):
        positions = _propose(_radius(area), circles)
        valid = _filter(_radius(area), circles, positions)
        if area > 0:
            circle = _choose_funder(_radius(area), valid)
            last_funder = circle
        else:
            circle = _choose_user(_radius(area), valid, last_funder)
        circles.append(circle)

    return circles


def build(circles, data, size, highlight=[], output='circles.svg'):
    d = draw.Drawing(size, size, origin='center')
    d.append(draw.Rectangle(
        -size / 2,
        -size / 2,
        size,
        size,
        fill='white',
    ))

    if circles and data:
        last_funder_index = [i for i, d in enumerate(data) if d[1] > 0][-1]

    def _color_funder(l, ml):
        return '#{:02x}{:02x}{:02x}'.format(*([int(255 * (l / ml))] * 3))

    for i, item in enumerate(zip(circles, data)):
        if i == last_funder_index:
            circle = [x for x in circles[i]]
            circle[2] = _radius(data[i][1] - sum(d[1] for d in data))
        else:
            circle = item[0]

        if data[i][1] > 0:
            color = _color_funder(circle[2], math.sqrt(item[1][1] / math.pi))
        else:
            if data[i][0] and data[i][0] in highlight:
                color = '#ffff00'
            else:
                color = '#84ab3f'

        d.append(draw.Circle(*circle, fill=color))

    d.saveSvg(output)


def explode(circles, data, size, max_area, highlight=[], output='circles.svg'):
    d = draw.Drawing(size, size, origin='center')

    def _color_background(l, ml):
        return '#{:02x}{:02x}{:02x}'.format(
            int(132 + (255 - 132) * (l / ml)),
            int(171 + (255 - 171) * (l / ml)),
            int(63 + (255 - 63) * (l / ml)),
        )

    d.append(
        draw.Rectangle(
            -size / 2,
            -size / 2,
            size,
            size,
            fill=_color_background(
                sum(-d[1] for d in data if d[1] < 0),
                max_area,
            ),
        ))

    for i, item in enumerate(zip(circles, data)):
        circle = item[0]

        if data[i][1] < 0:
            if i == 0:
                color = '#ffcfcf'
                circle = [circle[0], circle[1], circle[2] * 3]
            else:
                color = '#84ab3f'

            d.append(draw.Circle(*circle, fill=color))

    d.saveSvg(output)


def run(funders, users, highlight=[]):

    data = []
    balance = 0
    index = 0

    for name, amount in funders:
        data.append((name, amount))
        balance += amount

        while index < len(users) and users[index][1] <= balance:
            balance -= users[index][1]
            data.append((users[index][0], -users[index][1]))
            index += 1

        if index == len(users):
            break

    data = [x for x in data if x[1] >= 1 or x[1] <= -1]

    try:
        with open('circles.json') as fd:
            circles = json.load(fd)
    except Exception:
        circles = calculate(data)
        with open('circles.json', 'w') as fd:
            json.dump(circles, fd, indent=2)

    size = 2 * max(_distance(c) + c[2] for c in circles)

    for i in range(len(list((zip(circles, data))))):
        build(
            circles[:i],
            data[:i],
            size,
            highlight,
            output='output/circles_{}.svg'.format(i),
        )

    for i in range(len(list((zip(circles, data)))) + 1):
        explode(
            circles[i:],
            data[i:],
            size,
            sum(-d[1] for d in data if d[1] < 0),
            highlight,
            output='output/circles_{}.svg'.format(
                len(list(zip(circles, data))) + i))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description=
        """Tool for rendering names and values into a deterministically packed structure of circles """,
    )

    parser.add_argument(
        'funders',
        help='Path to JSON list of n pairs of [donor_name, total_donations]',
    )

    parser.add_argument(
        'users',
        help='Path to JSON list of n pairs of [user_name, total_donations]',
    )

    parser.add_argument(
        '-l',
        '--highlight',
        help='labels to highlight',
        action='append',
        default=[],
    )

    args = parser.parse_args()

    with open(args.funders) as fd:
        funders = json.load(fd)

    with open(args.users) as fd:
        users = json.load(fd)

    run(funders, users, args.highlight)
