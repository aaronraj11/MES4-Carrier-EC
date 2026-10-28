"""Comms, hand-routed (the parts away from J1; J1's fingers are routed with the MCU escape). Run after route_analog.py.

    route_comms.py <pcb> [group,group,...]

can: the bus J3 - D6 - D7 - J4 ports 1-4 runs down x 72.9 between J4 and the J2 / SW1 column. On every RJ45 port the
H pin (left column) sits beside the L pin (right column), so an H stub on the same layer would cross the L line:
L runs on F.Cu and H on B.Cu (the port pins are through-hole), stubs at 45 deg. D6 / D7 H pins reach B.Cu by a via
off the pad end. 0.25 mm (CAN class).
uart: servo UART at J17. The +24V_SRV tracks wall J17 off on F.Cu, so TX / RX drop to B.Cu by a via right after the
ESD diodes D24 / D23; RX passes under J17's TX pin so the two never cross."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from handroute import Board

B = Board(sys.argv[1]); only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
G = {}
H, L = 'CANH', 'CANL'
G['can'] = [
    # L on F.Cu: J3 pin 5 -> bus -> port 4; tees to D6, port 1, D7, ports 2 / 3
    (L, 0.25, [('F', [(69.83, 60.48), (72.90, 63.55), (72.90, 111.65), (71.90, 112.65), (69.44, 112.65)])]),
    (L, 0.25, [('F', [(72.90, 66.71), (75.15, 64.46)])]),
    (L, 0.25, [('F', [(72.90, 72.68), (74.62, 70.96), (75.33, 70.96)])]),
] + [(L, 0.25, [('F', [(72.90, y - 1.00), (71.90, y), (69.44, y)])]) for y in (70.65, 84.65, 98.65)] + [
    # H on B.Cu: port 1 -> bus -> port 4; tees to ports 2 / 3; J3 pin 3 -> D6 via -> D7 via -> bus
    (H, 0.25, [('B', [(66.90, 69.38), (71.90, 69.38), (72.90, 70.38), (72.90, 110.38), (71.90, 111.38), (66.90, 111.38)])]),
] + [(H, 0.25, [('B', [(72.90, y - 1.00), (71.90, y), (66.90, y)])]) for y in (83.38, 97.38)] + [
    (H, 0.25, [('F', [(77.05, 64.46), (77.05, 63.33)]), ('B', [(77.05, 63.33)])]),
    (H, 0.25, [('F', [(75.33, 69.06), (74.19, 69.06)]), ('B', [(74.19, 69.06)])]),
    (H, 0.25, [('B', [(75.38, 60.48), (77.05, 62.15), (77.05, 63.33), (74.19, 66.19), (74.19, 70.06), (72.90, 71.35)])]),
]
TX, RX = '/AuxPower/SRV_TX', '/AuxPower/SRV_RX'
G['uart'] = [
    ('PA2', 0.2, [('F', [(194.07, 133.63), (196.70, 133.63)])]),
    ('PA3', 0.2, [('F', [(194.07, 139.30), (196.70, 139.30)])]),
    (TX, 0.2, [('F', [(197.72, 133.63), (199.88, 133.63), (200.68, 132.83)]),
               ('B', [(200.68, 132.83), (209.11, 132.83), (217.04, 140.76)])]),                       # -> J17.4 from above
    (RX, 0.2, [('F', [(197.72, 139.30), (199.88, 139.30), (200.68, 138.50)]),
               ('B', [(200.68, 138.50), (204.68, 142.50), (218.80, 142.50), (220.54, 140.76)])]),     # -> J17.3, under J17.4
]

for k, paths in G.items():
    if only and k not in only: continue
    for net, w, runs in paths: B.path(net, w, runs)
    print(k, len(paths), 'paths')
B.save()
