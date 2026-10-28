"""Winch relays, hand-routed: K5 / K6 contacts and interlock to J18, and the coil drive.
Winch_48V nets keep >= 2 mm from other copper. J18's order (ACLK, COM, CLK) is mirrored against K6's pins
(COM on the top row, ACLK on the bottom row), so ACLK and COM-to-K5 drop from J18's through-hole pins on
B.Cu to a via under the relay body; everything else is F.Cu. ILK_CLK runs between the relays' pin rows,
ILK_ACLK below the relays. A no-pour rule area on all copper layers keeps the planes off the winch copper.
Run after route_rails.py."""
import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from handroute import Board

B = Board(sys.argv[1])
W = '/Winch/'
PATHS = [
    (W + 'WINCH_CLK', 0.4, [('F', [(173.66, 55.27), (173.66, 57.00), (172.40, 58.26), (172.40, 64.15)])]),                    # J18.1 -> K5.4
    (W + 'WINCH_COM', 0.4, [('F', [(170.16, 55.27), (170.16, 57.50), (165.72, 61.94), (165.72, 64.15)])]),                    # J18.2 -> K6.6
    (W + 'WINCH_COM', 0.4, [('B', [(170.16, 55.27), (170.16, 63.91), (174.60, 68.35)]), ('F', [(174.60, 68.35), (174.60, 70.15)])]),   # -> K5.6
    (W + 'WINCH_ACLK', 0.4, [('B', [(166.66, 55.27), (166.66, 67.09), (167.92, 68.35)]), ('F', [(167.92, 68.35), (167.92, 70.15)])]),  # J18.3 -> K6.4
    (W + 'ILK_CLK', 0.4, [('F', [(163.52, 64.15), (163.52, 66.15), (164.52, 67.15), (173.60, 67.15), (174.60, 66.15), (174.60, 64.15)])]),  # K6.7 -> K5.3
    (W + 'ILK_ACLK', 0.4, [('F', [(165.72, 70.15), (165.72, 71.65), (166.72, 72.65), (175.80, 72.65), (176.80, 71.65), (176.80, 70.15)])]),  # K6.3 -> K5.7
    # coil drive (0.3): coil- <-> flyback diode anode (mirrors the coil+ tracks), coil- -> FET drain. K6's coil- drops
    # left of the relay (x 159.6) to stay 2 mm from K6.2, an unused NC contact that is live (ILK_ACLK) while K6 is off.
    ('Net-(D26-A)', 0.3, [('F', [(157.08, 65.50), (158.97, 65.50), (160.32, 64.15)])]),
    ('Net-(D26-A)', 0.3, [('F', [(159.60, 64.87), (159.60, 72.94)])]),
    ('Net-(D25-A)', 0.3, [('F', [(180.00, 70.15), (181.89, 70.15), (183.24, 68.80)])]),
    ('Net-(D25-A)', 0.3, [('F', [(180.00, 70.15), (180.00, 72.22), (180.72, 72.94)])]),
]
for net, w, runs in PATHS: B.path(net, w, runs)

# no copper pour on any layer over J18 and the relay contacts: the inner planes otherwise sit 0.25 mm from J18's pins and
# the winch vias, and a later F / B GND fill would flood to 0.6 mm. 2 mm margin around all winch copper, up to the board edge.
import pcbnew
z = pcbnew.ZONE(B.b); z.SetIsRuleArea(True); z.SetZoneName('Winch 48V isolation')
ls = pcbnew.LSET()
for L in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu): ls.AddLayer(L)
z.SetLayerSet(ls)
z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
o = z.Outline(); o.NewOutline()
for x, y in ((161.1, 49.0), (179.2, 49.0), (179.2, 74.9), (161.1, 74.9)): o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
B.b.Add(z)
B.save()
print(len(PATHS), 'paths')
