from dataclasses import dataclass, field

from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedToken

from .ast_types import Programa, Regra, desenhar_ast, mostrar
from .lexer_parser import ConstrutorAST, analisar_lexico, parser, construir_ast
from .semantics import AnalisadorSemantico, ACOES
from .optimizer import Otimizador
from .vm import CasaPet, CentralDeAutomacao, GeradorDeCodigo, MaquinaVirtual, mostrar_regra_compilada
from .common import formatar_horario, horario_para_minutos

PROGRAMA_EXEMPLO = '''
QUANDO relogio >= 07:30 E peso_pote < 20 ENTAO
    servir(comedouro, 60);
    notificar("Pote vazio: servindo ração!")
SENAO
    notificar("Pote abastecido. Bom apetite!")
FIM

QUANDO nivel_agua < 25 ENTAO
    ligar(fonte);
    encher(fonte, 80)
SENAO
    desligar(fonte)
FIM

QUANDO temperatura > 26 + 2 E movimento ENTAO
    ajustar(climatizador, 22)
SENAO
    desligar(climatizador)
FIM

QUANDO comportamento == "agitado" ENTAO
    gravar(camera);
    notificar("Seu pet está agitado!")
SENAO
    desligar(camera)
FIM
'''

NOMES_AMIGAVEIS = {
    "QUANDO": "QUANDO", "ENTAO": "ENTAO", "SENAO": "SENAO", "FIM": "FIM", "E": "E", "OU": "OU", "NAO": "NAO",
    "LPAR": "(", "RPAR": ")", "SEMICOLON": ";", "COMMA": ",", "NOME": "um nome",
    "NUMERO": "um número", "HORARIO": "um horário HH:MM", "TEXTO": "um texto entre aspas",
    "OP_COMP": "um comparador (==, >, ...)", "OP_SOMA": "+ ou -", "OP_MULT": "* ou /",
    "VERDADEIRO": "VERDADEIRO", "FALSO": "FALSO", "$END": "fim do programa",
}


@dataclass
class ResultadoCompilacao:
    ok: bool = False
    fase_erro: str = None
    mensagens: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    tokens: list = field(default_factory=list)
    arvore: object = None
    ast: object = None
    ast_otimizada: object = None
    relatorio_otimizacao: list = field(default_factory=list)
    bytecode: list = field(default_factory=list)


def erro_amigavel(e, fonte):
    contexto = e.get_context(fonte).rstrip()
    if isinstance(e, UnexpectedCharacters):
        caractere = fonte[e.pos_in_stream]
        dica = " Horários só vão de 00:00 a 23:59 (formato HH:MM)." if caractere == ":" else ""
        return "léxica", (f"❌ ERRO LÉXICO na linha {e.line}, coluna {e.column}: o caractere '{caractere}' não pertence à CasaScript.{dica}\n\n{contexto}")
    if isinstance(e, UnexpectedToken):
        esperados = sorted({NOMES_AMIGAVEIS.get(x, x) for x in e.expected})
        achou = "o fim do programa" if e.token.type == "$END" else f"'{e.token}'"
        return "sintática", (f"❌ ERRO SINTÁTICO na linha {e.line}, coluna {e.column}: encontrei {achou}, mas esperava: {', '.join(esperados)}\n\n{contexto}")
    if isinstance(e, UnexpectedEOF):
        return "sintática", "❌ ERRO SINTÁTICO: o programa terminou antes da hora (faltou um FIM?)."
    return "desconhecida", str(e)


def compilar(fonte, otimizar=True):
    r = ResultadoCompilacao()
    try:
        r.tokens = analisar_lexico(fonte)
        r.arvore = parser.parse(fonte)
    except (UnexpectedCharacters, UnexpectedToken, UnexpectedEOF) as e:
        r.fase_erro, msg = erro_amigavel(e, fonte)
        r.mensagens.append(msg)
        return r
    r.ast = ConstrutorAST(fonte).transform(r.arvore)
    erros, r.avisos = AnalisadorSemantico().analisar(r.ast)
    if erros:
        r.fase_erro = "semântica"
        r.mensagens = erros
        return r
    otm = Otimizador()
    r.ast_otimizada = otm.otimizar(r.ast) if otimizar else r.ast
    r.relatorio_otimizacao = otm.relatorio
    r.bytecode = GeradorDeCodigo().gerar(r.ast_otimizada)
    r.ok = True
    return r


def contar_instrucoes(res):
    return sum(len(b.condicao) + len(b.acoes) + len(b.acoes_senao) for b in res.bytecode)


def main():
    print("✅ CasaScript 2.0 carregado.")
    res = compilar(PROGRAMA_EXEMPLO)
    if res.ok:
        print(f"Programa compilado com {len(res.bytecode)} regra(s).")
        print(desenhar_ast(res.ast_otimizada))
        for regra in res.bytecode:
            mostrar_regra_compilada(regra)
    else:
        print("\n".join(res.mensagens))

    casa = CasaPet()
    central = CentralDeAutomacao(res.bytecode, casa)
    print("Executando teste de ativação de borda de subida/descida...")
    print(central.evento("movimento", True))
    print(central.evento("movimento", False))


if __name__ == "__main__":
    main()
