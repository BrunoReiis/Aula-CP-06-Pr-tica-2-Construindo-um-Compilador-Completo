from dataclasses import dataclass, field


@dataclass
class Numero:
    valor: float
    linha: int = 0
    coluna: int = 0


@dataclass
class Horario:
    valor: int
    linha: int = 0
    coluna: int = 0


@dataclass
class Texto:
    valor: str
    linha: int = 0
    coluna: int = 0


@dataclass
class Logico:
    valor: bool
    linha: int = 0
    coluna: int = 0


@dataclass
class Variavel:
    nome: str
    linha: int = 0
    coluna: int = 0


@dataclass
class Aritmetica:
    op: str
    esq: object
    dir: object
    linha: int = 0
    coluna: int = 0


@dataclass
class Comparacao:
    op: str
    esq: object
    dir: object
    linha: int = 0
    coluna: int = 0


@dataclass
class Logica:
    op: str
    esq: object
    dir: object
    linha: int = 0
    coluna: int = 0


@dataclass
class Nao:
    expr: object
    linha: int = 0
    coluna: int = 0


@dataclass
class Acao:
    nome: str
    args: list
    linha: int = 0
    coluna: int = 0


@dataclass
class Regra:
    numero: int
    condicao: object
    acoes: list
    fonte: str = ""
    linha: int = 0
    coluna: int = 0
    acoes_senao: list = field(default_factory=list)


@dataclass
class Programa:
    regras: list


def mostrar(no):
    """Converte uma expressão AST de volta para texto."""
    if isinstance(no, Numero):
        return str(no.valor)
    if isinstance(no, Horario):
        from .common import formatar_horario
        return formatar_horario(no.valor)
    if isinstance(no, Texto):
        return f'"{no.valor}"'
    if isinstance(no, Logico):
        return "VERDADEIRO" if no.valor else "FALSO"
    if isinstance(no, Variavel):
        return no.nome
    if isinstance(no, Nao):
        return f"NAO {mostrar(no.expr)}"
    return f"({mostrar(no.esq)} {no.op} {mostrar(no.dir)})"


def mostrar_acao(acao):
    return f"{acao.nome}({', '.join(mostrar(a) for a in acao.args)})"


def rotulo(no):
    from .common import formatar_horario
    if isinstance(no, Programa):
        return "📦 Programa"
    if isinstance(no, Regra):
        return f"📏 Regra #{no.numero}"
    if isinstance(no, Numero):
        return f"🔢 Numero {no.valor}"
    if isinstance(no, Horario):
        return f"🕒 Horario {formatar_horario(no.valor)} ({no.valor} min)"
    if isinstance(no, Texto):
        return f'🔤 Texto "{no.valor}"'
    if isinstance(no, Logico):
        return f"⚪ Logico {'VERDADEIRO' if no.valor else 'FALSO'}"
    if isinstance(no, Variavel):
        return f"🏷️ Variavel {no.nome}"
    if isinstance(no, Aritmetica):
        return f"➕ Aritmetica ({no.op})"
    if isinstance(no, Comparacao):
        return f"⚖️ Comparacao ({no.op})"
    if isinstance(no, Logica):
        return f"🔗 Logica ({no.op})"
    if isinstance(no, Nao):
        return "🚫 Nao"
    if isinstance(no, Acao):
        return f"⚡ Acao {no.nome}()"
    return str(no)


def filhos(no):
    if isinstance(no, Programa):
        return [("", r) for r in no.regras]
    if isinstance(no, Regra):
        return ([("SE: ", no.condicao)] + [("FAÇA: ", a) for a in no.acoes] + [("SENÃO: ", a) for a in no.acoes_senao])
    if isinstance(no, (Aritmetica, Comparacao, Logica)):
        return [("", no.esq), ("", no.dir)]
    if isinstance(no, Nao):
        return [("", no.expr)]
    if isinstance(no, Acao):
        return [("", a) for a in no.args]
    return []


def desenhar_ast(no, prefixo="", ultimo=True, raiz=True, etiqueta=""):
    conector = "" if raiz else ("└── " if ultimo else "├── ")
    linhas = [prefixo + conector + etiqueta + rotulo(no)]
    novo_prefixo = prefixo + ("" if raiz else ("    " if ultimo else "│   "))
    lista = filhos(no)
    for i, (et, filho) in enumerate(lista):
        linhas.append(desenhar_ast(filho, novo_prefixo, i == len(lista) - 1, False, et))
    return "\n".join(linhas)
