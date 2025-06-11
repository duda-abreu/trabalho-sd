import random

class DistribuidorBlocos:
    def __init__(self, total_blocos=20):
        # Número total de blocos do arquivo
        self.total_blocos = total_blocos
        
        # Dicionário para rastrear quais blocos cada peer possui
        self.blocos_por_peer = {}
        
        # O tracker atua como seed inicial e possui todos os blocos
        self.blocos_por_peer['tracker'] = list(range(self.total_blocos))
        print(f"Distribuidor iniciado com {total_blocos} blocos totais")
        print(f"Tracker inicializado com todos os {self.total_blocos} blocos")
    
    def distribuir_blocos_iniciais(self, peer_id):
        """Distribui blocos iniciais aleatórios para um novo peer"""
        if peer_id in self.blocos_por_peer:
            print(f"[AVISO] Peer {peer_id} já recebeu blocos antes: {self.blocos_por_peer[peer_id]}")
            return self.blocos_por_peer[peer_id]
        
        # Cada peer começa com 30-50% dos blocos aleatoriamente
        min_blocos = max(1, self.total_blocos // 3)  # mínimo 1/3
        max_blocos = max(2, self.total_blocos // 2)  # máximo 1/2

        num_blocos = random.randint(min_blocos, max_blocos)
        
        # Seleciona blocos aleatórios
        todos_blocos = list(range(self.total_blocos))
        blocos_selecionados = random.sample(todos_blocos, num_blocos)
        blocos_selecionados.sort()
        
        # Salva os blocos do peer
        self.blocos_por_peer[peer_id] = blocos_selecionados
        
        print(f"Peer {peer_id} recebeu {len(blocos_selecionados)} blocos: {blocos_selecionados}")
        
        return blocos_selecionados
    
    def obter_blocos_peer(self, peer_id):
        """Retorna lista de blocos que um peer possui"""
        return self.blocos_por_peer.get(peer_id, [])
    
    def atualizar_blocos_peer(self, peer_id, novos_blocos):
        """Atualiza lista de blocos de um peer"""
        if peer_id not in self.blocos_por_peer:
            self.blocos_por_peer[peer_id] = []
        
        self.blocos_por_peer[peer_id] = sorted(list(set(novos_blocos)))
        print(f"Blocos do peer {peer_id} atualizados: {len(novos_blocos)} blocos")
    
    def adicionar_bloco_peer(self, peer_id, num_bloco):
        """Adiciona um bloco específico a um peer"""
        if peer_id not in self.blocos_por_peer:
            self.blocos_por_peer[peer_id] = []
        
        if num_bloco not in self.blocos_por_peer[peer_id]:
            self.blocos_por_peer[peer_id].append(num_bloco)
            self.blocos_por_peer[peer_id].sort()
            print(f"Bloco {num_bloco} adicionado ao peer {peer_id}")
    
    def obter_estatisticas_blocos(self):
        """Retorna estatísticas sobre distribuição de blocos"""
        if not self.blocos_por_peer:
            return {"total_peers": 0, "blocos_por_peer": {}}
        
        estatisticas = {
            "total_peers": len(self.blocos_por_peer),
            "total_blocos": self.total_blocos,
            "blocos_por_peer": {}
        }
        
        # Conta quantos peers têm cada bloco
        contador_blocos = {}
        for peer_id, blocos in self.blocos_por_peer.items():
            estatisticas["blocos_por_peer"][peer_id] = len(blocos)
            
            for bloco in blocos:
                if bloco not in contador_blocos:
                    contador_blocos[bloco] = 0
                contador_blocos[bloco] += 1
        
        estatisticas["distribuicao_blocos"] = contador_blocos
        
        return estatisticas
    
    def remover_peer(self, peer_id):
        """Remove peer da lista de distribuição"""
        if peer_id in self.blocos_por_peer:
            del self.blocos_por_peer[peer_id]
            print(f"Peer {peer_id} removido da distribuição")
    
    def peer_tem_arquivo_completo(self, peer_id):
        """Verifica se peer tem o arquivo completo"""
        blocos_peer = self.obter_blocos_peer(peer_id)
        return len(blocos_peer) == self.total_blocos
    
    def ainda_precisa_seed(self):
        """Verifica se ainda há peers que precisam de blocos.
        Enquanto algum peer (exceto o tracker) estiver incompleto, o tracker deve continuar atuando como seed."""
        for peer_id, blocos in self.blocos_por_peer.items():
            if peer_id == 'tracker':
                continue
            if len(blocos) < self.total_blocos:
                return True
        return False
    
    def fornecer_bloco_ao_peer(self, peer_id):
        """
        O tracker atua como seed inicial e pode fornecer blocos para um peer.
        Retorna um bloco que o peer não tem ainda, para ajudar na convergência da rede.
        Retorna None se o peer já tiver todos os blocos.
        """
        blocos_peer = set(self.obter_blocos_peer(peer_id))
        blocos_tracker = set(self.blocos_por_peer['tracker'])
        
        blocos_faltando = blocos_tracker - blocos_peer
        if blocos_faltando:
            bloco_escolhido = random.choice(list(blocos_faltando))
            self.adicionar_bloco_peer(peer_id, bloco_escolhido)
            print(f"Tracker forneceu bloco {bloco_escolhido} ao peer {peer_id}")
            return bloco_escolhido
        else:
            return None
    
    def __str__(self):
        """Representação em string do distribuidor"""
        return f"DistribuidorBlocos: {len(self.blocos_por_peer)} peers, {self.total_blocos} blocos totais"