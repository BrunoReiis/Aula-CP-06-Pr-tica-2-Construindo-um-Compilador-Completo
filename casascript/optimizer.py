from .ast_types import Acao, Aritmetica, Comparacao, Logica, Logico, Nao, Numero
from .common import OPS_ARIT, OPS_COMP, e_constante
from .semantics import ACOES


class Otimizador:
    def __init__(self):
        self.relatorio = []

    def registrar(self, tecnica, antes, depois):
        from .ast_types import mostrar
        self.relatorio.append((tecnica, mostrar(antes), mostrar(depois)))

    def otimizar_base(self, no):
        if isinstance(no, (Aritmetica, Comparacao, Logica)):
            no = type(no)(no.op, self.otimizar_expr(no.esq), self.otimizar_expr(no.dir), no.linha, no.coluna)
        elif isinstance(no, Nao):
            no = Nao(self.otimizar_expr(no.expr), no.linha, no.coluna)

        if isinstance(no, Aritmetica) and e_constante(no.esq) and e_constante(no.dir):
            if not (no.op == "/" and no.dir.valor == 0):
                valor = OPS_ARIT[no.op](no.esq.valor, no.dir.valor)
                if isinstance(valor, float) and valor.is_integer():
                    valor = int(valor)
                novo = Numero(valor, no.linha, no.coluna)
                self.registrar("Constant folding", no, novo)
                return novo
        if isinstance(no, Comparacao) and e_constante(no.esq) and e_constante(no.dir):
            novo = Logico(OPS_COMP[no.op](no.esq.valor, no.dir.valor), no.linha, no.coluna)
            self.registrar("Constant folding", no, novo)
            return novo
        if isinstance(no, Nao) and isinstance(no.expr, Logico):
            novo = Logico(not no.expr.valor, no.linha, no.coluna)
            self.registrar("Constant folding", no, novo)
            return novo

        if isinstance(no, Logica):
            for const, outro in ((no.esq, no.dir), (no.dir, no.esq)):
                if isinstance(const, Logico):
                    if no.op == "E":
                        novo = outro if const.valor else Logico(False, no.linha, no.coluna)
                    else:
                        novo = Logico(True, no.linha, no.coluna) if const.valor else outro
                    self.registrar("Simplificação lógica", no, novo)
                    return novo
        return no

    def dupla_negacao(self, no):
        if isinstance(no, Nao) and isinstance(no.expr, Nao):
            novo = no.expr.expr
            self.registrar("Dupla negação", no, novo)
            return novo
        return no

    def identidade_aritmetica(self, no):
        if not isinstance(no, Aritmetica):
            return no
        e, d = no.esq, no.dir
        eh = lambda n, v: isinstance(n, Numero) and n.valor == v
        novo = None
        if no.op == "+" and eh(d, 0):
            novo = e
        elif no.op == "+" and eh(e, 0):
            novo = d
        elif no.op == "-" and eh(d, 0):
            novo = e
        elif no.op == "*" and eh(d, 1):
            novo = e
        elif no.op == "*" and eh(e, 1):
            novo = d
        elif no.op == "/" and eh(d, 1):
            novo = e
        elif no.op == "*" and (eh(d, 0) or eh(e, 0)):
            novo = Numero(0, no.linha, no.coluna)
        if novo is not None:
            self.registrar("Identidade aritmética", no, novo)
            return novo
        return no

    def otimizar_expr(self, no):
        no = self.otimizar_base(no)
        no = self.dupla_negacao(no)
        no = self.identidade_aritmetica(no)
        return no

    def otimizar_acoes(self, acoes):
        return [Acao(a.nome, [self.otimizar_expr(arg) for arg in a.args], a.linha, a.coluna) for a in acoes]

    def otimizar(self, programa):
        regras = []
        for r in programa.regras:
            cond = self.otimizar_expr(r.condicao)
            if isinstance(cond, Logico) and not cond.valor:
                self.relatorio.append(("Código morto", f"Regra #{r.numero}", "removida (nunca dispara)"))
                continue
            regras.append(type(r)(r.numero, cond, self.otimizar_acoes(r.acoes), r.fonte, r.linha, r.coluna,
                                  self.otimizar_acoes(r.acoes_senao)))
        from .ast_types import Programa
        return Programa(regras)
