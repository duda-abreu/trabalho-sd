import time
import random

# Imports dos nossos modulos de estrategia usando import relativo
from .rarest_first import escolher_bloco_mais_raro
from .tit_for_tat_strategy import (_calcular_pontuacao_de_raridade_do_peer,
                                   selecionar_candidato_optimistic_aleatorio,
                                   avaliar_e_atualizar_listas_unchoked)
from .choking_manager import ChokingManager # Importa a classe para instanciar
from . import choking_manager as cm_module_para_mocking # Importa o modulo para fazer o patch do t4t

# --- Mock simples para tit_for_tat_strategy ---
class MockTitForTatStrategy:
    # Atributos para controlar o comportamento do mock em cada teste
    selecionado_para_optimistic = None
    retorno_avaliacao_fixos = []
    retorno_avaliacao_optimistic = None

    # Contadores de chamadas (opcional, para asserts mais avancados)
    contador_selecionar_candidato = 0
    contador_avaliar_e_atualizar = 0

    def reset_mock(self):
        self.selecionado_para_optimistic = None
        self.retorno_avaliacao_fixos = []
        self.retorno_avaliacao_optimistic = None
        self.contador_selecionar_candidato = 0
        self.contador_avaliar_e_atualizar = 0

    def selecionar_candidato_optimistic_aleatorio(self, **kwargs):
        self.contador_selecionar_candidato += 1
        # print(f"DEBUG MOCK: selecionar_candidato_optimistic_aleatorio chamado com {kwargs}. Retornando: {self.selecionado_para_optimistic}")
        return self.selecionado_para_optimistic

    def avaliar_e_atualizar_listas_unchoked(self, **kwargs):
        self.contador_avaliar_e_atualizar += 1
        # print(f"DEBUG MOCK: avaliar_e_atualizar_listas_unchoked chamado com {kwargs}. Retornando: ({self.retorno_avaliacao_fixos}, {self.retorno_avaliacao_optimistic})")
        return self.retorno_avaliacao_fixos, self.retorno_avaliacao_optimistic

mock_t4t_global_instance = MockTitForTatStrategy()

# --- Helper para rodar os testes ---
def run_test(test_function):
    test_name = test_function.__name__
    print(f"--- Rodando teste: {test_name} ---")
    try:
        # Resetar o mock global e o seed do random antes de cada teste
        mock_t4t_global_instance.reset_mock()
        random.seed(42) # Garante determinismo para testes que usam random
        test_function()
        print(f"[PASSOU] Teste {test_name}\n")
    except AssertionError as e:
        print(f"[FALHOU] Teste {test_name}: {e}\n")
    except Exception as e:
        print(f"[ERRO NO TESTE] {test_name}: Excecao inesperada - {e}\n")
        import traceback
        traceback.print_exc() # Imprime o traceback completo para erros inesperados
        print("")


# --- Testes para rarest_first.py ---
def teste_rf_ja_tem_tudo():
    meus_blocos = {0, 1, 2}
    todos_blocos = {0, 1, 2}
    mapa_peers = {'peerA': {0,1}}
    resultado = escolher_bloco_mais_raro(meus_blocos, todos_blocos, mapa_peers)
    assert resultado is None, "Deveria ser None, ja que tenho todos os blocos"

def teste_rf_nenhum_bloco_necessario_disponivel():
    meus_blocos = {0}
    todos_blocos = {0, 1, 2}
    mapa_peers = {'peerA': {0}}
    resultado = escolher_bloco_mais_raro(meus_blocos, todos_blocos, mapa_peers)
    assert resultado is None, "Deveria ser None, nenhum bloco necessario esta disponivel"

def teste_rf_um_bloco_claramente_raro():
    meus_blocos = set()
    todos_blocos = {0, 1, 2}
    mapa_peers = {'peerA': {0, 1}, 'peerB': {0, 1}, 'peerC': {0, 2}}
    resultado = escolher_bloco_mais_raro(meus_blocos, todos_blocos, mapa_peers)
    assert resultado == 2, f"Deveria escolher o bloco 2 (mais raro), mas escolheu {resultado}"

