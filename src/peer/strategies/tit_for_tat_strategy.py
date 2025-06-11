import random

def _calcular_pontuacao_de_raridade_do_peer(
        peer_id_avaliado: str,
        mapa_de_blocos_global: dict[str, set[int]],
        todos_os_blocos_do_arquivo: set[int],
        meu_peer_id: str) -> int:
    """
    calcula uma pontuacao para um peer com base em quantos blocos 'raros' ele possui.
    um bloco eh considerado raro se estiver presente em poucos peers na rede.

    a pontuacao eh simplesmente a contagem de blocos raros que o peer possui.
    """
    if peer_id_avaliado not in mapa_de_blocos_global:
        return 0 # peer desconhecido ou sem blocos informados

    blocos_do_peer_avaliado = mapa_de_blocos_global.get(peer_id_avaliado, set())
    if not blocos_do_peer_avaliado:
        return 0 # peer nao tem nenhum bloco

    # passo 1: calcular a frequencia de cada bloco na rede (quantos peers tem cada bloco)
    frequencia_blocos: dict[int, int] = {bloco_id: 0 for bloco_id in todos_os_blocos_do_arquivo}
    num_total_peers_com_info = 0
    for peer_id, blocos_deste_peer in mapa_de_blocos_global.items():
        if peer_id == meu_peer_id: # nao contamos nossos proprios blocos para definir raridade global
            continue
        if blocos_deste_peer: # so conta se o peer tiver alguma info de bloco
            num_total_peers_com_info +=1
            for bloco_id in blocos_deste_peer:
                if bloco_id in frequencia_blocos:
                    frequencia_blocos[bloco_id] += 1
    
    if num_total_peers_com_info == 0: # evita divisao por zero e define que nada eh raro se nao ha outros peers
        return 0


    # passo 2: definir um limiar de raridade.
    # por exemplo, um bloco eh 'raro' se estiver em menos de 25% dos outros peers que tem informacao.
    # ou um valor fixo pequeno, ex: <= 2 peers.
    # vamos usar um limiar um pouco dinamico: um bloco eh raro se estiver em ate 'limiar_contagem_raro' peers.
    # um valor simples: se um bloco esta em 1 ou 2 outros peers, consideramos raro para essa contagem.
    # idealmente, isso poderia ser mais sofisticado (ex: baseado em percentil de frequencia).
    limiar_contagem_raro = max(1, int(num_total_peers_com_info * 0.3)) # ex: ate 30% dos peers eh raro

    # passo 3: contar quantos blocos do 'peer_id_avaliado' sao raros
    pontuacao = 0
    for bloco_id in blocos_do_peer_avaliado:
        if frequencia_blocos.get(bloco_id, num_total_peers_com_info + 1) <= limiar_contagem_raro : # se o bloco nao estiver em frequencia_blocos, eh como se fosse muito comum (evita erro)
            pontuacao += 1
            
    # print(f"debug (tit_for_tat): pontuacao para {peer_id_avaliado}: {pontuacao} (limiar_raro <= {limiar_contagem_raro} peers de {num_total_peers_com_info})")
    return pontuacao


def selecionar_candidato_optimistic_aleatorio(
        peers_conhecidos: set[str],
        peers_fixos_unchoked: set[str],
        peer_optimistic_atual: str | None,
        meu_peer_id: str) -> str | None:
    """
    seleciona um novo peer aleatorio para ser o 'optimistic unchoke'.
    o escolhido nao pode ser o proprio peer, nem um dos fixos, nem o otimista atual.
    """
    # print(f"debug (tit_for_tat): selecionando optimistic. conhecidos: {len(peers_conhecidos)}, fixos: {len(peers_fixos_unchoked)}, atual: {peer_optimistic_atual}")
    
    candidatos_possiveis = list(
        peers_conhecidos - peers_fixos_unchoked - {meu_peer_id}
    )
    
    # se o optimistic atual existe, remove ele também da lista de candidatos para escolher um *novo*
    if peer_optimistic_atual and peer_optimistic_atual in candidatos_possiveis:
        candidatos_possiveis.remove(peer_optimistic_atual)

    if not candidatos_possiveis:
        # print("debug (tit_for_tat): sem candidatos viaveis para optimistic unchoke.")
        return None
    
    escolhido = random.choice(candidatos_possiveis)
    # print(f"debug (tit_for_tat): candidato optimistic aleatorio escolhido: {escolhido}")
    return escolhido


