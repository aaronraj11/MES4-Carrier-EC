"""MES4-MCU escape (J1's 0.5 mm fingers), hand-routed. Run after route_comms.py.

    route_mcu.py <pcb> [group,group,...]

west: J1 pins 1-11 and 6 / 8 -> CAN bus, J2 (STDC14), SW1, D1-D5. J1's top row (y 97.86) faces J2's bottom row across
a 2.4 mm corridor; on 0.5 mm pitch only every other finger can take a via, so: CANL and SWDIO leave north on F.Cu,
CANH north on F.Cu to a via by the bus, SWCLK and NRST also leave south (between J1's rows) to vias. B.Cu does the
crossings: SWCLK under SWDIO to a via off J2.6; NRST west under the CAN pair to SW1 (via off its inner pad end) and
J2.12; VCP_TX / VCP_RX (bottom row) north under J1 and J2, TX up into J2's inter-row channel (to J2.14 and D4),
RX past J2's top row to a via off D5. SWD / NRST ESD diodes: SWCLK and SWDIO run east in J2's inter-row channel
(upper / lower lane) to D2 / D1 from below, NRST round J2's east side to D3 from above, leaving the strip above
J1 pins 29+ free for their escapes. CAN 0.25, the rest 0.2.
adc: PA6 / PA5 / LC_DOUT drop straight from U8 pins 22-24 (R34 and R33 sit on PA6's and PA5's lines, R32 turns DOUT
into PA4 on the east side), then PA6 / PA5 / PA4 run SW as three parallel 45 deg lines (x + y = 183.5 / 184.5 / 185.5)
past D3 straight into J1 pins 37 / 39 / 41, leaving everything SE of them for J1's east-going pins.
gates: the four relay gates leave J1 south (between its rows; pins 27 / 33's GND vias moved to the north end) to vias
fanned out off the finger ends and run B.Cu, where their order doesn't matter: PA8 diagonally NE under the fan-out
to a via west of the I2C bus, then F.Cu east to R9; PC6 / PA7 / PB3 straight south under the module (between J1's
bottom-row GND vias, PB3's lane ends before PA7 crosses it) to a via level with R12 / R20 / R17, then F.Cu east.
i2c: SDA / SCL / PA15 fan out of J1 on F.Cu (45 deg, parallel to the PA4-6 lines, with slots kept for PA3-PA0 / PC15
north of SDA and PB6 between SCL and PA15), run east to a via each and become a B.Cu bus west of the +3V3 spine
(x 101.43 / 102.08 / 102.73, 0.65 apart like the spine, so a via on one lane clears the next). At each INA236 and at the pull-ups a
via and an F.Cu stub east; PA15 reaches pin 8 from below (the 3V3 cap sits west of it). U4's A1 (pin 7) ties to SDA
on its pads; U5's (pin 7, SCL) by a B.Cu jumper between vias off pins 5 and 7.
far: the GPIO that leave the MCU area. B.Cu is walled east of x 145 by the relay output lanes (RLY2-4_OUT, x 145.4-150.5,
north to J7-J9) and east of x 151 by the test-point feeds (x 154.5 / 159.5 / 179.8, down to y 141.8); F.Cu is cut by
the +3V3 opto / servo-pull-up line (diagonal off U7, then y 133.63 to R37 with branches down x 175.5 and x 193.05).
PA1 / PA0 / PC15 / PB6 take their 45 deg slots out of J1, cross the I2C bus on F.Cu and drop to B.Cu east of the spine
(lanes 0.65 apart like the I2C lanes, so each via sits on its own lane and the next lane clears it), then share the one B.Cu band that clears the INA and relay
columns (y 93.95-95.45). PA1 / PA0 turn north in the clear strip east of the relays and climb diagonally to vias past
LED2, then run F.Cu at y 73.2 / 73.9 (0.7 apart so a via clears the other lane), PA0 jogging to y 75.8 south of
the winch area, to R45 / R43. PB6 comes up before the relay output lanes and drops down x 150.17 through R25 into
U6; PC15 dives under PB6 on B.Cu, comes up east of LED5 and drops down x 148.6 (west of U6's pads) into R27 and U7.
PA3 / PA2 leave J1 south like the gates, run down under the module, hop the I2C bus on F.Cu at y 129.3-130, cross
the relay columns on B.Cu, come up before the relay output lanes, run F.Cu under the +3V3 line to x 161, hop it on
B.Cu and run F.Cu north of it at y 132.93 / 132.23 (0.7 apart, like the lanes under it); PA2 lands on R39 from above, PA3 dives east of R39 (clear of the
screen trunk) and comes into the R36-R38 link from the east.
"""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from handroute import Board

