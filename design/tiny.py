from synth.logic.builder import LogicBuilder, Unsigned


def build_counter(build: LogicBuilder, bits: int) -> Unsigned:
    curr = build.new_unsigned(bits, "curr")
    curr %= curr.add_trunc(1).delay()
    return curr
