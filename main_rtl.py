from rtl_lang.basic import gate_xor, gate_table
from rtl_lang.core import NetList


def main():
    net = NetList()

    a = net.new_wire("a")
    b = net.new_wire("b")
    c = net.new_wire("c")

    # r = gate_xor(net, a, b, c)
    # print(r)

    for i in range(10):
        r = gate_table(net, [0, 1], [a])
        print(r)

    component_cost = {
        "NMos": 0.0062,
        "Resistor": 0.0005,
    }
    net.print(component_cost)

    net.render()


if __name__ == '__main__':
    main()
