from lark import Lark, Transformer, v_args

from .ast_types import (
    Acao,
    Aritmetica,
    Comparacao,
    Logica,
    Nao,
    Numero,
    Programa,
    Regra,
    Texto,
    Variavel,
    Logico,
    Horario,
)
from .common import horario_para_minutos

GRAMATICA = r'''
programa   : regra+

regra      : "QUANDO" expr "ENTAO" acoes ["SENAO" acoes] "FIM"

acoes      : acao (";" acao)* ";"?
acao       : NOME "(" [argumentos] ")"
argumentos : expr ("," expr)*

?expr       : ou
?ou         : e          | ou "OU" e             -> op_ou
?e          : nao        | e "E" nao             -> op_e
?nao        : comparacao | "NAO" nao             -> op_nao
?comparacao : soma       | soma OP_COMP soma     -> op_comp
?soma       : produto    | soma OP_SOMA produto  -> op_arit
?produto    : atomo      | produto OP_MULT atomo -> op_arit
?atomo      : HORARIO        -> horario
            | NUMERO         -> numero
            | TEXTO          -> texto
            | "VERDADEIRO"   -> verdadeiro
            | "FALSO"        -> falso
            | NOME           -> variavel
            | "(" expr ")"

OP_COMP    : "==" | "!=" | ">=" | "<=" | ">" | "<"
OP_SOMA    : "+" | "-"
OP_MULT    : "*" | "/"
HORARIO.2  : /(?:[01]\d|2[0-3]):[0-5]\d(?!\d)/
NUMERO     : /\d+(\.\d+)?/
TEXTO      : /"[^"\n]*"/
NOME       : /[a-z_][a-z0-9_]*/
COMENTARIO : /#[^\n]*/

%import common.WS
%ignore WS
%ignore COMENTARIO
'''

parser = Lark(GRAMATICA, start="programa", parser="lalr", propagate_positions=True, maybe_placeholders=True)


def analisar_lexico(fonte):
    return list(parser.lex(fonte))


@v_args(meta=True)
class ConstrutorAST(Transformer):
    def __init__(self, fonte):
        super().__init__()
        self.fonte = fonte

    def numero(self, meta, f):
        t = f[0]
        return Numero(float(t) if "." in t else int(t), meta.line, meta.column)

    def horario(self, meta, f):
        return Horario(horario_para_minutos(f[0]), meta.line, meta.column)

    def texto(self, meta, f):
        return Texto(f[0][1:-1], meta.line, meta.column)

    def verdadeiro(self, meta, f):
        return Logico(True, meta.line, meta.column)

    def falso(self, meta, f):
        return Logico(False, meta.line, meta.column)

    def variavel(self, meta, f):
        return Variavel(str(f[0]), meta.line, meta.column)

    def op_arit(self, meta, f):
        return Aritmetica(str(f[1]), f[0], f[2], meta.line, meta.column)

    def op_comp(self, meta, f):
        return Comparacao(str(f[1]), f[0], f[2], meta.line, meta.column)

    def op_e(self, meta, f):
        return Logica("E", f[0], f[1], meta.line, meta.column)

    def op_ou(self, meta, f):
        return Logica("OU", f[0], f[1], meta.line, meta.column)

    def op_nao(self, meta, f):
        return Nao(f[0], meta.line, meta.column)

    def argumentos(self, meta, f):
        return list(f)

    def acao(self, meta, f):
        return Acao(str(f[0]), f[1] or [], meta.line, meta.column)

    def acoes(self, meta, f):
        return list(f)

    def regra(self, meta, f):
        trecho = self.fonte[meta.start_pos:meta.end_pos]
        senao = f[2] if len(f) > 2 and f[2] else []
        return Regra(0, f[0], f[1], trecho, meta.line, meta.column, senao)

    def programa(self, meta, f):
        for i, r in enumerate(f, 1):
            r.numero = i
        return Programa(list(f))


def construir_ast(fonte):
    return ConstrutorAST(fonte).transform(parser.parse(fonte))
