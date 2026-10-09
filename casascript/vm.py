from dataclasses import dataclass, field

from .ast_types import Acao, Aritmetica, Comparacao, Logica, Logico, Nao, Numero, Programa, Regra, Texto, Variavel, Horario
from .common import OPS_ARIT, OPS_COMP, formatar_horario, horario_para_minutos
from .semantics import ACOES

ESTADO_INICIAL = {
    "relogio": horario_para_minutos("06:00"),
    "peso_pote": 150,
    "nivel_agua": 70,
    "temperatura": 25,
    "movimento": False,
    "comportamento": "calmo",
}


@dataclass
class RegraCompilada:
    numero: int
    fonte: str
    condicao: list
    acoes: list
    acoes_senao: list = field(default_factory=list)


class GeradorDeCodigo:
    def __init__(self):
        self.codigo = []

    def emitir(self, op, arg=None):
        self.codigo.append([op, arg])
        return len(self.codigo) - 1

    def gerar_expr(self, no):
        if isinstance(no, (Numero, Horario, Texto, Logico)):
            self.emitir("PUSH_CONST", no.valor)
        elif isinstance(no, Variavel):
            self.emitir("LOAD_SENSOR", no.nome)
        elif isinstance(no, Aritmetica):
            self.gerar_expr(no.esq)
            self.gerar_expr(no.dir)
            self.emitir("BIN_OP", no.op)
        elif isinstance(no, Comparacao):
            self.gerar_expr(no.esq)
            self.gerar_expr(no.dir)
            self.emitir("COMPARE", no.op)
        elif isinstance(no, Nao):
            self.gerar_expr(no.expr)
            self.emitir("NOT")
        elif isinstance(no, Logica):
            self.gerar_expr(no.esq)
            salto = self.emitir("JUMP_IF_FALSE_OR_POP" if no.op == "E" else "JUMP_IF_TRUE_OR_POP", "?")
            self.gerar_expr(no.dir)
            self.codigo[salto][1] = len(self.codigo)

    def gerar_condicao(self, expr):
        self.codigo = []
        self.gerar_expr(expr)
        self.emitir("RETURN")
        return self.codigo

    def gerar_acoes(self, acoes):
        self.codigo = []
        for acao in acoes:
            params = ACOES[acao.nome][0]
            for param, arg in zip(params, acao.args):
                if param == "dispositivo":
                    self.emitir("LOAD_DEVICE", arg.nome)
                else:
                    self.gerar_expr(arg)
            self.emitir("CALL_ACTION", (acao.nome, len(acao.args)))
        self.emitir("HALT")
        return self.codigo

    def gerar(self, programa):
        return [RegraCompilada(r.numero, r.fonte,
                               self.gerar_condicao(r.condicao),
                               self.gerar_acoes(r.acoes),
                               self.gerar_acoes(r.acoes_senao) if r.acoes_senao else [])
                for r in programa.regras]


def desmontar(codigo, titulo=""):
    linhas = [titulo] if titulo else []
    for endereco, (op, arg) in enumerate(codigo):
        if arg is None:
            txt = ""
        elif op == "CALL_ACTION":
            txt = f"{arg[0]} (args={arg[1]})"
        elif op.startswith("JUMP"):
            txt = f"-> {arg}"
        elif op in ("BIN_OP", "COMPARE"):
            txt = arg
        else:
            txt = repr(arg)
        linhas.append(f"  {endereco:>3}  {op:<22}{txt}")
    return "\n".join(linhas)


def mostrar_regra_compilada(r):
    print(f"══════ Regra #{r.numero} ══════")
    print(desmontar(r.condicao, "  [condição]"))
    print(desmontar(r.acoes, "  [ações do ENTAO]"))
    if r.acoes_senao:
        print(desmontar(r.acoes_senao, "  [ações do SENAO]"))
    else:
        print("  [ações do SENAO]  (sem SENAO)")
    print()


