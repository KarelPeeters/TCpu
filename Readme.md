## Part selection

* NMOS:
    * SI2302: €0.0062, SOT-23, https://jlcpcb.com/partdetail/Jsmsemi-SI2302/C5296725
    * JSM2301S: €0.0063, SOT-23, https://jlcpcb.com/partdetail/Jsmsemi-JSM2301S/C916399
    * 2N7002: €0.0074, SOT-23, https://jlcpcb.com/partdetail/Jsmsemi-2N7002/C916396
    * smaller packages: (sadly more expensive?)
      * SOT-323 == SC-70, SOT-563
      * VML0806 (€0.0556)
      * DFN0603
* Resistor: 1k(?), footprint 0402 (smallest)
    * €0.0005, https://jlcpcb.com/parts/basic_parts
* LED
* RAM chip
* Regfile chip?
* Clocking stuff

# PCB Capabilities

https://jlcpcb.com/capabilities/Capabilities
* minimum via size?
  * hole: 0.15mm, diameter: 0.25mm
* minimum trace size?
  * width: 0.09mm, spacing: 0.09mm
  * do we ever need to care about the resistance?
* parasitic capacitance in wires, transistors, resistors, ...
  
* Figure out t_hold and t_setup!
  * analog SPICE simulation?

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


Place & Route algorithms:

* Intro placement in Rust: https://stefanabikaram.com/writing/fpga-sa-placer/
* Manhattan spanning tree: https://www.topcoder.com/thrive/articles/Line%20Sweep%20Algorithms

# Final processor design

* 8/16/32 bit?
* RISCV? Something else? Something custom?
* RAM/ROM embedded or via pins?
* clock generation on-board?
* VGA out? audio out?
* GPIO pins?
* Leds?
