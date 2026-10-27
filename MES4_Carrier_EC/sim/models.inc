* Generic models for the MES4-Carrier-EC benches (datasheet-class, not vendor models)
.model AO3400A VDMOS(Vto=1.05 Kp=25 Rd=12m Rs=6m Rg=1.5 Cgs=550p Cgdmax=250p Cgdmin=30p Cjo=150p Is=1e-12 Rb=8m)
.model D1N4148W D(Is=2.52n Rs=0.568 N=1.752 Cjo=4p M=0.4 Tt=20n BV=100 IBV=100u)
.model SS34   D(Is=20u Rs=30m N=1.1 Cjo=300p M=0.5 BV=40 IBV=1m)
.model DLED   D(Is=1e-18 N=1.8 Rs=5 Cjo=30p)                       ; PC817 input LED, Vf ~1.2 V at 2 mA
.model SMF6V0 D(Is=1e-12 N=1.2 Rs=0.5 BV=6.9 IBV=1m)                ; module 5 V TVS
.model OD SW(Ron=15 Roff=100Meg Vt=0.5 Vh=0.1)                      ; open-drain output stage
