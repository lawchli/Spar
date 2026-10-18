# Spar PCB — Rev C-M2

![Top](previews/top.png)

Jacks grouped next to the plug. The further the jacks sit from the plug, the more leverage a plugged-in cable has on the plug, so both jacks moved next to it: (6, 6) and (18, 6) mm. The wire pads moved to the right, R1/R2 rotated 180° and the M2 holes moved to (27, 2.7) and (35, 9.5) mm. Circuit, star ground and design rules are unchanged; ERC and DRC clean. 48 × 13.5 × 1.0 mm. Trade-off: the wires from the plug to the pads became longer (about 40–53 mm).

`mechanical-layout.json` records the jack, hole and pad positions shared with the enclosure.

Open `kicad/xz1-direct.kicad_pro`. Symbols and footprints are in `kicad/lib/`.

## Circuit

The board is passive. A 5-pole plug goes into the phone; its poles are counted from the tip:

| Pole | Function | Connection |
|---|---|---|
| 1 | Left headphone | headphone jack tip |
| 2 | Right headphone | headphone jack ring |
| 3 | Left microphone | line-in tip through 10 kΩ, 2.2 kΩ to ground |
| 4 | Ground | both sleeves, star point |
| 5 | Right microphone | line-in ring through 10 kΩ, 2.2 kΩ to ground |

The 2.2 kΩ resistors give each microphone contact the DC load the phone needs to detect a headset microphone; the 10 kΩ series resistors drop line level to microphone level. Every ground branch (both jack sleeves and both 2.2 kΩ resistors) returns separately to the single ground pad of the plug wires, and neither copper layer has a pour. Background: [software/docs/STEREO-CAPTURE.md](../../../blob/software/software/docs/STEREO-CAPTURE.md).

## Fabrication

`fab/` holds the Gerber archive, `BOM.csv` and the placement file `CPL.csv`, prepared for JLCPCB (FR-4, 2 layers, 1.0 mm, 1 oz copper, top-side SMT). Check jack orientation in the manufacturer's placement preview before ordering. This revision was not fabricated.

| Ref | Part | LCSC |
|---|---|---|
| J1, J2 | XKB PJ-327A0-SMT, 3.5 mm TRS socket | C381135 |
| R1, R2 | 10 kΩ 1 %, 0603 | C25804 |
| R3, R4 | 2.2 kΩ 1 %, 0603 | C4190 |

The five plug wires are soldered to pads W1; they are not a connector.

## Rebuilding

The project was generated and checked with KiCad 10 and its bundled Python:

- `build_design.py` generates the schematic, footprints and board. Its 3D-model step needs the jack's EasyEDA model, which is not redistributed here, so the jack has no 3D model in this repository; the board files open and check without it.
- `release.py` runs ERC and DRC and exports the Gerbers, BOM, placement file and renders. Set `KICAD_CLI` and `KICAD_PYTHON` if KiCad is not in its default macOS location.
- `verify_design.py` independently checks the star ground, the resistor paths and the clearances against the exported netlist.

The jack footprint was drawn from the manufacturer's top-view drawing (XKB PJ-327A0-SMT, LCSC C381135). The 0603 resistor footprint and 3D model come from the KiCad library (CC BY-SA 4.0 with the KiCad design exception).

## Files

| Path | Contents |
|---|---|
| `kicad/` | KiCad project and local library |
| `fab/` | Gerbers, BOM, placement |
| `previews/` | KiCad renders, copper views, schematic |
| `reports/` | ERC, DRC, drill report, netlist, independent design audit, release checksums |
| `build_design.py`, `route_signals.py`, `release.py`, `verify_design.py` | Generator, router, release and check scripts |

## Revisions

Each revision replaces the previous one on this branch; earlier ones are kept as tags.

| Tag | Date | Revision |
|---|---|---|
| [`pcb-breadboard`](../../../tree/pcb-breadboard/pcb) | 2026-10-11 | Breadboard / hand-wired build |
| [`pcb-rev-a`](../../../tree/pcb-rev-a/pcb) | 2026-10-13 | Cable splitter board, 35 × 15 mm (KiCad) |
| [`pcb-rev-b`](../../../tree/pcb-rev-b/pcb) | 2026-10-15 | Direct-plug board, 48 × 13.5 mm (KiCad) |
| [`pcb-rev-b-m2`](../../../tree/pcb-rev-b-m2/pcb) | 2026-10-16 | Rev B with two M2 mounting holes (KiCad) |
| [`pcb-rev-c-m2`](../../../tree/pcb-rev-c-m2/pcb) | 2026-10-18 | Jacks grouped next to the plug (KiCad) |
