import time

class GerenciadorPeers:
    def __init__(self):
        # Lista de peers ativos: {peer_id, ip, porta, timestamp}
        self.peers_ativos = {}
        print("Gerenciador de Peers iniciado")
    
    def adicionar_peer(self, peer_id, ip, porta, blocos=None):
        """Adiciona um novo peer à lista de ativos"""
        if blocos is None:
            blocos = []
        self.peers_ativos[peer_id] = {
            'peer_id': peer_id,
            'ip': ip,
            'porta': porta,
            'blocos': blocos,
            'timestamp': time.time()
        }
        print(f"Peer adicionado: {peer_id} ({ip}:{porta})")
    
    def remover_peer(self, peer_id):
        """Remove peer da lista de ativos"""
        if peer_id in self.peers_ativos:
            del self.peers_ativos[peer_id]
            print(f"Peer removido: {peer_id}")
        else:
            print(f"Peer {peer_id} não encontrado para remoção")
    
    def listar_peers_ativos(self):
        """Retorna lista de todos os peers ativos"""
        return list(self.peers_ativos.values())
    
    def obter_peer(self, peer_id):
        """Retorna informações de um peer específico"""
        return self.peers_ativos.get(peer_id, None)
    
    def total_peers(self):
        """Retorna número total de peers ativos"""
        return len(self.peers_ativos)
    
    def limpar_peers_inativos(self, timeout=300):
        """Remove peers que não respondem há muito tempo (5 min)"""
        tempo_atual = time.time()
        peers_inativos = []
        
        for peer_id, dados in self.peers_ativos.items():
            if tempo_atual - dados['timestamp'] > timeout:
                peers_inativos.append(peer_id)
        
        for peer_id in peers_inativos:
            self.remover_peer(peer_id)
            print(f"Peer inativo removido: {peer_id}")
    
    def atualizar_timestamp(self, peer_id):
        """Atualiza timestamp de um peer (para manter ativo)"""
        if peer_id in self.peers_ativos:
            self.peers_ativos[peer_id]['timestamp'] = time.time()
    
    def __str__(self):
        """Representação em string do gerenciador"""
        return f"GerenciadorPeers: {len(self.peers_ativos)} peers ativos"