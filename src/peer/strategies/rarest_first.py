def escolher_bloco_mais_raro(meus_blocos: set[int],
                             todos_os_blocos_do_arquivo: set[int],
                             mapa_de_blocos_dos_peers: dict[str, set[int]]) -> int | None:
    """
    escolhe o id do bloco mais raro que o peer ainda nao possui.

    esta funcao eh o coracao do 'rarest first'. ela olha para os blocos que faltam,
    ve quantos outros peers tem cada um desses blocos faltantes, e entao
    sugere qual bloco parece ser o mais 'dificil' de encontrar (o mais raro)
    para o peer tentar baixar logo.

    parametros:
        meus_blocos: um conjunto (set) com os ids dos blocos que eu ja tenho.
        todos_os_blocos_do_arquivo: um conjunto (set) com os ids de todos os blocos que o arquivo completo tem.
        mapa_de_blocos_dos_peers: um dicionario onde a chave eh o id de um peer conhecido
                                 e o valor eh um conjunto (set) dos ids dos blocos que esse peer tem.
                                 exemplo: {'peer_vizinho_1': {0, 1, 5}, 'peer_vizinho_2': {2, 3, 5}}

    retorna:
        o id do bloco (int) que foi escolhido como o mais raro para ser baixado.
        retorna none se eu ja tiver todos os blocos ou se nenhum dos blocos
        que eu preciso estiver disponivel nos peers que eu conheco.
    """
    # primeiro, a gente ve quais blocos ainda faltam pra completar o arquivo
    blocos_necessarios = todos_os_blocos_do_arquivo - meus_blocos

    # se a lista de blocos necessarios estiver vazia, eh porque ja temos tudo!
    # entao nao tem o que escolher.
    if not blocos_necessarios:
        # print("info: ja tenho todos os blocos, nada a fazer no rarest_first.") # log util pra debug
        return None

    # agora, pra cada bloco que a gente precisa, vamos contar em quantos peers ele esta disponivel.
    # quanto menor a contagem, mais raro eh o bloco.
    contagem_de_raridade = {}
    for id_bloco in blocos_necessarios:
        contagem_de_raridade[id_bloco] = 0  # comeca assumindo que ninguem tem
        for id_peer in mapa_de_blocos_dos_peers:
            # pega os blocos que o peer vizinho tem, se nao tiver info dele, considera um conjunto vazio
            blocos_do_peer_vizinho = mapa_de_blocos_dos_peers.get(id_peer, set())
            if id_bloco in blocos_do_peer_vizinho:
                contagem_de_raridade[id_bloco] += 1
    
    # beleza, agora temos a contagem. vamos filtrar e pegar so os blocos
    # que estao realmente disponiveis (contagem > 0).
    # nao adianta querer um bloco que, segundo nossa informacao, ninguem tem.
    blocos_disponiveis_para_baixar = {
        id_bloco: contagem
        for id_bloco, contagem in contagem_de_raridade.items()
        if contagem > 0
    }

    # se, depois de filtrar, nao sobrou nenhum bloco que esteja disponivel...
    if not blocos_disponiveis_para_baixar:
        # print("aviso: nenhum dos blocos que preciso esta disponivel nos peers conhecidos atualmente.")
        return None

    # finalmente, encontrar o bloco que tem a menor contagem (o mais raro)
    # a funcao min() do python pode fazer isso em dicionarios se a gente disser pra ele
    # olhar para os valores (as contagens) usando o 'key'.
    # se varios blocos tiverem a mesma contagem minima, ele pega um deles.
    # para o nosso caso, pegar qualquer um dos mais raros ja eh bom.
    id_bloco_escolhido = min(blocos_disponiveis_para_baixar, key=blocos_disponiveis_para_baixar.get)
    
    # contagem_do_escolhido = blocos_disponiveis_para_baixar[id_bloco_escolhido]
    # print(f"info: bloco mais raro escolhido: {id_bloco_escolhido} (encontrado em {contagem_do_escolhido} peers)")
    return id_bloco_escolhido