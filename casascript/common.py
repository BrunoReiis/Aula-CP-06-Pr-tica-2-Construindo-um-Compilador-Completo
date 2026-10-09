import operator

OPS_ARIT = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
OPS_COMP = {"==": operator.eq, "!=": operator.ne, ">": operator.gt,
            "<": operator.lt, ">=": operator.ge, "<=": operator.le}


def horario_para_minutos(texto):
    """Converte '18:30' em minutos desde a meia-noite."""
    h, m = str(texto).split(":")
    return int(h) * 60 + int(m)


def formatar_horario(minutos):
    """Converte 1110 em '18:30'."""
    return f"{int(minutos) // 60:02d}:{int(minutos) % 60:02d}"


def e_constante(no):
    from .ast_types import Numero, Texto, Logico, Horario
    return isinstance(no, (Numero, Texto, Logico, Horario))
