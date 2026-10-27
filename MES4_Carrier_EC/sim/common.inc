* MES4-Carrier-EC power path, shared by the three test benches (values from the schematic, 27 Oct 2026)
* Ceramic 10 uF / 50 V caps are modelled at ~4 uF (DC-bias derating at 24-30 V).
* Electrolytic ESR / ESL are typical datasheet-class values (100 uF 63 V: 0.25 ohm, 47 uF 100 V: 0.6 ohm).
.model SMBJ30A D(Is=1e-12 N=1.2 Rs=1.08 BV=35 IBV=1m Cjo=2n)   ; BV 33.3-36.8 V, Vc 48.4 V at 12.4 A
.model DBODY  D(Is=1e-9 N=1.5 Rs=5m Cjo=1n)                    ; Q1 body diode
.model SWQ    SW(Ron=13m Roff=10Meg Vt=4 Vh=0.5)                ; Q1 AGM60P90D on when Vsg > ~4 V
* --- from the XT30 (node in) to +24V (node v24)
Rf1  in   f     4m                         ; F1 15 A Nano2
D_Q1 f    v24   DBODY                      ; body diode conducts before the gate is up
S_Q1 f    v24   v24 0 SWQ                  ; gate pulled to GND_24V by R6, D8 clamps Vsg at 15 V
D9   0    v24   SMBJ30A                    ; TVS after Q1
C1   v24  0     100u Rser=0.25 Lser=10n    ; 100 uF 63 V bulk
C2   v24  0     4u   Rser=5m               ; 10 uF 50 V ceramic
C3   v24  0     100n Rser=20m
Rbase v24 0     120                        ; relays off, LEDs, sensors: ~0.2 A
* --- logic DC/DC branch (+24V_DC, U1 URB2405S-6WR3, ~3.75 W in)
L1   v24  vdc   10u  Rser=83m              ; Sunlord SWPA5040S100MT
C4   vdc  0     4u   Rser=5m
C5   vdc  0     100u Rser=0.25 Lser=10n
B_U1 vdc  0     I=if(V(vdc)>9, 3.75/V(vdc), 0)*limit((time-{ton})/5m,0,1)
* --- aux branch (+24V_AUX, U9 IMU ~0.5 W in (3DM-CV7 dev kit), U10 screen)
L2   v24  vaux  10u  Rser=83m
C26  vaux 0     4u   Rser=5m
C27  vaux 0     100u Rser=0.25 Lser=10n
C28  vaux 0     47u  Rser=0.6  Lser=10n
C30  vaux 0     47u  Rser=0.6  Lser=10n
B_U9 vaux 0     I=if(V(vaux)>9, 0.5/V(vaux), 0)*limit((time-{ton})/5m,0,1)   ; IMU: CV7 dev kit 0.4 W / 85 %
* --- servo branch (+24V_SRV, F9 3 A PTC, FE-URT-2 idle)
Rf9  v24  vsrv  50m
C31  vsrv 0     100n Rser=20m
C32  vsrv 0     47u  Rser=0.6  Lser=10n