def teste_rf_empate_na_raridade():
    meus_blocos = set()
    todos_blocos = {0, 1, 2, 3}
    mapa_peers = {'peerA': {0, 3}, 'peerB': {1, 3}}
    resultado = escolher_bloco_mais_raro(meus_blocos, todos_blocos, mapa_peers)
    assert resultado in [0, 1], f"Deveria escolher 0 ou 1 (empate de raridade), mas escolheu {resultado}"

def teste_rf_sem_peers_conhecidos():
    meus_blocos = {0}
    todos_blocos = {0, 1, 2}
    mapa_peers = {}
    resultado = escolher_bloco_mais_raro(meus_blocos, todos_blocos, mapa_peers)
    assert resultado is None, "Deveria ser None, nao ha peers conhecidos"

# --- Testes para tit_for_tat_strategy.py ---
MEU_PEER_ID_TESTE = "test_peer_me"

def teste_t4t_pontuacao_peer_com_blocos_raros():
    mapa = {"peerA": {0, 2}, "peerB": {1, 2}, MEU_PEER_ID_TESTE: {0,1,2}}
    todos_b = {0, 1, 2, 3}
    # Freq (sem contar MEU_PEER_ID_TESTE): B0:1, B1:1, B2:2. num_total_peers_com_info=2. limiar_raro=max(1, int(2*0.3))=1.
    # Blocos raros (freq<=1): 0, 1. peerA tem o bloco 0 (raro). Pontuacao = 1.
    pontuacao = _calcular_pontuacao_de_raridade_do_peer("peerA", mapa, todos_b, MEU_PEER_ID_TESTE)
    assert pontuacao == 1, f"Esperado 1, obteve {pontuacao}"

def teste_t4t_pontuacao_peer_com_blocos_comuns():
    mapa = {"peerA": {2, 3}, "peerB": {0,1,2,3}, "peerC": {0,1,2,3}, MEU_PEER_ID_TESTE:set()}
    todos_b = {0,1,2,3}
    # Freq: B0:2, B1:2, B2:3, B3:3. num_total_peers_com_info=3. limiar_raro=max(1, int(3*0.3))=1.
    # Nenhum bloco de peerA (2,3) eh raro. Pontuacao = 0.
    pontuacao = _calcular_pontuacao_de_raridade_do_peer("peerA", mapa, todos_b, MEU_PEER_ID_TESTE)
    assert pontuacao == 0, f"Esperado 0, obteve {pontuacao}"

def teste_t4t_seleciona_optimistic_com_candidatos():
    conhecidos = {"p1", "p2", "p3", "p4", MEU_PEER_ID_TESTE}
    fixos = {"p1"}
    optimistic_atual = "p2"
    # Candidatos possiveis: p3, p4. Com seed(42), random.choice(['p3', 'p4']) ou (['p4', 'p3']) -> p4
    # (random.choice em lista pega um elemento, a ordem da lista pode variar de sets)
    # Para garantir, vamos testar se está no conjunto.
    escolhido = selecionar_candidato_optimistic_aleatorio(conhecidos, fixos, optimistic_atual, MEU_PEER_ID_TESTE)
    assert escolhido in {"p3", "p4"}, f"Deveria ser 'p3' ou 'p4', foi {escolhido}"

def teste_t4t_seleciona_optimistic_sem_candidatos():
    conhecidos = {"p1", "p2", MEU_PEER_ID_TESTE}
    fixos = {"p1"}
    optimistic_atual = "p2"
    escolhido = selecionar_candidato_optimistic_aleatorio(conhecidos, fixos, optimistic_atual, MEU_PEER_ID_TESTE)
    assert escolhido is None, "Nao deveria escolher ninguem"

