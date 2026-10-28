# MES4-Carrier-EC: handoff for the next Claude session

Written 2026-10-27, updated 2026-10-28 after the PCB prep session (placement, planes, vias, net classes). Read this file first, then `README.md`.

## Start here: where the PCB stands (2026-10-28)

Branch `mes4-gpio-standard`, last commit `ead91b1` ("Net classes sized by current, +24V plane vias, fused M.2 GND bars"). The PCB helper scripts are in `generator/pcb/`.

**Done**
- Every part placed and grouped (23 KiCad groups), silkscreen pass, logo, test points named (TP labels from `TP_NAME` in `gen.py`).
- 4-layer stackup JLC04161H-7628: **F.Cu** "Top Signal", **In1** solid GND plane, **In2** solid +24V plane, **B.Cu** "Bottom Signal". One ground (`ONE_GND = True`); the GPS mount is left out (`GPS_MOUNT = False`).
- **GND vias** on every SMD GND pad (commit `7e09c66`), straight off the pad end, gap 0.1 mm.
- **Net classes sized by current** (in `gen.py`, written to the `.kicad_pro`):

| Class | Track / clearance | Via | Nets |
|---|---|---|---|
| Default | 0.2 / 0.2 | 0.6 / 0.3 | signals |
| Power_Small | 0.3 | | +3V3_MOD, SENS*_PWR, LC_EXC+ |
| Power | 0.5 | | +5V, +5V_24, GND, +5V_SRV, +9V_IMU, IMU_9V, +24V_DC |
| 24V_Power | 1.0 | 0.8 / 0.4 | +24V, +24V_AUX |
| Out_3A | 1.5 | 0.8 / 0.4 | relay outputs, Net-(F*-Pad1), Net-(U*-IN-), +24V_SRV, +5V_SCR, VBUS_SCR |
| Input_15A | 3.0 / 0.3 | | +24V_IN, +24V_F (use pours) |
| Winch_48V | 0.4 / **0.6** | | J18, WINCH_*, ILK_* |
| CAN | 0.25, pair 0.25 / 0.25 | | CANH / CANL (not auto-detected as a pair: route as a pair by hand) |
| LoadCell | 0.25, pair 0.25 / 0.2 | | LC_SIG*, AIN*, REF*, CAP* |

  Router presets: tracks 0.2 / 0.25 / 0.3 / 0.5 / 1.0 / 1.5 / 3.0, vias 0.6/0.3 and 0.8/0.4, diff pairs 0.25/0.2 and 0.25/0.25.