B = Board(sys.argv[1]); only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
G = {}
DIO, CLK, RST = '/Main/SWDIO', '/Main/SWCLK', '/Main/NRST'
TX, RX = '/Main/VCP_TX', '/Main/VCP_RX'
G['west'] = [
    # CAN pair west along the corridor's south edge; CANH by a via onto the B.Cu bus, CANL straight into the F.Cu bus
    ('CANH', 0.25, [('F', [(79.30, 97.86), (79.30, 96.95), (78.95, 96.60), (74.40, 96.60)]), ('B', [(74.40, 96.60), (72.90, 98.10)])]),
    ('CANL', 0.25, [('F', [(79.80, 97.86), (79.80, 96.40), (79.35, 95.95), (73.90, 95.95), (72.90, 96.95)])]),
    # SWDIO: J1.7 -> J2.4 -> channel lower lane -> under D1's GND pad -> D1
    (DIO, 0.2, [('F', [(80.80, 97.86), (80.80, 96.60), (81.58, 95.82), (81.58, 91.80), (81.81, 91.57), (83.60, 91.57), (84.03, 92.00),
                       (87.42, 92.00), (87.99, 91.43)])]),
    # SWCLK: J1.9 south -> via -> B.Cu under SWDIO -> via off J2.6 -> channel upper lane -> D2
    (CLK, 0.2, [('F', [(81.30, 97.86), (81.30, 99.035)]), ('B', [(81.30, 99.035), (81.30, 96.40), (80.31, 95.41)]),
                ('F', [(80.31, 95.41), (80.31, 91.60), (80.94, 90.97), (83.80, 90.97), (85.60, 89.17), (87.50, 89.17), (87.99, 88.68), (87.99, 88.07)])]),
    # NRST: J1.11 north round J2's east side -> D3; J1.11 south -> via -> B.Cu west -> SW1 (via off pin 1's inner end), tee to J2.12
    (RST, 0.2, [('F', [(81.80, 97.86), (81.80, 96.90), (83.90, 94.80), (83.90, 93.80), (84.40, 93.30), (87.50, 93.30), (87.99, 93.79), (87.99, 94.47)])]),
    (RST, 0.2, [('F', [(81.80, 97.86), (81.80, 98.635), (82.25, 99.085), (82.25, 100.30), (81.70, 100.85)]),
                ('B', [(81.70, 100.85), (80.95, 101.60), (75.60, 101.60), (75.25, 101.25)]), ('F', [(75.25, 101.25), (75.25, 102.26)])]),
    (RST, 0.2, [('B', [(76.90, 101.60), (76.50, 101.20), (76.50, 95.105)]), ('F', [(76.50, 95.105), (76.50, 93.31)])]),
    # VCP_TX: J1.6 north -> via -> B.Cu x 79.0 -> via in J2's channel -> west past J2.13 -> D4; J2.14 tapped at 45 deg
    (TX, 0.2, [('F', [(80.55, 105.40), (80.55, 102.10), (79.00, 100.55)]), ('B', [(79.00, 100.55), (79.00, 91.27)]),
               ('F', [(79.00, 91.27), (75.00, 91.27), (74.40, 90.67), (74.40, 86.65), (74.00, 86.25), (74.00, 85.95)])]),
    (TX, 0.2, [('F', [(75.60, 91.27), (75.23, 91.64), (75.23, 93.31)])]),
    # VCP_RX: J1.8 north -> via -> B.Cu x 79.68 (between J2's top-row vias) -> via off D5 pin 1; D5 -> J2.13 top end
    (RX, 0.2, [('F', [(81.05, 105.40), (81.05, 101.17), (79.68, 99.80)]), ('B', [(79.68, 99.80), (79.68, 87.00), (78.63, 85.95), (76.625, 85.95)]),
               ('F', [(76.625, 85.95), (76.00, 85.95)])]),
    (RX, 0.2, [('F', [(76.00, 85.95), (76.00, 86.50), (75.23, 87.27), (75.23, 89.23)])]),
]
DOUT = '/LoadCell/LC_DOUT'
G['adc'] = [
    (DOUT, 0.2, [('F', [(98.78, 80.33), (98.78, 80.98), (100.50, 82.70)])]),
    ('PA6', 0.2, [('F', [(97.48, 80.33), (97.48, 86.02), (88.30, 95.20), (88.30, 97.86)])]),
    ('PA5', 0.2, [('F', [(98.13, 80.33), (98.13, 86.37), (88.80, 95.70), (88.80, 97.86)])]),
    ('PA4', 0.2, [('F', [(100.50, 83.72), (100.50, 85.00), (89.30, 96.20), (89.30, 97.86)])]),
]
G['gates'] = [
    ('PA8', 0.2, [('F', [(86.80, 97.86), (86.80, 98.90), (87.30, 99.40)]), ('B', [(87.30, 99.40), (96.88, 89.82), (100.60, 89.82)]),
                  ('F', [(100.60, 89.82), (106.39, 89.82)])]),
    ('PC6', 0.2, [('F', [(86.30, 97.86), (86.30, 99.80)]), ('B', [(86.30, 99.80), (86.30, 107.42)]), ('F', [(86.30, 107.42), (106.39, 107.42)])]),
    ('PA7', 0.2, [('F', [(87.80, 97.86), (87.80, 99.00), (88.30, 99.50)]), ('B', [(88.30, 99.50), (88.30, 132.00), (95.00, 138.70), (95.00, 142.62)]),
                  ('F', [(95.00, 142.62), (106.39, 142.62)])]),
    ('PB3', 0.2, [('F', [(94.30, 97.86), (94.30, 99.035)]), ('B', [(94.30, 99.035), (94.30, 125.02)]), ('F', [(94.30, 125.02), (106.39, 125.02)])]),
]
SDA, SCL = 'I2C1_SDA', 'I2C1_SCL'
XA, XB, XC = 101.43, 102.08, 102.73                         # SDA / SCL / PA15 bus lanes, 0.65 apart like the +3V3 spine
G['i2c'] = [
    (SDA, 0.2, [('F', [(92.30, 97.86), (92.30, 96.80), (96.05, 93.05), (XA, 93.05)]),
                ('B', [(XA, 93.05), (XA, 85.10), (XA, 83.25)]), ('F', [(XA, 83.25), (104.49, 83.25)])]),
    (SDA, 0.2, [('B', [(XA, 93.05), (XA, 102.70), (XA, 120.30), (XA, 137.90)])]),
    (SCL, 0.2, [('F', [(92.80, 97.86), (92.80, 96.90), (96.00, 93.70), (XB, 93.70)]),
                ('B', [(XB, 93.70), (XB, 84.45), (XB, 82.00)]), ('F', [(XB, 82.00), (104.49, 82.00)])]),
    (SCL, 0.2, [('B', [(XB, 93.70), (XB, 102.05), (XB, 119.65), (XB, 137.25)])]),
    ('PA15', 0.2, [('F', [(94.80, 97.86), (94.80, 96.10), (95.90, 95.00), (XC, 95.00)]),
                   ('B', [(XC, 95.00), (XC, 88.30), (XC, 80.75)]), ('F', [(XC, 80.75), (104.49, 80.75)])]),
    ('PA15', 0.2, [('B', [(XC, 95.00), (XC, 105.90), (XC, 123.50), (XC, 141.10)])]),
    (SDA, 0.2, [('F', [(106.89, 120.30), (106.89, 120.95)])]),                                   # U4 A1 -> SDA
    (SCL, 0.2, [('F', [(105.965, 137.25)]), ('B', [(105.965, 137.25), (105.965, 138.55)]), ('F', [(105.965, 138.55), (106.89, 138.55)])]),   # U5 A1 -> SCL
]
for dy in (0.0, 17.6, 35.2, 52.8):                          # each INA236: SCL pin 5, SDA pin 6, PA15 pin 8 from below
    y = lambda v: round(v + dy, 2)
    G['i2c'] += [
        (SCL, 0.2, [('B', [(XB, y(84.45))]), ('F', [(XB, y(84.45)), (105.965, y(84.45)), (106.89, y(84.45))])]),
        (SDA, 0.2, [('B', [(XA, y(85.10))]), ('F', [(XA, y(85.10)), (106.89, y(85.10))])]),
        ('PA15', 0.2, [('B', [(XC, y(88.30))]), ('F', [(XC, y(88.30)), (105.01, y(88.30)), (106.89, y(86.42))])]),   # 45 deg into pin 8's centre line
    ]