def teste_t4t_avalia_promocao_optimistic_com_vaga():
    fixos_atuais = ["p_fixo1"] 
    candidato = "p_optimista_bom"
    mapa = {"p_fixo1": {0}, "p_optimista_bom": {1}, "outro": {0}, MEU_PEER_ID_TESTE:set()} # B1 raro, B0 comum
    todos_b, meus_b, max_f = {0,1}, set(), 2
    # p_optimista_bom (score 1), p_fixo1 (score 0)
    novos_f, novo_o = avaliar_e_atualizar_listas_unchoked(fixos_atuais, candidato, max_f, mapa, meus_b, todos_b, MEU_PEER_ID_TESTE)
    assert "p_optimista_bom" in novos_f and "p_fixo1" in novos_f, "Ambos deveriam estar nos fixos"
    assert novos_f.index("p_optimista_bom") < novos_f.index("p_fixo1"), "Otimista bom deveria vir primeiro"
    assert novo_o is None, "Otimista promovido deixa de ser otimista"

def teste_t4t_avalia_optimistic_nao_promovido():
    fixos_atuais = ["p_fixo_bom1", "p_fixo_bom2"] 
    candidato = "p_optimista_ruim"
    mapa = {"p_fixo_bom1":{0},"p_fixo_bom2":{1},"p_optimista_ruim":{2},"outro":{0,1,2}, MEU_PEER_ID_TESTE:set()}
    # -- Todos blocos comuns, todas pontuacoes 0.
    todos_b, meus_b, max_f = {0,1,2}, set(), 2
    novos_f, novo_o = avaliar_e_atualizar_listas_unchoked(fixos_atuais, candidato, max_f, mapa, meus_b, todos_b, MEU_PEER_ID_TESTE)
    assert "p_optimista_ruim" not in novos_f, "Otimista ruim nao deveria ser promovido"
    assert novo_o == "p_optimista_ruim", "Otimista ruim continua como otimista"
    assert set(novos_f) == set(fixos_atuais), "Fixos deveriam permanecer os mesmos"


# --- Testes para choking_manager.py ---
def teste_cm_inicializacao_e_add_peer():
    cm = ChokingManager("cm_peer_eu", max_fixos_unchoked=1, intervalo_optimistic_s=10)
    assert cm.meu_peer_id == "cm_peer_eu"
    assert cm.max_fixos_unchoked == 1
    cm.peer_entrou_na_rede("p1")
    assert "p1" in cm.peers_conhecidos
    cm.peer_entrou_na_rede("cm_peer_eu") 
    assert "cm_peer_eu" not in cm.peers_conhecidos

def teste_cm_estado_unchoke():
    cm = ChokingManager("cm_peer_eu")
    cm.peers_fixos_unchoked = ["p_fixo"]
    cm.peer_optimistic_unchoked = "p_opt"
    assert cm.esta_peer_unchoked("p_fixo")
    assert cm.esta_peer_unchoked("p_opt")
    assert not cm.esta_peer_unchoked("p_outro")
    assert cm.get_peers_unchoked_por_mim() == {"p_fixo", "p_opt"}

def teste_cm_executar_ciclo_com_mock_t4t_promocao():
    # Salva o modulo original que choking_manager.py usa e o substitui pelo mock
    original_t4t_usado_pelo_cm_module = cm_module_para_mocking.tit_for_tat_strategy
    cm_module_para_mocking.tit_for_tat_strategy = mock_t4t_global_instance
    
    cm = ChokingManager("cm_peer_eu", max_fixos_unchoked=1, intervalo_optimistic_s=10)
    cm.peer_entrou_na_rede("p1_candidato")
    cm.peer_entrou_na_rede("p2_outro")

    ts_inicial = time.time()
    cm.ultimo_timestamp_optimistic = ts_inicial - 11 # Forca o ciclo otimista

    # Configura o mock: p1_candidato eh selecionado e depois promovido
    mock_t4t_global_instance.selecionado_para_optimistic = "p1_candidato"
    mock_t4t_global_instance.retorno_avaliacao_fixos = ["p1_candidato"] # Promovido
    mock_t4t_global_instance.retorno_avaliacao_optimistic = None      # Nao eh mais otimista

    cm.executar_ciclo_unchoking(ts_inicial, {"p1_candidato":{1},"p2_outro":{2}}, {0}, {0,1,2})
    
    assert "p1_candidato" in cm.peers_fixos_unchoked, "p1_candidato deveria ser fixo"
    assert cm.peer_optimistic_unchoked is None, "Otimista deveria ser None apos promocao"
    assert cm.ultimo_timestamp_optimistic == ts_inicial, "Timestamp do otimista deve ser atualizado"
    assert mock_t4t_global_instance.contador_selecionar_candidato == 1
    assert mock_t4t_global_instance.contador_avaliar_e_atualizar == 1

    # Restaura o modulo original
    cm_module_para_mocking.tit_for_tat_strategy = original_t4t_usado_pelo_cm_module