- **+24V vias** into the In2 plane (0.8/0.4), one pattern per part type: two vias across the pad end on the shunts R8 / R11 / R16 / R19, L1 / L2, F9, C1, D9; one via on C2 / C3, F7 / F8, D8, R7.
- **J1 (M.2) GND**: vias on the inner side of the pad rows (under the socket body, so the outer side stays free for signal escape). Runs of 3+ GND fingers are **fused by a 0.6 mm F.Cu bar** with a few vias: pins 24–74 (6 vias), 65–75 (2 vias). Isolated GND fingers have one via each.
- DRC baseline: **3 notes, all accepted** (silk_edge_clearance: J4's outline runs to the board edge by design; was 14 before the silkscreen pass), schematic parity 0. **0 unrouted — routing complete (2026-10-28)** (258 before routing, 218 after high-current, 150 after rails, 140 after winch, 132 after Kelvin, 107 after load cell, 89 after CAN / UART, 76 after the MCU west corner, 49 after the ADC lines, gates and I²C, 41 after the far-east GPIO — the MCU escape is done, 25 after the relay drive, 21 after the winch gates, 15 after the sensors, 7 after the LEDs, 0 after the screen USB-C). Full render `review/routing_complete.png`. Keep DRC at exactly these 3 after every step.
- **Supply rails done (2026-10-28), hand-routed** in `generator/pcb/route_rails.py`: every path is written out by hand as coordinates (the user does not want an autorouter; a maze router was tried and dropped). Re-apply everything from the 24 V-input board: `route_relays.py` → `route_srv_scr.py` → `route_rails.py <pcb> dc,aux,5v24,mod5v,imu,srv5,sens,3v3,tp`. Checks: `generator/pcb/drc.sh`, `generator/pcb/joints.py` (no 90° joints / width steps outside pads and vias). Render `review/routing_supply_rails.png`.
  - **Winch done (2026-10-28)**, `generator/pcb/route_winch.py` (run after `route_rails.py`; shared path helpers in `handroute.py`). J18's order (ACLK, COM, CLK) is mirrored against K6's pins, so ACLK and COM-to-K5 drop from J18's TH pins on B.Cu to a via under the relay body; CLK, COM-to-K6 on F.Cu; ILK_CLK between the relays' pin rows, ILK_ACLK below them. The unused NC1 / NO2 pins are live (NC1 closes to COM1 when the relay is off), so they count as 48 V copper. K6's coil+ now has its own via onto the B.Cu +5V_24 feed so coil- can drop left of the relay. Check: `generator/pcb/winch_clear.py` (≥ 2 mm from winch copper to anything else, all copper layers). All copper layers pass: a no-pour rule area "Winch 48V isolation" (F, In1, In2, B; x 161.1–179.2, board edge to y 74.9) keeps the planes and any later outer GND fill 2 mm off J18, the relay contacts and the winch vias (user-approved 2026-10-28).
  - **INA236 Kelvin pairs done (2026-10-28)**, `generator/pcb/route_analog.py kelvin` (run after `route_winch.py`): 0.25 mm sense lines tapped at the shunt pads. IN+ (pin 1) is the INA236's bottom pin but the shunt's +24V pad is on top, so the pair crosses: IN- on F.Cu at 45° into the bottom pad; IN+ by a via off pin 1's end (under pin 3's GND via), B.Cu under the shunt, a via off the top pad's right end. Same on all four channels. Render `review/routing_kelvin.png`.
  - **Load cell done (2026-10-28)**, `route_analog.py loadcell`. The placement interleaves the nets on every row, so: the input pair (SIG± → R28 / R29 → C16 / C18 / C17 / D20 / D21 → pins 11 / 12), CAPA / CAPB (C22 → pins 9 / 10) and the reference (REFP pin 16 → R30 / C20 / C19, REFN pin 15 → C21 / C20 / R31) are all F.Cu with no vias; LC_EXC+ joins FB2, D20 / D21, J13, AVDD (pin 18), R30 and C24 on B.Cu through vias (spine x 93.3 under the ADC, run y 63.6 from J13). LC_DOUT (pin 24 → R32) is left for the MCU signals. Render `review/routing_loadcell.png`.
  - **CAN bus and servo UART (J17 side) done (2026-10-28)**, `generator/pcb/route_comms.py` (run after `route_analog.py`). CAN: J3 - D6 - D7 - J4 ports 1-4 down x 72.9 (between J4 and J2 / SW1); each RJ45 port's H pin sits beside its L pin, so L is on F.Cu and H on B.Cu with 45° stubs (D6 / D7 H by vias off the pad ends). Servo UART: the +24V_SRV tracks wall J17 off on F.Cu, so TX / RX drop to B.Cu right after D24 / D23; RX passes under J17's TX pin. Renders `review/routing_can.png`, `review/routing_servo_uart.png`.
  - **Placement moves for the MCU escape** live in `generator/pcb/place_moves.py`, run first in the chain (user-approved 2026-10-28): R3 / R4 / R5 (I²C / PA15 pull-ups) stacked 1.25 mm apart just above U2, signal pads west, refs west of each row; D4 / D5 (VCP ESD) side by side above J2's left column; D1 / D2 (SWDIO / SWCLK ESD) swapped; three GND vias out of the J1 / J2 corridor (J1's tab via to the tab's west end, SW1 pin 2's to its inner end, J1 pin 10's to the finger's outer end); R32 / R33 / R34 off the row under U8 (R34 / R33 sit on PA6's / PA5's line, R32 upright east of them); J1 pin 33's GND via to the finger's north end and pin 27's bent SW behind the unused pin 25 (its north end sits on the +5V B.Cu diagonal), freeing the gates' south escapes. The INA236 3V3 rework is in `route_rails.py 3v3` (VS by a via and a B.Cu link off the spine x 103.38; +3V3 from J1 now runs up B.Cu x 82.45, east of the SWD / VCP crossings, onto the ADC line).
  - **MCU escape, west corner done (2026-10-28)**, `generator/pcb/route_mcu.py west` (run after `route_comms.py`): CAN pair west along the corridor's south edge (CANH by a via onto the B.Cu bus); SWDIO J1.7 → J2.4 on F.Cu; SWCLK and NRST also leave J1 south (between the rows) to vias, SWCLK crosses under SWDIO to a via off J2.6, NRST runs B.Cu west to SW1 (via off pin 1's inner end) with a tee up to J2.12; NRST's north side goes round J2's east side to D3 from above. SWCLK / SWDIO run east in J2's inter-row channel (upper / lower lane) to D2 / D1 from below. VCP_TX / VCP_RX (bottom-row fingers 6 / 8) go north under J1 and J2 on B.Cu: TX up into J2's channel → J2.14 (45° tee) and on past J2.13 to D4; RX between J2's top-row vias to a via off D5 → J2.13. Render `review/routing_mcu_west.png`.
  - **MCU escape, ADC lines / gates / I²C done (2026-10-28)**, `route_mcu.py adc,gates,i2c`. ADC: PA6 / PA5 / LC_DOUT drop straight from U8 pins 22–24 through R34 / R33 / R32, then PA6 / PA5 / PA4 run SW as parallel 45° lines (x + y = 183.5 / 184.5 / 185.5) past D3 into J1 pins 37–41. Gates: PC6 / PA8 / PA7 / PB3 leave J1 south to vias and run B.Cu (order doesn't matter there): PA8 diagonally NE under the fan-out to a via at (100.6, 89.82), then F.Cu to R9; PC6 / PB3 / PA7 straight south under the module to a via level with R12 / R17 / R20, then F.Cu east. I²C: SDA / SCL / PA15 fan out of J1 on F.Cu at 45° (parallel to PA4–6) to vias, then a B.Cu bus at x 101.45 / 102.07 / 102.69 (west of the +3V3 spine, 0.62 apart so a via clears the next lane) from the pull-ups (y 80.75–83.25) to U5; at each INA236 a via and an F.Cu stub east (PA15 reaches pin 8 from below, the 3V3 cap is west of it); U4's A1 ties to SDA on its pads, U5's to SCL by a B.Cu jumper between vias off pins 5 / 7. Render `review/routing_mcu_east.png`.
  - **MCU escape, far-east GPIO done (2026-10-28)**, `route_mcu.py far`. B.Cu is walled east of x 145 by the relay output lanes (RLY2–4_OUT, north to J7–J9) and east of x 151 by the test-point feeds (x 154.5 / 159.5 / 179.8, down to y 141.8); F.Cu by the +3V3 opto / servo-pull-up line (diagonal off U7, y 133.63 to R37, branches down x 175.5 and x 193.05). PA1 / PA0 / PC15 / PB6 cross the I²C bus on F.Cu, drop to B.Cu east of the spine and share the one band that clears the INA and relay columns (y 93.95–95.45). PA1 / PA0 turn north east of the relays and run F.Cu at y 73.2 / 73.9 (PA0 jogs to 75.8, south of the winch area) to R45 / R43; PB6 comes up before the relay output lanes and drops through R25 into U6; PC15 dives under PB6, comes up east of LED5 and drops down x 148.6 into R27 / U7. PA3 / PA2 leave J1 south, run down under the module, hop the I²C bus at y 129.3–130, cross the relay columns on B.Cu, run F.Cu under the +3V3 line to x 161, hop it on B.Cu and run north of it (y 132.4 / 131.7); PA2 lands on R39 from above, PA3 comes into the R36–R38 link from the east. PA2 / PA3 carry 6 / 8 vias (UART, slow). Render `review/routing_mcu_far.png`.
  - **Relay drive done (2026-10-28)**, `generator/pcb/route_local.py drive` (run after `route_mcu.py`), same on all four channels: gate R9.2 → Q2.1 with the R10 pull-down tapped at 45° past R9.1; coil drive (0.3 mm) Q2's drain straight east to the coil's low side K1.2; the flyback diode D10 sits 12 mm north by the coil's high side, boxed in by U2, the shunt and the K1 load path, so its anode drops by a via off the pad's lower end, runs B.Cu east at y 81.2 and down x 117.44 between K1's pins onto K1.2's through-hole pad. Render `review/routing_relay_drive.png`.
  - **Winch gates done (2026-10-28)**, `route_local.py wingate`: Q7 — R45 straight into the R46 pull-down, then over R46's GND pad and via to Q7's gate; Q6 — R44 straight west into Q6's gate, R43 reaches R44 over the top (PA0 comes up into R43 from below). winch_clear: 0 issues. Render `review/routing_winch_gates.png`.
  - **Sensor inputs done (2026-10-28)**, `route_local.py sensors`. Opto link (R24.2 → D18.1 → U6.1, one net): diagonally under R24.1, west below D18's pads, and a 45° branch down the inside of U6 (its GND pin sits right above pin 1); the same on R26 / D19 / U7. SENS1 / SENS2 come 48 mm down from the top edge: in the DC-DC area U1's output (F.Cu) and U9's feed (B.Cu) cross every lane west of the modules' pins, and east of them only one track per layer fits between the pin rows (x 199.2 B.Cu, x 201.72 F.Cu). SENS1 leaves J10 on B.Cu under SENS1_PWR, runs F.Cu down x 191 and east at y 74.6, then B.Cu down x 199.2 (4 vias); SENS2 runs F.Cu straight down from J11, east at y 73.9, down x 201.72 (2 vias). Both come back west on B.Cu at y 97.1 / 97.75 (the one clear row under U9) and up to F.Cu into R24.1 / R26.1 from above. Render `review/routing_sensors.png`.
  - **LEDs done (2026-10-28)**, `route_local.py leds`: each LED resistor's pad 2 sits level with its LED's anode, so a straight F.Cu hop (R7 / R35 / R1 / R2 by the IMU switch, R14 / R15 / R22 / R23 by the relay output fuses). Render `review/routing_leds.png`.
  - **Screen USB-C done (2026-10-28)**, `route_local.py usb`: CC1 / CC2 sit between J16's two VBUS pins (both VBUS tracks fan into F11 and box them in on F.Cu), so each leaves by a via off its pad end and runs B.Cu NE to a via beside its 5.1k (CC1 → R41's east end, CC2 → R40's west end). Shield: the four shell pads tied on B.Cu; one 0.4 mm F.Cu line over F11 and the CC resistors, round into C37 from the east and on to R42. Render `review/routing_screen_usb.png`.
  - **Verification and tidy pass (2026-10-28), awaiting the user's review before the finishing pass.**
    - `generator/pcb/verify_nets.py <pcb> <net.xml>` (netlist from `kicad-cli sch export netlist --format kicadxml`): all 589 schematic pins match their board pads (only H6–H9, board-only mounting holes, have no schematic pin). On copper alone (no zones) every signal net is one piece; GND (149 pieces), +24V (17), +24V_F, +24V_IN (2 each) are joined by their planes / pours.
    - CAN GND: J3 pin 1, each J4 port's GND pin (3 / 11 / 19 / 27) and all shield tabs are on GND and reach the In1 plane through thermal spokes (no F / B track, so they don't show on an F / B render). Note J3's pinout is 1 GND / 3 CANH / 5 CANL (the schematic's), not the CiA 303-1 DB9 (2 CAN_L / 3 GND / 7 CAN_H).
    - `generator/pcb/audit.py <pcb> --bundles`: 90° / acute bends (2-track nodes; 3+ tracks at 45° are tees), 90° tees, jogs < 0.3 mm, uneven parallel bundles (nearest neighbours). Now 0 / 0 / 0 on every net, GND included. Fixes: the east-going MCU lanes (PA1 / PA0 / PC15) at 0.65 mm like the I²C fan, vias on their own lanes (no jogs); I²C B.Cu lanes 0.65 apart like the +3V3 spine (x 101.43 / 102.08 / 102.73); PA2 / PA3 0.7 apart from the +3V3 line on both sides of it; SWDIO's last jog into D1; J2.3's +3V3 stub now a 45° tee into the trunk; J1's fused GND fingers restyled (`place_moves.py`): a 0.3 mm bar through the finger ends with a vertex inside every finger instead of stubs teeing into a bar. Remaining spacing note: +3V3 / +5V / SWCLK on B.Cu at x 81–83 (three widths; set by the NRST via clearance).
    - Second sweep (whole board, by section, plus segment-angle and pad-entry checks): every segment is a multiple of 45°; PA15 now enters each INA236's pin 8 at 45° straight into the pad's centre line (was a vertical alongside it); PB6 / PC15 end straight in the opto pads (no 0.3 mm stub diagonals); the D19 opto link's 44.6° step fixed. Left for the finishing pass: crowded silk refs (R32 / R3–R5 over the I²C vias, R45 / R46, D4 / D5).
    - Renders `review/tidy_mcu_fanout.png`, `review/routing_complete.png` (updated).
  - **Planes checked (2026-10-28):** every zone refilled fills as one continuous piece (In1 GND, In2 +24V, the 24 V-input pours on F / B): no islands. DRC's starved_thermal (error) and isolated_copper (warning) checks are on and report nothing. Via clearances on both planes are separate small holes; no rows merge into slots. The only void is the winch isolation cut-out (x 161.1–179.2, edge to y 74.9), and only winch nets plus the +5V_24 coil feed cross it, so no other signal loses its reference. Renders `review/plane_in1_gnd.png`, `review/plane_in2_24v.png`.
  - **Analog guard added (2026-10-28)**, `route_local.py guard`: a priority-2 GND zone "Analog guard" on F.Cu around the load-cell block (J12 → R28 / R29 → C16–C18 → D20 / D21 → C17 / C22 → ADS1232, REF / CAP caps, C23–C25), 0.3 mm gap to the analog lines, notched out of the ADS1232's digital corner and off J3 (CAN currents stay out), stitched to In1 by 40 GND vias (2 mm grid, ≥ 0.7 mm from the analog lines). The input path was already clean before it: all F.Cu, no vias, over solid In1, no other net within 1 mm, J12 / J13 shields on GND, SIG± matched (10.39 / 10.45 mm). Any later general fill must have a lower priority than 2. Render `review/analog_guard.png`.
  - **Outer GND fill added (2026-10-28)**, `route_local.py fill`: GND zones "GND fill F" / "GND fill B" over the whole board, priority 0 (24 V-input pours raised to 1, analog guard 2), 0.3 mm gap, thermal reliefs (U7 pin 2 solid: tracks leave room for only one spoke), islands removed; the winch rule area keeps them off the 48 V copper. On F.Cu a 0.5 mm moat round the analog guard, so the guard meets the rest of GND only through its own vias. 245 stitching vias on a 5 mm grid (worked out at build time; clear of other nets on both layers, holes and part bodies; not in the guard, the winch area or the input pours). Renders `review/gnd_fill_F.png`, `review/gnd_fill_B.png`.
  - **Teardrops added (2026-10-28)**, `generator/pcb/teardrops.py` (last in the chain, after `route_local.py`): KiCad 9.0.2's teardrop generator isn't reachable from Python, so the script builds KiCad's straight teardrops itself: every non-GND track end in a via or pad (track narrower than 90 % of the via / pad across it) gets a zone from the via circle / pad edge, centred on the track (the narrower side of the via / pad sets both halves, so off-centre entries stay symmetric; 0 lopsided), length half the via / pad size (≤ 1 mm, never past the segment), tapering to the track width. 280 at vias, 286 at pads (pad entries with no room for a centred teardrop get none). They are saved as KiCad's own teardrop zones (`$teardrop_padvia$`, `(attr (teardrop (type padvia)))`; KiCad loads them as teardrops) and filled with the board's clearances; pads / vias have their teardrop flag set, so KiCad's GUI tool regenerates the same. GND ends are skipped (they join the pours). Render `review/teardrops_closeup.png`.
  - **Silkscreen pass (2026-10-29)**, `generator/pcb/silk.py` (last in the chain, after `teardrops.py`) and `generator/pcb/silk_audit.py` (labels crowding / on pads / on vias / far, strokes < 0.15 mm): removed the 0.12 mm pin-1 dots (radius 0.03, unprintable; they caused 12 of the old DRC notes) from the board and from the 10 project-library footprints that carried them (`MES4-Carrier-EC.pretty`, so board and library still match); widened every silk stroke under 0.15 mm to 0.15 (JLC minimum); moved 28 reference labels that crowded each other (F3–F5 / R15 / R22 / R23, R43 / R44, R45 / R46, C6 / C7, D4 / D5, C10 / R33, R32 by the R3–R5 stack), sat on another part (J16 on F11, D26 on Q7) or on a via (U2–U5, J1, F2, L1 …) to clear spots next to their parts (table in `silk.py`). Then every part's reference put on the silk (2026-10-29): the 19 the footprints kept on F.Fab only (J5, SW2, TP1–TP9, H1, H6–H9, the power LEDs LED1 / LED2 / LED3 / LED8) are now 1 mm silk labels. The 24V / 9V / 5V / 3V3 tags step 0.5 mm left and each power LED's ref sits right of its tag, in the LED's row (no room between LED and resistor). Test-point labels sit level with their pads; H6–H9 labels sit inboard of the servo-driver standoffs. H2–H5 are bare mounting holes and stay unlabelled, so 191 of 195 footprints carry a silk ref. No label sits on a via any more: R4 / R5 / R10 / U8 / D25 / Q1 moved off routed vias, and `silk.py` drops the GND stitching vias under labels (17; fill area and fragments unchanged). `silk_audit.py` now measures glyph extents, not the 1.7 mm text box; it lists only the four power-LED refs (3.5 mm from their LEDs, by design) and R4 / R5 (0.1 mm apart, set by the resistors' 1.25 mm pitch). C27 / C28 / C30 / C32 labels sit inside their own outlines. Render `review/silkscreen.png`.
  - **Next: the rest of the finishing pass:** JLC DFM check; BOM / CPL with LCSC numbers re-verified; Gerbers + drill; final 3D review.
  - **Rebuild chain** (scratchpad `apply_all.sh`): restore the 24 V-input board, then `place_moves.py` → `route_relays.py` → `route_srv_scr.py` → `route_rails.py dc,aux,5v24,mod5v,imu,srv5,sens,3v3,tp` → `route_winch.py` → `route_analog.py` → `route_comms.py` → `route_mcu.py` → `route_local.py` → `teardrops.py` → `silk.py` → `git checkout MES4_Carrier_EC.kicad_pro`. The committed `.kicad_pcb` is the result; the scripts document how it was made.
  - **`generator/pcb/probe.py`** (pre-check before DRC): `probe.py <pcb> path <net> <w> F:x,y;... B:x,y;...` lists copper within clearance of a planned path (vias between runs); `rows` / `cols` scan for clear straight corridors. Filters by bounding box, so long tracks count.
  - Kept free on purpose: the load-cell input area (J12 → R28 / R29 → C16–C18 → ADC pins 11 / 12, FB2's +5V comes over the top on B.Cu at y 62.8), the pull-ups' I²C / PA15 pads from the west, F.Cu over the relay lanes below y 80. LC_EXC+ (FB2 pin 2 → J13 pin 1) has a B.Cu gap between J3's shield pad and the +5V run at y 62.8.
  - **CH1's output moved to B.Cu** (via pair on the R14 branch at 135.78 / 82.6, B.Cu up x 134.78 → 132.83 to J6): its old F.Cu column walled off the only west–east channel above the relays.
  - +24V_DC / +24V_AUX: L → bulk cap → small cap → module input, 1.0 mm F.Cu (the AUX caps in a straight column at x 171.26).
  - +5V_24: 1.0 mm F.Cu trunk C6 → y 84.89 → y 77.05 → K1.5, coil chain K1–K4 at x 119.64, flyback diodes 0.5; winch coils via a via off each diode's pad end and a 0.5 mm B.Cu feed from U1 pin 6 (no B.Cu under the winch pads).
  - Module 5 V: F2 → FB1 → via → 0.8 mm B.Cu → via under J1 pin 22 (pin 20 joins at 45°); C8 / C9 on B.Cu below the pin 2–10 escapes. FB2 and R1 on F.Cu.
  - +3V3_MOD (0.3): J1 pin 4 → via → B.Cu to J2 pin 3 and the ADC (vias off pins 19 and 1); B.Cu spine x 103.38 with a via beside each INA236 cap; B.Cu bus at y 71.08 north of FB1's via to the I²C pull-ups (via off R3) and the INA spine; optos U6 / U7 and servo pull-ups R36 / R37 on F.Cu, crossing the relay lanes only above the relays.
  - +9V_IMU, IMU_9V, +5V_SRV, SENS1/2_PWR, and the five test points (TP4 "5V MCU" runs ≈ 100 mm from J1's +5V via along the bottom edge: worth moving TP4 or re-assigning it).
  - LC_EXC+ was routed with the load-cell group.
- **High-current routing done (2026-10-28)**, scripts in `generator/pcb/route_*.py` (one-shot, already applied), render `review/routing_high_current.png`:
  - 24 V input: F.Cu pours (zone connect solid) `24V IN` J5 → F1, `24V FUSED F` F1 → Q1 tab, `24V OUT` Q1 pin 3 with a 4×3 +24V via field into In2; `24V FUSED B` on B.Cu under Q1 / F1 with 16 + 8 thermal vias (2 mm pitch so In1 isn't walled off); GND pours on F.Cu and B.Cu at J5 pin 2 with a 4×3 GND via field. J5 pins 1 / 2 set to solid zone connection (the GND pin was on 0.4 mm thermal spokes into the 0.5 oz In1). Gate R6 → D8 → Q1 at 0.3 mm.
  - Relays: shunt → COM, NO → fuse, fuse → TVS / LED resistor at 1.5 mm on F.Cu. RLY1_OUT on F.Cu up the x 132.8 column to J6; RLY2–4_OUT drop through a via pair on a 45° line to B.Cu lanes at x 146.1 / 147.9 / 149.7 and fan out to J7–J9.
  - Servo: +24V_SRV on F.Cu **above** J17 (y 135.66) to J15, C31 on a 45° branch; F9 → C32 bulk.
  - Screen: U10 pin 4 → 2.0 mm F.Cu bus (y 127.05) running over the + pads of C35 / C33 / C34 (no stubs) → C38; 2.0 mm B.Cu trunk U10 → x 198.5 → y 143.6 (above the TP row) → y 147.9 (below H1 / K4) → TP9 → F11 (≈ 0.12 V drop at 3 A); F10 tapped by a via off its pad end onto the trunk; VBUS F11 → J16 as two separate 0.7 mm tracks, one per VBUS pad (A9 / B9 are 0.7 mm on a 1 mm pitch with CC between), D22 at 1.0, R40 / R41 at 0.3.
  - **Routing style (user, 2026-10-28): 45° bends only, never 90° (T-branches leave at 45° too); one width per run, width changes only at a pad, never track-to-track.** Check: no 90° joints and no width steps on any non-GND net (J1's fused GND finger bars are the accepted exception).
  - Still open from these nets: the four INA236 IN− Kelvin lines (U*-IN-), routed with the analog group.

**Next: route, in this order** (one group at a time; DRC and show the user a render after each; commit only when the user says so)

| # | Group | What to route | Class | Watch-outs |
|---|---|---|---|---|
| 1 | 24 V input | J5 → F1 → Q1 → +24V, TVS D9, bulk C1–C3 | F.Cu pours (15 A), not tracks | Q1 drain-tab copper for ≈ 2.2 W; a via field from Q1's output into In2 |
| 2 | AUX 24 V filter + DC/DC | L1 / L2 → bulk caps → U1 / U9 / U10 inputs; outputs +5V_24, +9V_IMU, +5V_SCR | 24V_Power / Power / Out_3A | Short input-cap loops |
| 3 | Module 5 V feed | +5V_24 → F2 → FB1 → C8 / C9 → J1 pins 20 / 22 | Power 0.5 or wider | ≈ 30 mm; the module's only 5 V |
| 4 | Relays CH1–CH4 | +24V via → shunt → relay contacts → 3 A fuse → output; then coil, FET, flyback | Out_3A 1.5 on the load path | **INA236 IN+ / IN− as a tight Kelvin pair from the shunt pads** (still to do); load returns away from the ADC |
| 5 | Winch relays | K5 / K6 contacts → J18, coil drive | Winch_48V | ≥ 2 mm from other copper, no GND pour under J18 / contacts |
| 6 | FE-URT-2 servo | F9 → +24V_SRV → J15; F10 → +5V_SRV → J17; TX / RX via R38 / R39, D23 / D24 | Out_3A for +24V_SRV | +24V_SRV passes under J17: B.Cu if needed |
| 7 | Screen 5 V | +5V_SCR → F11 → VBUS_SCR → J16, CC resistors | Out_3A | 3 A: short and wide |
| 8 | Load cell | J12 SIG± → R28 / R29 → ADS1232; J13 EXC from FB2; REF filter; CAP | LoadCell pairs | Before the digital crowds it; nothing digital crossing |
| 9 | CAN | CANH / CANL: J1 → J3 → the four J4 ports, D6 / D7 | CAN pair, ≈ 120 Ω diff | Bus with short stubs |
| 10 | MES4-MCU escape + debug | SWD / VCP → J2, I²C → U2–U5 (R3–R5), PA2 / PA3 → J17, PA4–PA6 → ADC, PB6 / PC15 → sensors, relay gates | Default 0.2 | J1's outer side is kept free for this |
| 11 | Sensors 1 / 2 | J10 / J11 → opto blocks → PB6 / PC15 | Default / Power | Slow; use the channel by the FE-URT-2 or B.Cu |
| 12 | IMU 9 V | +9V_IMU → SW2 → J14, LED8 | Power | Short |
| 13 | LEDs, pull-ups, test points | | Default / Power | Last |

After routing: unrouted = 0; refill planes and check islands / starved thermals / +24V clearance holes cutting GND returns; decide on F.Cu / B.Cu GND fill (stitch to In1 if added); teardrops; silkscreen pass; JLC DFM check; BOM / CPL with LCSC numbers re-verified; Gerbers + drill; final 3D review.

**PCB workflow (learned the hard way)**
- **KiCad must be closed** before any script writes the `.kicad_pcb`: check there is no `~MES4_Carrier_EC.kicad_pcb.lck` and `pgrep -fl MacOS/kicad` is empty. Ask the user to close it.
- Back up the board to the scratchpad before every scripted edit.
- `pcbnew.SaveBoard` rewrites `MES4_Carrier_EC.kicad_pro`: afterwards run `git checkout MES4_Carrier_EC.kicad_pro` (or rerun `run.sh` if `gen.py` changed). KiCad does the same on exit; the content is equivalent but restore it anyway.
- KiCad's Python: `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`. CLI: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`.
- DRC: `kicad-cli pcb drc --schematic-parity --format json --severity-all -o drc.json MES4_Carrier_EC.kicad_pcb`.
- Renders for the user: `kicad-cli pcb export svg --layers F.Cu,F.Silkscreen,Edge.Cuts --mode-single --exclude-drawing-sheet`, edit the `viewBox` to crop (units are board mm), screenshot with headless Chrome; 3D with `kicad-cli pcb render`.
- Helper scripts (one-shot, already applied; kept for reuse) in `generator/pcb/`:
  - `vias_gnd.py <pcb>`: GND vias on every SMD GND pad.
  - `vias_24v_j1.py <pcb>`: +24V via patterns (`GROUPS`) and the per-finger J1 GND vias. Run `strip_net_tracks.py <pcb> +24V` first. **Don't rerun on the current board**: it would re-add per-finger J1 vias on top of the fused bars.
  - `fuse_j1.py <pcb> generator/pcb/vias_24v_j1.py`: fuses J1 GND runs into bars.
  - `strip_net_tracks.py <pcb> <net>[,<net>]`: removes all tracks and vias of those nets (text level).
  - `strip_del.py <pcb>`: removes `__DEL__` texts and their group members.

**Via and routing style the user wants**
- Vias straight off the pad end at 0 / 90 / 180 / 270° only: no 45° stubs, no bends, as close as possible (gap 0.1 mm). Good examples: C6 / C7.
- The same pattern on every part of a type (e.g. both inductors, all four shunts). Uneven patterns get flagged.
- Keep stubs short; move silkscreen labels out of the way rather than moving vias.
- Fuse neighbouring same-net pads (like the J1 GND fingers) instead of a via per pad when it frees routing space.
- Be quick and token-efficient; show a render of what changed; commit only when the user says "commit".

## How this schematic is made

The schematic is **generated by Python**. Change the generator, not the `.kicad_sch` files: hand edits are overwritten on the next run.

| Path | What |
|---|---|
| `generator/run.sh` | Regenerates everything, then runs ERC, exports the netlist and writes `MES4_Carrier_EC.pdf`. **Close KiCad first**: on exit KiCad rewrites `MES4_Carrier_EC.kicad_pro` from its stale copy, which drops the net classes. Re-run `run.sh` if that happens. |
| `generator/gen.py` | One function per sheet: `main_sheet`, `can_sheet`, `power_sheet`, `relay_sheet` (×2), `sensor_sheet`, `loadcell_sheet`, `aux_sheet`, `winch_sheet`, `pinout_sheet` (page 11 finger table, hand-written rows), `root_items`. Note texts use `{tag}` / `{Sheet/tag}` placeholders that resolve to reference designators. |
| `generator/parts.py` | `NEWP`: every part that isn't copied from the MES4-Flasher, with a **verified** LCSC number. |
| `generator/builder.py` | Sheet builder. `fix_junctions`, `prune` / `clean`, `table` (KiCad 9 table objects; cell text resolves `{tag}`s), `assign_refs` (annotation), multi-unit support, and `from_template`, which re-UUIDs everything it copies. |
| `generator/can_parts.py`, `aux_parts.py` | Project symbols and footprints: 1×4 RJ45, URB 10 W / 20 W, TCA9535, IM03GR, KF250NH-4P. They're copied from the MES3.1 / MES2 Harvester / MES2_Extension projects and upgraded with `kicad-cli fp upgrade`. |
| `generator/libs.py` | Rebuilds `MES4-Carrier-EC.kicad_sym`, `.pretty/` and `.3dshapes/` from what the sheets use. |
| `generator/import_footprints.py` | One-time import of all footprints and nets into an empty `.kicad_pcb`, grouped by sheet below the outline (run with KiCad's Python, KiCad closed). Done on 27 Oct 2026: DRC schematic parity 0 issues. **From now on use F8 (Update PCB from Schematic) in KiCad**; the script refuses a board that has footprints, except with `--add-missing <netlist>`, which adds only symbols that have no footprint yet (used for H6-H9). |
| `generator/group_footprints.py` | Puts the footprints that must sit together into 21 named KiCad groups (24 V input, DC/DC, M.2 socket, each relay channel with its shunt + INA236, each sensor, load cell, IMU, screen, servo, winch, ...), packed below the outline. Only packs brand-new footprints (the `--add-missing` row); never moves a placed or parked part, and stops once groups have been edited in KiCad (regroup there from then on; `--force` rebuilds the table). The MES4-MCU slot group (J1 + H1, 41.75 mm socket to standoff, with the MES4-Flasher's slot silkscreen) was made by hand. |
| `generator/netdump.py` | `python3 generator/netdump.py <netlist> /SheetName/` prints every part's pin → net. |
| `generator/checks.py` | Pin / pad, single-pin net, duplicate UUID and LCSC checks on the netlist (run by `run.sh`). |

Several sheets are **templates from `../../MES4-Flasher/`**: Relays, Sensors, LoadCell and Main. That's done with `Sheet.from_template`, followed by deleting regions, relabelling and swapping parts.

Checks to run after every change (all passed at handoff, 190 parts):
- ERC: 0 errors, 0 warnings.
- Every symbol pin has a footprint pad.
- No single-pin nets.
- No duplicate UUIDs.
- Every purchased BOM line has an LCSC number (the net tie and bare test pads have none).

`run.sh` runs ERC, then `generator/checks.py` for the other four checks, and stops on a failure.

**Rules the user set:**
- Every part needs a real, checked LCSC number. Never guess one; check `https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=Cxxxx`.
- LEDs must be JLC **Basic** parts.
- Write in the Flasher's style.
- `gen.py` / `libs.py` write to an **absolute** `OUT` path: running an old checkout's generator (e.g. in a git worktree) overwrites this project's generated files. Re-run `run.sh` here afterwards.

## GPIO map: a deliberate deviation from the MES4 standard

The user first set the rule **"all GPIOs must match the MES4-MCU standard"** (`../../MES4-MCU/CARRIER_INTERFACE.md` §2c). On 2026-10-27 they then decided, under pressure from their boss, to **drop the relay coil feedback** on this board to free GPIOs. That is the current design (branch `mes4-gpio-standard`); don't put the feedback back without asking.

| Pin (finger) | CIF §2c function | This board |
|---|---|---|
| PA8 (31) / PC6 (29) / PB3 (61) / PA7 (35) | Relay CH1–CH4 drive | Same |
| PA0 (49) / PA1 (47) | Relay CH1 / CH2 coil feedback | **Winch CLK / ACLK relay drive** (IM03GR K5 / K6, AO3400A Q6 / Q7) |
| PA2 (45) / PA3 (43) | Relay CH3 / CH4 coil feedback | **Door servo UART, USART2** TX / RX → J17 (FE-URT-2) |
| PA15 (63) | INA226 ALERT | Same (INA236 ALERT) |
| PA4 / PA5 / PA6 (41 / 39 / 37) | ADS1232 DRDY, SCLK, PDWN | Same |
| PB6 (59) / PC15 (51) | Spare (inputs only) | Autonics sensor 1 / 2 (PC817 opto) |
| I²C1 (53 / 55) | INA226 0x40 / 41 / 44 / 45, optional TCA9535 | 4 × INA236 at 0x40 / 41 / 42 / 43 |

What went with it:
- The Flasher template's 10k / 15k / 10 nF coil dividers are removed in `relay_sheet()` (`fb_parts` in `TPL`).
- Relay diagnosis is current-monitor-only (INA236) (`RELAY_DIAG`): an open coil or dead driver now looks like a contact that doesn't close ("ON, I ≈ 0").
- The SC16IS740 I²C-UART bridge, its 16 MHz crystal and caps, and the TCA9535 expander are gone (and out of `parts.py`). `aux_parts.tca9535_symbol()` and `im03gr_symbol()` are kept as library code.
- The photoMOS winch idea (KAQY214S C2890344, back-to-back LEDs, 220 Ω C25091 for ≥ 5 mA worst case; KiCad `Package_SO:SO-4_4.4x3.9mm_P2.54mm` matches the datasheet land) was **not** used: the user chose the IM03GR relays on PA0 / PA1. TCA9539PWR (C131972, RESET pin) was the alternative if an expander comes back.

## Still unverified (tell the user; nothing to change yet)

- ARZOPA Z1C screen at 5 V only (no USB-PD source): check full brightness on the bench.
- FE-URT-2 must be set to **3.3 V UART levels** (noted on the AuxPower sheet and in the README). Bench check: read a servo's ID / position at 3.3 V; the FE-URT-2 datasheet wasn't found, so it's unconfirmed whether the switch also changes the servo-bus side. Servo supply is raw 24 V through F9 3 A PTC: check the servos' stall current against it.
- IMU = 3DM-CV7-AHRS on the C-Series Connectivity Board (6212-3009): J14 9 V → board Vaux (5.2–28 V), never Vpri (3.2–5.2 V); not both at once (SW2 off with the USB cable). Draw ≈ 45 mA (sim IMU1), so SW2's 0.5 A rating is fine.
- Low stock at last check: URB2409S-10WR3 C7424703 (78), SMBJ30A C113998 (920 global), L1 SWPA5040S100MT C84608 (LCSC page "not found", JLC page live).
- Custom footprints checked against the manufacturer drawings (2026-10-27): RJ45 1×4 now built from the HCTL drawing (14.0 mm ports, Ø1.0 / Ø1.5 / Ø3.2 holes; the JLC library part has 13.97 mm ports, 2.50 mm rows and Ø3.5 pegs, so it isn't used); the screen converter is now URB2405YMD-20WR3 (1" x 1", 2026-10-28): footprint from the JLC/EasyEDA part C5369777, checked against the Mornsun URB_YMD-20WR3 drawing (pins 1 Ctrl, 2 GND, 3 Vin, 4 +Vo, 5 Trim, 6 0V). Still worth a print-out test fit before ordering.
- PCB: placed, planes and vias done, not routed yet (see "Start here").

## Design review R1 (MES4-Carrier-EC_Design_Review.pdf, 27 Oct 2026)

| ID | Status |
|---|---|
| M1 INA226 40 V vs SMBJ30A 48 V clamp | Fixed: U2–U5 are now INA236AIDDFR (C5443912, 50 V abs max, TSOT-23-8), addresses 0x40–0x43 via A0 (GND / VS / SDA / SCL). INA238 / INA228 (85 V) had 0 LCSC stock |
| M2 24 V on the load-cell terminals | Silkscreen only (user's choice: no keyed connector): "5V LOAD CELL – NEVER 24V" box, J12 / J13 away from 24 V terminals |
| M3 J15 polarity | Fixed: pin 1 = +24 V, pin 2 = GND_24V. Re-pin the Harvester CN5 cable |
| M4 Simulations | Done for the whole board: 16 LTspice benches in `sim/` grouped by sheet, report `sim/report.html`, fed by the real supply (DDR-480C-24 at 24 V and a 24 V Li-ion pack via XY-CD63L, diode-OR'd by an AB20). All pass; PWR3 (IEC surge) is not applicable to this internal, isolated supply. Hold-up on total loss 4.0 ms. Datasheet checks pass: U1 / U9 / U10 surge 50 V for 1 s, Q1 I_DM −360 A, F1 melting I²t 97.8 A²s. Still open: F11 at its 3 A hold if the screen draws 3 A; pack full-charge voltage vs the AB20 variant (A/B/C are 30 V) |
| L1 LED resistor power | Already 1206 (0.25 W): no change |
| L2 5 mA threshold | Fixed: 3 mA in the diagnosis note |
| L3 Servo return via logic GND | Layout: J15, J17 and NT1 together, away from the load cell; heavy wire on J15 |
| L4 PA3 back-power | Fixed: R38 = 1 kΩ |
| L5 RJ45 looks like Ethernet | Silkscreen + panel "CAN – NOT ETHERNET" (CAN note on Main) |
| L6 Stale Power notes | Fixed: 13 A worst case, Q1 2.2 W |
| L7 PTC derating | Noted (2.2 A at 60 °C > 2 A); check enclosure temperature |
| L8 Screen on 5 V | Bench test (unverified list) |
| L9 DC/DC pins | Closed: U1, U9, U10 symbols and footprints match the JLC library, U10 also the YLPTEC drawing |

## Layout checklist (from the reviews)

- U2–U5 INA236 use the project footprint `TSOT-23-8_TI_DDF` (TI's DDF land pattern, 0.45 mm pads); KiCad's generic TSOT-23-8 broke the 0.2 mm clearance.
- If net classes go missing in KiCad (KiCad rewrites `.kicad_pro` on exit), close KiCad and rerun `run.sh`.
- Winch: Winch_48V nets ≥ 2 mm from other copper, no GND pour under J18 / relay contacts, no ESD to GND on J18.
- Q1 drain-tab copper for 2.2 W.
- J15, J17 and NT1 together, away from the load cell (L3).
- Silkscreen: "5V LOAD CELL – NEVER 24V" (filled box) at J12 / J13, placed away from the 24 V terminals; "CAN – NOT ETHERNET" at J4; polarity marks on every power terminal.

## Supply into the carrier (from the user, 27 Oct 2026)

48 V main battery → Mean Well DDR-480C-24 (set 24 V, isolated, OVP 28.8–35 V) → Autoro AB20 line 1. 24 V 12 Ah Li-ion pack → XY-CD63L discharge monitor → AB20 line 2. The DDR also charges the pack through a charge board. The AB20 is a diode-OR ATS (higher input wins, zero delay, blocks back-feed). Pack cell count unknown: 7S Li-ion = 29.4 V full, 8S LiFePO4 = 29.2 V. The AB20A/B/C are rated 30 V, the AB20D 60 V.

## Decisions already made with the user (don't re-ask)

- 2 Autonics sensors (not 4), opto + fuse only, on PB6 / PC15.
- Relay drivers: AO3400A + 100 Ω + 100k pull-down (CIF §7a), not the Flasher's 2SC2884.
- Current monitors: INA236 (50 V), not the CIF's INA226 (40 V), because of the SMBJ30A clamp (review M1).
- No relay coil feedback; PA0 / PA1 = winch, PA2 / PA3 = servo USART2 (above).
- DB9 male to the IPC: **1 GND, 3 CAN_H, 5 CAN_L** (the IPC's pinout, deliberately not CiA 303-1). 1×4 RJ45 without magnetics, T568B pins 1 H / 2 L / 3 GND.
- IMU 9 V: MES3.1 parts (URB2409S-10WR3, SS12D10G5), LED8 after the switch.
- Screen: USB-C 5 V / 3 A source on URB2405YMD-20WR3 (C5369777, 25.4 x 25.4 mm, replaced the 2" x 1" URB2405LD-20WR3 to save space; 50 V 1 s surge like before), Rp 10k. Output bulk C38 100 uF / 16 V (CX RVT1C101M0605, C81993) per the YMD datasheet Cout.
- Servo: FE-URT-2 like the MES2 Harvester, 24 V supply terminal (pin 1 = +24 V, unlike Harvester CN5) plus 4-pin UART terminal, on USART2.
- FE-URT-2 mounts on the carrier as on the MES3 E-Crawler / MES3.1: H6-H9 YIYUAN SMTSOM320BTR M3 x 2 mm SMD standoffs (C5301780, same series as the H1 hold-down) on its 48.5 x 28.7 mm holes (Feetech drawing). A1 is the board-only outline with a footprint keep-out under it. Its STEP isn't on file: drop `LC-PCB-PCB0-URT-2201.STEP` into `MES4-Carrier-EC.3dshapes/`. Generator symbols added after the fact take UUIDs from a separate counter range (see gen.py) so no existing PCB link moves.
- GPS (ArduSimple simpleRTK4 Dual, A2) is stacked above the FE-URT-2 on H10-H12: YIYUAN SMTSOM365BTR M3 x 6.5 mm SMD standoffs (C5301796) + M3 x 12 mm male-female spacers fitted by hand (not in the JLC BOM), on its left-bottom, left-top and right holes (the two middle holes are unused). Underside 18.5 mm up: clears the FE-URT-2 (13.5 mm) and every carrier part (relays 15.5 mm). SMAs and the GPS USB-C face west; it's powered from that USB-C, nothing on the carrier. The FE-URT-2's screw terminal and servo sockets are under the RTK: wire them before fitting it.
- Load cell: keep the KF250NH terminals (no keyed connector: JLC doesn't stock the mating plugs); silkscreen warning instead.
- Winch: the MES2_Extension's two IM03GR relays with the contact interlock, on PA0 / PA1.
- Winch 48 V isolation: J18 / WINCH_* / ILK_* touch only relay contacts (net class `Winch_48V`, ≥ 2 mm to other copper on the PCB). No ESD to GND on J18.
