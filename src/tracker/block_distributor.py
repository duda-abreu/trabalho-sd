import random

class DistribuidorBlocos:
    def __init__(self, total_blocos=20):
        # Número total de blocos do arquivo
        self.total_blocos = total_blocos
        
        # Dicionário para rastrear quais blocos cada peer possui
        self.blocos_por_peer: dict[str, set[int]] = {} 
        
        print(f"Distribuidor iniciado com {total_blocos} blocos totais")
    
    def distribuir_blocos_iniciais(self, peer_id: str) -> list[int]:
        """Distribui blocos iniciais aleatórios para um novo peer."""
        # Cada peer começa com 30-50% dos blocos aleatoriamente
        min_blocos = max(1, self.total_blocos // 3)  # mínimo 1/3
        max_blocos = max(2, self.total_blocos // 2)  # máximo 1/2
        
        num_blocos = random.randint(min_blocos, max_blocos)
        
        # Seleciona blocos aleatórios
        todos_blocos = list(range(self.total_blocos))
        blocos_selecionados = random.sample(todos_blocos, num_blocos)
        
        # Salva os blocos do peer como um set
        self.blocos_por_peer[peer_id] = set(blocos_selecionados)
        
        # Para logging ou retorno
        blocos_ordenados = sorted(list(self.blocos_por_peer[peer_id]))
        print(f"Peer {peer_id} recebeu {len(blocos_ordenados)} blocos iniciais: {blocos_ordenados}")
        
        return blocos_ordenados # Retorna como lista ordenada para consistência com o que o peer espera


    def obter_blocos_peer(self, peer_id: str) -> list[int]:
        """Retorna lista de blocos que um peer possui."""
        # Retorna uma lista ordenada 
        return sorted(list(self.blocos_por_peer.get(peer_id, set())))
    
    def atualizar_blocos_peer(self, peer_id: str, novos_blocos: list[int]):
        """Atualiza lista de blocos de um peer."""
        # Converte a lista de entrada para um set 
        self.blocos_por_peer[peer_id] = set(novos_blocos)
        print(f"Blocos do peer {peer_id} atualizados para {len(novos_blocos)} blocos.")
    
    def adicionar_bloco_peer(self, peer_id: str, num_bloco: int):
        """Adiciona um bloco específico a um peer."""
        if peer_id not in self.blocos_por_peer:
            self.blocos_por_peer[peer_id] = set() # Inicializa como set vazio
        
        if num_bloco not in self.blocos_por_peer[peer_id]:
            self.blocos_por_peer[peer_id].add(num_bloco)
            print(f"Bloco {num_bloco} adicionado ao peer {peer_id}.")
        else:
            print(f"Peer {peer_id} já possui o bloco {num_bloco}.")

    def obter_estatisticas_blocos(self) -> dict:
        """Retorna estatísticas sobre distribuição de blocos."""
        if not self.blocos_por_peer:
            return {"total_peers": 0, "total_blocos": self.total_blocos, "blocos_por_peer": {}, "distribuicao_blocos": {}}
        
        estatisticas = {
            "total_peers": len(self.blocos_por_peer),
            "total_blocos": self.total_blocos,
            "blocos_por_peer": {} # Quantidade de blocos por peer
        }
        
        # Conta quantos peers têm cada bloco
        contador_blocos: dict[int, int] = {bloco_id: 0 for bloco_id in range(self.total_blocos)}
        
        for peer_id, blocos_do_peer in self.blocos_por_peer.items():
            estatisticas["blocos_por_peer"][peer_id] = len(blocos_do_peer)
            
            for bloco in blocos_do_peer:
                if bloco in contador_blocos: # Garante que é um bloco válido do arquivo
                    contador_blocos[bloco] += 1
        
        estatisticas["distribuicao_blocos"] = contador_blocos
        
        return estatisticas
    
    def remover_peer(self, peer_id: str):
        """Remove peer da lista de distribuição."""
        if peer_id in self.blocos_por_peer:
            del self.blocos_por_peer[peer_id]
            print(f"Peer {peer_id} removido da distribuição.")
        else:
            print(f"Peer {peer_id} não encontrado na distribuição para remoção.")
    
    def peer_tem_arquivo_completo(self, peer_id: str) -> bool:
        """Verifica se peer tem o arquivo completo."""
        # Se o peer não está registrado, não pode ter o arquivo completo
        if peer_id not in self.blocos_por_peer:
            return False
        
        blocos_peer = self.blocos_por_peer[peer_id]
        return len(blocos_peer) == self.total_blocos
    
    def __str__(self):
        """Representação em string do distribuidor."""
        return f"DistribuidorBlocos: {len(self.blocos_por_peer)} peers, {self.total_blocos} blocos totais"