def teste_cm_executar_ciclo_com_mock_t4t_sem_promocao():
    original_t4t_usado_pelo_cm_module = cm_module_para_mocking.tit_for_tat_strategy
    cm_module_para_mocking.tit_for_tat_strategy = mock_t4t_global_instance

    cm = ChokingManager("cm_peer_eu", max_fixos_unchoked=1, intervalo_optimistic_s=10)
    cm.peer_entrou_na_rede("p_fixo_existente")
    cm.peer_entrou_na_rede("p_candidato_ruim")
    cm.peers_fixos_unchoked = ["p_fixo_existente"] # Ja tem um fixo

    ts_inicial = time.time()
    cm.ultimo_timestamp_optimistic = ts_inicial - 11

    # Configura o mock: p_candidato_ruim eh selecionado, mas nao promovido
    mock_t4t_global_instance.selecionado_para_optimistic = "p_candidato_ruim"
    mock_t4t_global_instance.retorno_avaliacao_fixos = ["p_fixo_existente"] # Fixo continua
    mock_t4t_global_instance.retorno_avaliacao_optimistic = "p_candidato_ruim" # Continua otimista

    cm.executar_ciclo_unchoking(ts_inicial, {"p_fixo_existente":{1},"p_candidato_ruim":{2}}, {0}, {0,1,2})
    
    assert "p_fixo_existente" in cm.peers_fixos_unchoked
    assert "p_candidato_ruim" not in cm.peers_fixos_unchoked
    assert cm.peer_optimistic_unchoked == "p_candidato_ruim"
    assert mock_t4t_global_instance.contador_selecionar_candidato == 1
    assert mock_t4t_global_instance.contador_avaliar_e_atualizar == 1
    
    cm_module_para_mocking.tit_for_tat_strategy = original_t4t_usado_pelo_cm_module

# --- Lista de todos os testes a serem executados ---
todos_os_testes_definidos = [
    teste_rf_ja_tem_tudo,
    teste_rf_nenhum_bloco_necessario_disponivel,
    teste_rf_um_bloco_claramente_raro,
    teste_rf_empate_na_raridade,
    teste_rf_sem_peers_conhecidos,
    teste_t4t_pontuacao_peer_com_blocos_raros,
    teste_t4t_pontuacao_peer_com_blocos_comuns,
    teste_t4t_seleciona_optimistic_com_candidatos,
    teste_t4t_seleciona_optimistic_sem_candidatos,
    teste_t4t_avalia_promocao_optimistic_com_vaga,
    teste_t4t_avalia_optimistic_nao_promovido,
    teste_cm_inicializacao_e_add_peer,
    teste_cm_estado_unchoke,
    teste_cm_executar_ciclo_com_mock_t4t_promocao,
    teste_cm_executar_ciclo_com_mock_t4t_sem_promocao,
]

if __name__ == "__main__":
    print("Iniciando bateria de testes para as estrategias...\n")
    
    for numero, teste_func in enumerate(todos_os_testes_definidos):
        # print(f"Preparando para rodar teste #{numero + 1}")
        run_test(teste_func)

    print("\nBateria de testes concluida.")