class CasaPet:
    def __init__(self):
        self.sensores = dict(ESTADO_INICIAL)
        self.dispositivos = {
            "comedouro": {"porcoes": 0, "total_g": 0},
            "fonte": {"ligado": False, "nivel": 40},
            "camera": {"ligado": False, "gravando": False},
            "climatizador": {"ligado": False, "nivel": 24},
        }
        self.log = []

    def executar_acao(self, nome, args):
        carimbo = f"[{formatar_horario(self.sensores['relogio'])}]"
        if nome == "notificar":
            self.log.append(f"{carimbo} 📱 NOTIFICAÇÃO: {args[0]}")
            return
        alvo = self.dispositivos[args[0]]
        if nome == "ligar":
            alvo["ligado"] = True
        elif nome == "desligar":
            alvo["ligado"] = False
            if "gravando" in alvo:
                alvo["gravando"] = False
        elif nome == "ajustar":
            alvo.update(ligado=True, nivel=args[1])
        elif nome == "servir":
            alvo["porcoes"] += 1
            alvo["total_g"] += args[1]
        elif nome == "encher":
            alvo["nivel"] = args[1]
        elif nome == "gravar":
            alvo.update(ligado=True, gravando=True)
        extra = f" -> {args[1]}" if len(args) > 1 else ""
        self.log.append(f"{carimbo} ⚡ {nome}({args[0]}){extra}")


class MaquinaVirtual:
    def __init__(self, casa):
        self.casa = casa

    def executar(self, codigo, rastrear=False):
        pilha, pc, rastro = [], 0, []
        while True:
            op, arg = codigo[pc]
            endereco = pc
            pc += 1

            if op == "PUSH_CONST":
                pilha.append(arg)
            elif op == "LOAD_SENSOR":
                pilha.append(self.casa.sensores[arg])
            elif op == "LOAD_DEVICE":
                pilha.append(arg)
            elif op == "BIN_OP":
                b, a = pilha.pop(), pilha.pop()
                pilha.append(OPS_ARIT[arg](a, b))
            elif op == "COMPARE":
                b, a = pilha.pop(), pilha.pop()
                pilha.append(OPS_COMP[arg](a, b))
            elif op == "NOT":
                pilha.append(not pilha.pop())
            elif op == "JUMP_IF_FALSE_OR_POP":
                if not pilha[-1]:
                    pc = arg
                else:
                    pilha.pop()
            elif op == "JUMP_IF_TRUE_OR_POP":
                if pilha[-1]:
                    pc = arg
                else:
                    pilha.pop()
            elif op == "CALL_ACTION":
                nome, n = arg
                args = pilha[-n:]
                del pilha[-n:]
                self.casa.executar_acao(nome, args)
            elif op == "RETURN":
                if rastrear:
                    rastro.append((endereco, op, "", list(pilha)))
                return pilha.pop(), rastro
            elif op == "HALT":
                if rastrear:
                    rastro.append((endereco, op, "", list(pilha)))
                return None, rastro
            else:
                raise RuntimeError(f"Instrução desconhecida: {op}")

            if rastrear:
                rastro.append((endereco, op, "" if arg is None else arg, list(pilha)))


class CentralDeAutomacao:
    def __init__(self, bytecode, casa):
        self.regras = bytecode
        self.casa = casa
        self.vm = MaquinaVirtual(casa)
        self.estado_anterior = {r.numero: False for r in bytecode}

    def avaliar_todas(self):
        disparos = []
        for regra in self.regras:
            agora, _ = self.vm.executar(regra.condicao)
            antes = self.estado_anterior[regra.numero]
            if agora and not antes:
                self.vm.executar(regra.acoes)
                disparos.append((regra.numero, "ENTAO"))
            elif antes and not agora and regra.acoes_senao:
                self.vm.executar(regra.acoes_senao)
                disparos.append((regra.numero, "SENAO"))
            self.estado_anterior[regra.numero] = agora
        return disparos

    def evento(self, sensor, valor):
        self.casa.sensores[sensor] = valor
        return self.avaliar_todas()
