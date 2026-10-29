"""New parts (not on the MES4-Flasher). LCSC numbers verified on lcsc.com / jlcpcb.com (2026-10-27)."""
NEWP = {
    'F_IN': dict(lib='Device:Fuse', value='15A', fp='MES4-Carrier-EC:Fuse_Littelfuse-NANO2-451_453', lcsc='C44480',
                 ds='https://www.littelfuse.com/products/fuses/surface-mount-fuses/nano2-fuses/451-453',
                 desc='main 24 V input fuse, Littelfuse 0451015.MRL Nano2 2410, 15 A fast, 65 V DC '
                      '(worst case 8.5 A stays under the 75 % derating; 10 A alt: 0451010.MRL C44479)'),
    'F_CH': dict(lib='Device:Polyfuse', value='3A', fp='MES4-Carrier-EC:Fuse_2920_7451Metric', lcsc='C22435908',
                 desc='relay output PTC, LUTE 2920L300/36GR: 3 A hold, 5 A trip, 36 V'),
    'Q_RP': dict(lib='Transistor_FET:Q_PMOS_GDS', value='AGM60P90D', fp='Package_TO_SOT_SMD:TO-252-2',
                 lcsc='C5464761',
                 desc='reverse-polarity P-MOSFET, AGMSEMI AGM60P90D: -60 V, 13 mOhm max @ -10 V, TO-252 '
                      '(1 G, 2 D tab, 3 S); give the drain tab a large copper area',
                 # JLC's TO-252 footprint has its tab the other way round and its origin on the body centre, 1.8 mm
                 # from the pads' centre (Fabrication Toolkit placement fields, checked by pcb/cpl_check.py)
                 extra={'FT Rotation Offset': '180', 'FT Position Offset': '-1.8,0'}),
    'DZ': dict(lib='Device:D_Zener', value='MMSZ5245B', fp='Diode_SMD:D_SOD-123', lcsc='C2126',
               desc='P-FET gate clamp, 15 V Zener (CJ MMSZ5245B): keeps Vgs inside +/-20 V'),
    'TVS': dict(lib='Device:D_Zener', value='SMBJ30A', fp='Diode_SMD:D_SMB', lcsc='C113998',
                desc='24 V input TVS, MDD SMBJ30A: 600 W, 30 V standoff, 48.4 V clamp (CIF §7a); alt MCC C669047'),
    'L_DC': dict(lib='Device:L', value='10uH', fp='Inductor_SMD:L_Sunlord_SWPA5040S', lcsc='C84608',
                 desc='DC/DC input pi-filter inductor, Sunlord SWPA5040S100MT: 10 uH, 2.1 A, 83 mOhm'),
    'FB_5V': dict(lib='Device:FerriteBead', value='120R', fp='Inductor_SMD:L_0805_2012Metric', lcsc='C79382',
                  desc='module 5 V feed ferrite, Murata BLM21PG121SN1D: 120 Ohm @ 100 MHz, 3 A, 30 mOhm'),
    # ---- aux power: IMU 9 V (MES3.1-Carrier-LH parts) + screen USB-C 5 V
    'U_IMU': dict(lib='MES4-Carrier-EC:URB2409S-6WR3', value='URB2409S-6WR3',
                  fp='MES4-Carrier-EC:PWRM-TH_YLPTEC_URXXXXXS-6WR3', lcsc='C7468814',
                  ds='https://www.lcsc.com/product-detail/C7468814.html',
                  desc='IMU supply, YLPTEC URB2409S-6WR3: 24 V to 9 V 0.67 A, 6 W isolated, SIP-8 (the logic DC/DC\'s family and '
                       'footprint; the MES3.1 carrier\'s 10 W URB2409S-10WR3, C7424703, is not in JLC\'s assembly library)'),
    'C_IMU_IN': dict(lib='Device:C_Polarized', value='47uF 100V', fp='Capacitor_SMD:CP_Elec_8x10', lcsc='C48935391',
                     desc='URB2409S input capacitor, JIERR RV100V47M8X10 (datasheet Cin 47 uF / 100 V, MES3.1 C1)'),
    'C_IMU_OUT': dict(lib='Device:C', value='22uF 16V', fp='Capacitor_SMD:C_0805_2012Metric', lcsc='C76637',
                      desc='9 V output capacitor, TDK C2012X5R1C226KT000E (datasheet Cout 22 uF / 16 V, MES3.1 C2)'),
    'SW_IMU': dict(lib='Switch:SW_SPDT', value='SS12D10G5', fp='MES4-Carrier-EC:SW-TH_SHOU-HAN_SS12D10G4',
                   lcsc='C7431054', desc='IMU power switch, SHOU HAN SS12D10G5 (as U22 on the MES3.1 carrier); '
                                         '2 = common (+9V), 1 = to the IMU terminal'),
    'U_SCR': dict(lib='MES4-Carrier-EC:URB2405YMD-20WR3', value='URB2405YMD-20WR3',
                  fp='MES4-Carrier-EC:PWRM-TH_YLPTEC_URBXXXXYMD-20WR3', lcsc='C5369777',
                  ds='https://www.lcsc.com/product-detail/C5369777.html',
                  desc='screen supply, YLPTEC URB2405YMD-20WR3: 24 V to 5 V 4 A, 20 W isolated, 1" x 1" DIP'),
    'C_SCR_IN': dict(lib='Device:C_Polarized', value='47uF 100V', fp='Capacitor_SMD:CP_Elec_8x10', lcsc='C48935391',
                     desc='URB2405YMD-20WR3 input capacitor (datasheet Cin 100 uF / 50 V: this 47 uF + the 100 uF aux bulk on +24V_AUX)'),
    'C_SCR_OUT': dict(lib='Device:C', value='22uF 25V', fp='Capacitor_SMD:C_0805_2012Metric', lcsc='C45783',
                      desc='5 V screen output ceramic (with the 100 uF bulk)'),
    'C_SCR_BULK': dict(lib='Device:C_Polarized', value='100uF 16V', fp='Capacitor_SMD:CP_Elec_6.3x5.4', lcsc='C81993',
                       desc='5 V screen output bulk, CX RVT1C101M0605 100 uF 16 V 6.3 x 5.4 mm (datasheet Cout 100 uF / 16 V)'),
    # ---- door servo (FE-URT-2, as on the MES2 Harvester)
    'J_SRVU': dict(lib='Connector:Screw_Terminal_01x04', value='SERVO UART', fp='MES4-Carrier-EC:CONN-TH_KF250NH-3.5-4P',
                   lcsc='C976558', desc='FE-URT-2 UART interface (as CN13 on the MES2 Harvester): 1 GND, 2 +5 V, '
                                        '3 RX (into the module, PA3), 4 TX (from the module, PA2); KF250NH 3.5 mm push-in'),
    # ---- winch direction relays (as U1 / U2 on the MES2_Extension)
    'K_WINCH': dict(lib='MES4-Carrier-EC:IM03GR', value='IM03GR', fp='MES4-Carrier-EC:RELAY-SMD_IMXXGR', lcsc='C2153100',
                    ds='https://www.lcsc.com/product-detail/C2153100.html',
                    desc='winch direction relay, TE IM03GR: 5 V coil 28 mA, DPDT 2 A / 220 VDC (as on the MES2_Extension)'),
}
