from dataclasses import dataclass
from typing import List

from synth.logic.builder import LogicBuilder, Bit


# This file is transcribed from or heavily based on https://github.com/olofk/serv
# See serve_licence for the copy of the ISC Licence serv is licenced under.

@dataclass
class ServInterface:
    inputs: List[Bit]
    outputs: List[Bit]


def build_cpu_serv(build: LogicBuilder) -> ServInterface:
    i_en = build.new_bit("i_en")
    i_cnt0 = build.new_bit("i_cnt0")
    o_cmp = build.new_bit("o_cmp")
    i_sub = build.new_bit("i_sub")
    i_bool_op = (build.new_bit("i_bool_op0"), build.new_bit("i_bool_op1"))
    i_cmp_eq = build.new_bit("i_cmp_eq")
    i_cmp_sig = build.new_bit("i_cmp_sig")
    i_rd_sel = (build.new_bit("i_rd_sel0"), build.new_bit("i_rd_sel1"), build.new_bit("i_rd_sel2"))
    i_rs1 = build.new_bit("i_rs1")
    i_op_b = build.new_bit("i_op_b")
    i_buf = build.new_bit("i_buf")
    o_rd = build.new_bit("o_rd")

    build_alu(build, i_en, i_cnt0, o_cmp, i_sub, i_bool_op, i_cmp_eq, i_cmp_sig, i_rd_sel, i_rs1, i_op_b, i_buf, o_rd)

    return ServInterface(
        inputs=[i_en, i_cnt0, i_sub, i_bool_op[0], i_bool_op[1], i_cmp_eq, i_cmp_sig, i_rd_sel[0], i_rd_sel[1],
                i_rd_sel[2], i_rs1, i_op_b, i_buf],
        outputs=[o_cmp, o_rd]
    )


# Transcribed from https://github.com/olofk/serv/blob/main/rtl/serv_alu.v
# Hardcoded W=1 => B=0
def build_alu(
        build: LogicBuilder,

        # State
        i_en: Bit,
        i_cnt0: Bit,
        o_cmp: Bit,
        # Control,
        i_sub: Bit,
        i_bool_op: (Bit, Bit),
        i_cmp_eq: Bit,
        i_cmp_sig: Bit,
        i_rd_sel: (Bit, Bit, Bit),
        # Data,
        i_rs1: Bit,
        i_op_b: Bit,
        i_buf: Bit,
        o_rd: Bit,
):
    result_add = build.new_bit("result_add")
    result_slt = build.new_bit("result_slt")
    cmp_r = build.new_bit("cmp_r")
    add_cy = build.new_bit("add_cy")
    add_cy_r = build.new_bit("add_cy_r")

    # Sign-extended operands
    rs1_sx = i_rs1 & i_cmp_sig
    op_b_sx = i_op_b & i_cmp_sig

    add_b = i_op_b ^ i_sub

    add_cy_connect, result_add_connect = Bit.full_add(i_rs1, add_b, add_cy_r)
    add_cy %= add_cy_connect
    result_add %= result_add_connect

    _, result_lt = Bit.full_add(rs1_sx, ~op_b_sx, add_cy)
    result_eq = ~(result_add & (cmp_r | i_cnt0))

    o_cmp %= i_cmp_eq.mux(result_lt, result_eq)

    result_bool = ((i_rs1 ^ i_op_b) & ~i_bool_op[0]) | (i_bool_op[1] & i_op_b & i_rs1)
    result_slt %= cmp_r & i_cnt0

    o_rd %= i_buf | (i_rd_sel[0] & result_add) | (i_rd_sel[1] & result_slt) | (i_rd_sel[2] & result_bool)

    add_cy_r %= i_en.mux(i_sub, add_cy).delay()
    cmp_r %= i_en.mux(cmp_r, o_cmp)
