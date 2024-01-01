## Part selection

* NMOS:
    * SI2302: €0.0062, SOT-23, https://jlcpcb.com/partdetail/Jsmsemi-SI2302/C5296725
    * JSM2301S: €0.0063, SOT-23, https://jlcpcb.com/partdetail/Jsmsemi-JSM2301S/C916399
    * 2N7002: €0.0074, SOT-23, https://jlcpcb.com/partdetail/Jsmsemi-2N7002/C916396
* Resistor: 1k(?), footprint 0402 (smallest)
    * €0.0005, https://jlcpcb.com/parts/basic_parts
* LED
* RAM chip
* Regfile chip?
* Clocking stuff

# PCB cost estimate:

JLCPCB board cost:
400x100mm => 18.37
400x400mm => 73.46
300x200mm => 27.59
cost per mm2: 0.000459

SOT-23 size: 3.4x3.84 = 13.1 mm2
extra cost per SOT-23: 0.006

0402 size: 1.86x0.94 = 1.75 mm2
extra cost per 0402: 0.0008

Conclusion: board space costs the same as the component, double the price of everything (and some margin for routing space)

## Resources

Kicad file format:

* https://dev-docs.kicad.org/en/file-formats/
* https://github.com/mvnmgrx/kiutils

Other similar kicad interactions:

* https://github.com/devbisme/skidl/blob/master/src/skidl/schematics/place.py
* https://github.com/devbisme/skidl/blob/master/src/skidl/schematics/route.py
* https://jeffmcbride.net/programmatic-layout-with-kicad-and-python/
* https://jeffmcbride.net/kicad-component-layout
* https://github.com/inventree/InvenTree

