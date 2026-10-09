import difflib

from .ast_types import Aritmetica, Comparacao, Logica, Nao, Numero, Texto, Logico, Variavel, Acao
from .common import OPS_ARIT, OPS_COMP
from .ast_types import mostrar, mostrar_acao

SENSORES = {
    "relogio": "horario",
    "peso_pote": "numero",
    "nivel_agua": "numero",
    "temperatura": "numero",
    "movimento": "logico",
    "comportamento": "texto",
}

FAIXA_SENSOR = {"peso_pote": (0, 500), "nivel_agua": (0, 100), "temperatura": (-10, 50)}
VALORES_TEXTO = {"comportamento": {"calmo", "agitado", "dormindo", "comendo"}}

DISPOSITIVOS = {
    "comedouro": "comedouro_automatico",
    "fonte": "fonte_agua",
    "camera": "camera",
    "climatizador": "climatizador",
}

ACOES = {
    "ligar": (["dispositivo"], {"fonte_agua", "camera", "climatizador"}),
    "desligar": (["dispositivo"], {"fonte_agua", "camera", "climatizador"}),
    "ajustar": (["dispositivo", "numero"], {"climatizador"}),
    "servir": (["dispositivo", "numero"], {"comedouro_automatico"}),
    "encher": (["dispositivo", "numero"], {"fonte_agua"}),
    "gravar": (["dispositivo"], {"camera"}),
    "notificar": (["texto"], set()),
}

FAIXA_ACAO = {"ajustar": (16, 30), "servir": (10, 200), "encher": (1, 100)}


