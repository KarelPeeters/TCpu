from kiutils.schematic import Schematic

path = r"C:\Documents\Hardware\Digitale meter\PCBDesign\project\TCpu\TCpu.kicad_sch"

schematic = Schematic.from_file(path)

print(schematic)

schematic.to_file("test.sch")
