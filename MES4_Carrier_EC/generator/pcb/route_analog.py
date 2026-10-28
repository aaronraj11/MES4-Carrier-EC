"""Analog, hand-routed. Run after route_winch.py.

    route_analog.py <pcb> [group,group,...]

kelvin: INA236 sense lines (0.25 mm, no current) tapped at the 30 mOhm shunt pads, never at the plane vias or the
load track. The INA236's IN+ (pin 1) is its bottom pin but the shunt's +24V pad is on top, so the pair has to
cross: IN- stays on F.Cu at 45 deg into the shunt's bottom pad; IN+ leaves pin 1 by a via off its pad end (under
pin 3's GND via), runs under the shunt on B.Cu and comes up by a via off the top pad's right end. Same pattern on
all four channels (17.6 mm apart)."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from handroute import Board

B = Board(sys.argv[1]); only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
G = {}

G['kelvin'] = []
for u, dy in (('U2', 0.0), ('U3', 17.6), ('U4', 35.2), ('U5', 52.8)):
    y = lambda v: round(v + dy, 2)
    G['kelvin'] += [
        (f'Net-({u}-IN-)', 0.25, [('F', [(109.50, y(85.75)), (110.75, y(85.75)), (111.89, y(86.89))])]),
        ('+24V', 0.25, [('F', [(109.50, y(86.40)), (110.42, y(86.40))]), ('B', [(110.42, y(86.40)), (112.86, y(83.96)), (113.17, y(83.96))]),
                        ('F', [(113.17, y(83.96)), (111.89, y(83.96))])]),
    ]

# loadcell: ADS1232 front end. The placement interleaves the nets on every row (row 64.5: C18 AINN, C16 AINP, R29 AINN,
# R28 AINP; row 69.5: D21 AINN, D20 AINP, C17 AINN / AINP; row 74.8: C20 REFN / REFP, C21 REFN; row 78.7: C19 REFP,
# R31 REFN, R30 REFP / EXC+), so: the input pair and the reference stay on F.Cu with no vias (AINN over the R29 / C16
# row and under the clamp diodes, AINP through the channel between the rows; REFP out of pin 16 under the IC body
# and west above row 4, REFN out of pin 15 below it, under row 4, up the left side and back over row 3), and EXC+
# (low impedance) joins FB2, the clamp diodes, J13, AVDD (pin 18), R30 and C24 on B.Cu through vias.
SIGP, SIGN, AINP, AINN = '/LoadCell/LC_SIG+', '/LoadCell/LC_SIG-', '/LoadCell/LC_AINP', '/LoadCell/LC_AINN'
CAPA, CAPB, REFP, REFN, EXC = '/LoadCell/LC_CAPA', '/LoadCell/LC_CAPB', '/LoadCell/LC_REFP', '/LoadCell/LC_REFN', '/LoadCell/LC_EXC+'
G['loadcell'] = [
    # J12 -> 100R series resistors
    (SIGP, 0.25, [('F', [(101.33, 55.27), (101.33, 61.70), (98.53, 64.50)])]),
    (SIGN, 0.25, [('F', [(97.83, 55.27), (97.83, 61.55), (94.88, 64.50)])]),
    # AINN: R29 -> over C16 -> C18 -> channel -> D21 -> under the diodes -> tee into C17 -> pin 12
    (AINN, 0.25, [('F', [(93.86, 64.50), (93.86, 63.85), (93.36, 63.35), (88.04, 63.35), (87.54, 63.85), (87.54, 64.50)])]),
    (AINN, 0.25, [('F', [(87.54, 64.50), (87.54, 65.00), (86.74, 65.80), (82.56, 65.80), (81.56, 66.80), (81.56, 69.48),
                         (81.56, 71.00), (82.56, 72.00), (91.09, 72.00)])]),
    (AINN, 0.25, [('F', [(90.49, 69.48), (90.49, 71.40), (91.63, 72.54), (91.63, 74.61)])]),
    # AINP: R28 -> channel lane -> D20; C16 and C17 tee in; C17 -> pin 11
    (AINP, 0.25, [('F', [(97.51, 64.50), (97.51, 65.30), (95.51, 67.30), (87.11, 67.30), (86.11, 68.30), (86.11, 69.48)])]),
    (AINP, 0.25, [('F', [(91.19, 64.50), (91.19, 66.40), (92.09, 67.30)])]),
    (AINP, 0.25, [('F', [(93.44, 69.48), (93.44, 68.18), (94.32, 67.30)])]),
    (AINP, 0.25, [('F', [(93.44, 69.48), (92.28, 70.64), (92.28, 74.61)])]),
    # C22 -> pins 10 / 9, under C17
    (CAPB, 0.25, [('F', [(95.78, 69.48), (95.78, 70.40), (95.28, 70.90), (93.43, 70.90), (92.93, 71.40), (92.93, 74.61)])]),
    (CAPA, 0.25, [('F', [(98.73, 69.48), (98.73, 70.48), (97.61, 71.60), (94.18, 71.60), (93.58, 72.20), (93.58, 74.61)])]),
    # REFP: pin 16 under the IC body, west above row 4 -> C19; R30 and C20 tee in
    (REFP, 0.25, [('F', [(93.58, 80.33), (93.58, 78.40), (93.13, 77.95), (82.47, 77.95), (82.00, 78.42), (82.00, 78.72)])]),
    (REFP, 0.25, [('F', [(88.62, 77.95), (88.12, 78.45), (88.12, 78.72)])]),
    (REFP, 0.25, [('F', [(86.42, 77.95), (85.79, 77.32), (85.79, 74.77)])]),
    # REFN: pin 15 below REFP, under row 4, up the left side, over row 3 -> C21; R31 and C20 tee in
    (REFN, 0.25, [('F', [(92.93, 80.33), (92.93, 79.35), (92.48, 78.90), (90.60, 78.90), (89.20, 80.30), (80.20, 80.30), (79.60, 79.70), (79.60, 73.90),
                         (80.20, 73.30), (88.61, 73.30), (89.11, 73.80), (89.11, 74.77)])]),
    (REFN, 0.25, [('F', [(85.07, 80.30), (84.57, 79.80), (84.57, 78.72)])]),
    (REFN, 0.25, [('F', [(82.34, 73.30), (82.84, 73.80), (82.84, 74.77)])]),
    # EXC+: vias off FB2, D21, D20, R30, C24 and AVDD (pin 18, under the IC body); B.Cu: J13 -> D20 -> D21 -> FB2,
    # a spine at x 93.3 from AVDD up to the J13 run, and a branch to R30 and C24; C23 <-> C24 on F.Cu
    (EXC, 0.3, [('F', [(82.12, 64.50), (81.29, 64.50)]), ('B', [(81.29, 64.50)])]),
    (EXC, 0.3, [('F', [(83.43, 68.53), (84.57, 68.53)]), ('B', [(84.57, 68.53)])]),
    (EXC, 0.3, [('F', [(87.98, 68.53), (89.14, 68.53)]), ('B', [(89.14, 68.53)])]),
    (EXC, 0.3, [('F', [(89.14, 78.72), (89.81, 78.72)]), ('B', [(89.81, 78.72)])]),
    (EXC, 0.3, [('F', [(84.28, 82.89), (84.96, 82.89)]), ('B', [(84.96, 82.89)])]),
    (EXC, 0.3, [('F', [(94.88, 80.33), (94.88, 77.60)]), ('B', [(94.88, 77.60)])]),
    (EXC, 0.3, [('B', [(114.16, 55.27), (114.16, 62.60), (113.16, 63.60), (94.07, 63.60), (89.14, 68.53), (84.57, 68.53),
                       (81.29, 65.25), (81.29, 64.50)])]),
    (EXC, 0.3, [('B', [(94.88, 77.60), (93.30, 76.02), (93.30, 64.37)])]),
    (EXC, 0.3, [('B', [(93.30, 75.23), (89.81, 78.72), (89.13, 78.72), (84.96, 82.89)])]),
    (EXC, 0.3, [('F', [(81.03, 82.89), (81.03, 81.89), (81.62, 81.30), (83.69, 81.30), (84.28, 81.89), (84.28, 82.89)])]),
]

for k, paths in G.items():
    if only and k not in only: continue
    for net, w, runs in paths: B.path(net, w, runs)
    print(k, len(paths), 'paths')
B.save()