def avaliar_e_atualizar_listas_unchoked(
        peers_fixos_atuais: list[str], # lista dos peers atualmente como fixos unchoked
        peer_candidato_para_avaliacao: str | None, # o peer que foi escolhido optimisticamente (pode ser None)
        max_fixos: int, # numero maximo de slots para peers fixos unchoked
        mapa_de_blocos_global: dict[str, set[int]], # info de blocos de todos os peers
        meus_blocos: set[int], # meus blocos (nao usado diretamente aqui, mas em _calcular_pontuacao)
        todos_os_blocos_do_arquivo: set[int], #- todos os blocos possiveis do arquivo
        meu_peer_id: str
    ) -> tuple[list[str], str | None]:
    """
    avalia o 'peer_candidato_para_avaliacao' (normalmente o optimistic unchoke)
    e os 'peers_fixos_atuais'. decide quem deve compor a nova lista de fixos
    e quem sera o optimistic unchoke final para este ciclo.

    retorna: uma tupla com (nova_lista_de_peers_fixos, peer_optimistic_final_neste_ciclo)
    """
    # print(f"debug (tit_for_tat): avaliando listas. Fixos atuais: {peers_fixos_atuais}, candidato: {peer_candidato_para_avaliacao}")

    # passo 1: calcular pontuacao para todos os envolvidos (fixos atuais + candidato)
    todos_para_avaliar = set(peers_fixos_atuais)
    if peer_candidato_para_avaliacao and peer_candidato_para_avaliacao != meu_peer_id: # so avalia se existe e nao sou eu
        todos_para_avaliar.add(peer_candidato_para_avaliacao)

    # dicionario para guardar peer_id -> pontuacao
    pontuacoes_peers: dict[str, int] = {}
    for peer_id in todos_para_avaliar:
        pontuacoes_peers[peer_id] = _calcular_pontuacao_de_raridade_do_peer(
            peer_id_avaliado=peer_id,
            mapa_de_blocos_global=mapa_de_blocos_global,
            todos_os_blocos_do_arquivo=todos_os_blocos_do_arquivo, # Argumento correto
            meu_peer_id=meu_peer_id
        )
    
    # passo 2: ordenar os peers pela pontuacao (maior primeiro)
    # o sort em python eh estavel, o que eh bom se as pontuacoes forem iguais
    peers_ordenados_por_pontuacao = sorted(
        pontuacoes_peers.keys(),
        key=lambda pid: pontuacoes_peers[pid],
        reverse=True # queremos a maior pontuacao primeiro
    )
    
    # print(f"debug (tit_for_tat): peers ordenados por pontuacao: {[(p, pontuacoes_peers[p]) for p in peers_ordenados_por_pontuacao]}")

    # passo 3: preencher a nova lista de fixos com os melhores, ate o maximo permitido
    nova_lista_fixos = peers_ordenados_por_pontuacao[:max_fixos]

    # passo 4: determinar quem sera o optimistic unchoke final para este ciclo
    peer_optimistic_final = None
    if peer_candidato_para_avaliacao:
        # se o candidato avaliado nao conseguiu entrar na lista de fixos (e nao era um dos fixos antigos),
        # ele continua como o otimista para este ciclo.
        if peer_candidato_para_avaliacao not in nova_lista_fixos:
            peer_optimistic_final = peer_candidato_para_avaliacao
        # else: o candidato foi promovido ou ja era fixo e se manteve, entao o slot otimista
        # teoricamente fica 'vago' ate a proxima selecao aleatoria pelo ChokingManager,
        # pois a regra eh "4 fixos + 1 otimista". 
        # o otimista eh o peer escolhido aleatoriamente para teste.
        # se ele eh promovido a fixo, o 'teste' dele acabou com sucesso, e nao existe mais slot otimista para ele.
        # o ChokingManager devera escolher um novo optimistic unchoke no proximo ciclo.
    
    # print(f"debug (tit_for_tat): resultado da avaliacao. Novos fixos: {nova_lista_fixos}, Novo optimistic: {peer_optimistic_final}")
    return nova_lista_fixos, peer_optimistic_final