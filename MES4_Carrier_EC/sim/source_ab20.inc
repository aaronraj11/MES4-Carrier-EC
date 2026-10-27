* Real supply chain (user, 27 Oct 2026): 48 V battery -> Mean Well DDR-480C-24 (set 24 V, isolated, 20 A) -> AB20 line 1;
* 24 V 12 Ah Li-ion pack -> XY-CD63L discharge monitor -> AB20 line 2. AB20 = diode-OR ("zero delay", anti-backflow).
* Pack full charge taken as 29.4 V (7S Li-ion; 8S LiFePO4 is 29.2 V). Node ab = AB20 output.
.model SBD20 D(Is=50u N=1.3 Rs=8m Cjo=1n BV=60 IBV=1m)          ; AB20 Schottky, ~0.45 V at 10 A
Vddr dd 0 PWL(0 {Vddr} {tddr} {Vddr} {tddr+1m} 0)              ; DDR-480C-24 output (drops at tddr if set)
Rddr dd d1 10m
Dab1 d1 ab SBD20
Vpk  pk 0 {Vpack}
Rpk  pk p1 60m                                                  ; 24 V 12 Ah pack (assumed 60 mohm)
Sxy  p1 p2 xyc 0 SWXY                                           ; XY-CD63L output switch
Vxyc xyc 0 PWL(0 1 {txy} 1 {txy+10u} 0)                          ; opens at txy (low-voltage cut-off) if set
.model SWXY SW(Ron=5m Roff=100Meg Vt=0.5 Vh=0)
Dab2 p2 ab SBD20
Rab ab 0 100k