class AnalisadorSemantico:
    def __init__(self):
        self.erros, self.avisos = [], []
        self.condicoes_vistas = {}

    def erro(self, no, msg):
        self.erros.append(f"❌ Linha {no.linha}, col {no.coluna}: {msg}")

    def aviso(self, no, msg):
        self.avisos.append(f"⚠️ Linha {no.linha}, col {no.coluna}: {msg}")

    def sugestao(self, nome, conhecidos):
        parecido = difflib.get_close_matches(nome, conhecidos, n=1)
        return f" Você quis dizer '{parecido[0]}'?" if parecido else ""

    def valor_constante(self, no):
        if isinstance(no, Numero):
            return no.valor
        if isinstance(no, Aritmetica):
            e, d = self.valor_constante(no.esq), self.valor_constante(no.dir)
            if no.op == "*" and (e == 0 or d == 0):
                return 0
            if e is None or d is None:
                return None
            if no.op == "/" and d == 0:
                return None
            return OPS_ARIT[no.op](e, d)
        return None

    def tipo(self, no):
        from .ast_types import Horario, Numero, Texto, Logico, Variavel

        if isinstance(no, Numero):
            return "numero"
        if isinstance(no, Horario):
            return "horario"
        if isinstance(no, Texto):
            return "texto"
        if isinstance(no, Logico):
            return "logico"

        if isinstance(no, Variavel):
            if no.nome in SENSORES:
                return SENSORES[no.nome]
            if no.nome in DISPOSITIVOS:
                self.erro(no, f"'{no.nome}' é um DISPOSITIVO, não um sensor. Dispositivos não têm valor para comparar.")
            else:
                self.erro(no, f"sensor '{no.nome}' não existe." + self.sugestao(no.nome, SENSORES))
            return "erro"

        if isinstance(no, Aritmetica):
            te, td = self.tipo(no.esq), self.tipo(no.dir)
            if "erro" in (te, td):
                return "erro"
            if te != "numero" or td != "numero":
                self.erro(no, f"a conta '{no.op}' só funciona com números (recebeu {te} {no.op} {td}).")
                return "erro"
            if no.op == "/" and self.valor_constante(no.dir) == 0:
                self.erro(no, "divisão por zero!")
                return "erro"
            return "numero"

        if isinstance(no, Comparacao):
            te, td = self.tipo(no.esq), self.tipo(no.dir)
            if "erro" in (te, td):
                return "erro"
            if te != td:
                self.erro(no, f"não dá para comparar {te} com {td} usando '{no.op}'.")
                return "erro"
            if te in ("texto", "logico") and no.op not in ("==", "!="):
                self.erro(no, f"'{no.op}' não faz sentido para {te}. Use apenas == ou !=.")
                return "erro"
            self.verificar_valores(no)
            return "logico"

        if isinstance(no, Logica):
            te, td = self.tipo(no.esq), self.tipo(no.dir)
            if "erro" in (te, td):
                return "erro"
            if te != "logico" or td != "logico":
                self.erro(no, f"'{no.op}' liga duas condições VERDADEIRO/FALSO (recebeu {te} {no.op} {td}).")
                return "erro"
            return "logico"

        if isinstance(no, Nao):
            t = self.tipo(no.expr)
            if t not in ("logico", "erro"):
                self.erro(no, f"NAO só pode negar uma condição (recebeu {t}).")
                return "erro"
            return t

        return "erro"

    def verificar_valores(self, comp):
        var, const = comp.esq, comp.dir
        if not isinstance(var, Variavel):
            var, const = comp.dir, comp.esq
        if not isinstance(var, Variavel):
            return
        if isinstance(const, Numero) and var.nome in FAIXA_SENSOR:
            minimo, maximo = FAIXA_SENSOR[var.nome]
            if not (minimo <= const.valor <= maximo):
                self.aviso(comp, f"'{var.nome}' vai de {minimo} a {maximo}; o valor {const.valor} está fora da faixa.")
        if isinstance(const, Texto) and var.nome in VALORES_TEXTO:
            validos = VALORES_TEXTO[var.nome]
            if const.valor not in validos:
                self.aviso(comp, f"'{var.nome}' nunca vale \"{const.valor}\" (valores possíveis: {sorted(validos)})."
                                 + self.sugestao(const.valor, validos))

    def verificar_acao(self, acao):
        if acao.nome not in ACOES:
            self.erro(acao, f"ação '{acao.nome}' não existe." + self.sugestao(acao.nome, ACOES))
            return
        params, aceita = ACOES[acao.nome]
        if len(acao.args) != len(params):
            self.erro(acao, f"'{acao.nome}' espera {len(params)} argumento(s), mas recebeu {len(acao.args)}.")
            return
        for param, arg in zip(params, acao.args):
            if param == "dispositivo":
                if not isinstance(arg, Variavel) or arg.nome not in DISPOSITIVOS:
                    nome = arg.nome if isinstance(arg, Variavel) else "?"
                    self.erro(arg, f"'{acao.nome}' precisa de um dispositivo; '{nome}' não é um."
                                   + (self.sugestao(nome, DISPOSITIVOS) if nome != "?" else ""))
                    return
                tipo_disp = DISPOSITIVOS[arg.nome]
                if tipo_disp not in aceita:
                    self.erro(acao, f"não é possível '{acao.nome}' um(a) {tipo_disp} ('{arg.nome}').")
                    return
            else:
                t = self.tipo(arg)
                if t != "erro" and t != param:
                    self.erro(arg, f"'{acao.nome}' esperava {param}, mas recebeu {t}.")
        if acao.nome in FAIXA_ACAO and len(acao.args) == 2:
            valor = self.valor_constante(acao.args[1])
            minimo, maximo = FAIXA_ACAO[acao.nome]
            if valor is not None and not (minimo <= valor <= maximo):
                self.erro(acao.args[1], f"'{acao.nome}' em '{acao.args[0].nome}' aceita valores de {minimo} a {maximo}.")

    def analisar(self, programa):
        for regra in programa.regras:
            t = self.tipo(regra.condicao)
            if t not in ("logico", "erro"):
                self.erro(regra.condicao, f"a condição da Regra #{regra.numero} precisa ser VERDADEIRO/FALSO, mas é {t}.")

            chave = mostrar(regra.condicao)
            if chave in self.condicoes_vistas:
                self.aviso(regra, f"a Regra #{regra.numero} tem exatamente a mesma condição da Regra #{self.condicoes_vistas[chave]}: {chave}")
            else:
                self.condicoes_vistas[chave] = regra.numero

            vistas = {}
            for bloco, acoes in (("ENTAO", regra.acoes), ("SENAO", regra.acoes_senao)):
                usados = {}
                for acao in acoes:
                    self.verificar_acao(acao)
                    texto = mostrar_acao(acao)
                    if texto in vistas:
                        onde = "no mesmo bloco" if vistas[texto] == bloco else f"também no bloco {vistas[texto]}"
                        self.aviso(acao, f"a ação {texto} está repetida na Regra #{regra.numero} ({bloco}; aparece {onde}).")
                    else:
                        vistas[texto] = bloco

                    if acao.nome in ("ligar", "desligar") and acao.args and isinstance(acao.args[0], Variavel):
                        usados.setdefault(acao.args[0].nome, set()).add(acao.nome)
                for disp, nomes in usados.items():
                    if len(nomes) == 2:
                        self.aviso(regra, f"a Regra #{regra.numero} liga E desliga '{disp}' ao mesmo tempo (bloco {bloco}).")
        return self.erros, self.avisos
