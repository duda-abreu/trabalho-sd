import random
from typing import Optional, Set, Dict

def escolher_bloco_mais_raro(meus_blocos: Set[int],
                             todos_os_blocos_do_arquivo: Set[int],
                             mapa_de_blocos_dos_peers: Dict[str, Set[int]]) -> Optional[int]:
    """
    escolhe o id do bloco mais raro que o peer ainda nao possui.
    lidar com empates de raridade,
    escolhendo aleatoriamente entre os blocos igualmente mais raros.
    """
    # passo 1: ver quais blocos ainda faltam
    blocos_necessarios = todos_os_blocos_do_arquivo - meus_blocos
    if not blocos_necessarios:
        return None

    # passo 2: contar a disponibilidade de cada bloco necessario
    contagem_de_raridade = {}
    for id_bloco in blocos_necessarios:
        contagem_de_raridade[id_bloco] = 0
        for id_peer in mapa_de_blocos_dos_peers:
            blocos_do_peer_vizinho = mapa_de_blocos_dos_peers.get(id_peer, set())
            if id_bloco in blocos_do_peer_vizinho:
                contagem_de_raridade[id_bloco] += 1
    
    # passo 3: filtrar apenas os blocos que estao disponiveis (contagem > 0)
    blocos_disponiveis = {
        id_bloco: contagem
        for id_bloco, contagem in contagem_de_raridade.items()
        if contagem > 0
    }

    if not blocos_disponiveis:
        return None

    # passo 4: encontrar qual eh a menor contagem de raridade
    contagem_minima = min(blocos_disponiveis.values())

    # passo 5: criar uma lista com todos os blocos que tem essa raridade minima
    candidatos_mais_raros = [
        id_bloco
        for id_bloco, contagem in blocos_disponiveis.items()
        if contagem == contagem_minima
    ]

    # passo 6: escolher aleatoriamente um bloco da lista de candidatos mais raros
    if candidatos_mais_raros:
        bloco_escolhido = random.choice(candidatos_mais_raros)
        # print(f"debug: raridade minima: {contagem_minima}. candidatos: {candidatos_mais_raros}. escolhido: {bloco_escolhido}")
        return bloco_escolhido
    

    # fallback, caso a lista de candidatos por algum motivo esteja vazia
    return None