G['far'] = [
    ('PA1', 0.2, [('F', [(90.80, 97.86), (90.80, 96.50), (96.20, 91.10), (105.60, 91.10)]),
                  ('B', [(105.60, 91.10), (108.45, 93.95), (137.10, 93.95), (137.50, 93.55), (137.50, 79.50), (143.80, 73.20)]),
                  ('F', [(143.80, 73.20), (149.20, 73.20), (149.62, 72.78), (149.62, 72.34)])]),
    ('PA0', 0.2, [('F', [(91.30, 97.86), (91.30, 96.60), (96.15, 91.75), (104.95, 91.75)]),
                  ('B', [(104.95, 91.75), (107.65, 94.45), (137.70, 94.45), (138.20, 93.95), (138.20, 80.20), (144.50, 73.90)]),
                  ('F', [(144.50, 73.90), (151.50, 73.90), (153.40, 75.80), (188.33, 75.80), (188.75, 75.38), (188.75, 73.54)])]),
    ('PC15', 0.2, [('F', [(91.80, 97.86), (91.80, 96.70), (96.10, 92.40), (104.30, 92.40)]),
                   ('B', [(104.30, 92.40), (106.85, 94.95), (139.20, 94.95), (139.70, 94.45), (142.75, 94.45), (144.40, 96.10)]),
                   ('F', [(144.40, 96.10), (148.20, 96.10), (148.60, 96.50), (148.60, 115.60), (150.17, 117.17), (150.17, 122.85)])]),
    ('PB6', 0.2, [('F', [(93.80, 97.86), (93.80, 96.50), (95.95, 94.35), (104.30, 94.35)]),
                  ('B', [(104.30, 94.35), (105.40, 95.45), (140.50, 95.45)]),
                  ('F', [(140.50, 95.45), (149.77, 95.45), (150.17, 95.85), (150.17, 102.90), (150.17, 108.58)])]),
    ('PA2', 0.2, [('F', [(90.30, 97.86), (90.30, 99.80)]),
                  ('B', [(90.30, 99.80), (90.30, 100.30), (90.80, 100.80), (90.80, 128.90), (91.20, 129.30), (100.30, 129.30)]),
                  ('F', [(100.30, 129.30), (104.40, 129.30)]), ('B', [(104.40, 129.30), (139.40, 129.30), (144.43, 134.33)]),
                  ('F', [(144.43, 134.33), (162.00, 134.33)]), ('B', [(162.00, 134.33), (162.00, 132.93)]),
                  ('F', [(162.00, 132.93), (196.30, 132.93), (196.70, 133.33), (196.70, 133.63)])]),
    ('PA3', 0.2, [('F', [(89.80, 97.86), (89.80, 98.90), (89.30, 99.40), (89.30, 99.80)]),
                  ('B', [(89.30, 99.80), (89.30, 129.60), (89.70, 130.00), (99.60, 130.00)]), ('F', [(99.60, 130.00), (105.10, 130.00)]),
                  ('B', [(105.10, 130.00), (138.90, 130.00), (143.93, 135.03)]), ('F', [(143.93, 135.03), (160.60, 135.03)]),
                  ('B', [(160.60, 135.03), (160.60, 132.23)]), ('F', [(160.60, 132.23), (196.90, 132.23)]),
                  ('B', [(196.90, 132.23), (196.90, 137.80), (195.40, 139.30)]), ('F', [(195.40, 139.30)])]),
]

for k, paths in G.items():
    if only and k not in only: continue
    for net, w, runs in paths: B.path(net, w, runs)
    print(k, len(paths), 'paths')
B.save()
