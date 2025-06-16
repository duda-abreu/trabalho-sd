import time

class GerenciadorPeers:
    def __init__(self):
        # Dicionário: peer_id -> {ip, porta, timestamp}
        self.peers_ativos = {}
        print("Gerenciador de Peers iniciado")

    def adicionar_peer(self, peer_id, ip, porta):
        """Adiciona um peer novo ou atualiza as informações de um peer existente."""
        self.peers_ativos[peer_id] = self.peers_ativos.get(peer_id, {})
        self.peers_ativos[peer_id].update({
            'peer_id': peer_id,
            'ip': ip,
            'porta': porta,
            'timestamp': time.time()
        })
        print(f"Peer adicionado/atualizado: {peer_id} ({ip}:{porta})")

    def remover_peer(self, peer_id):
        """Remove peer da lista de ativos."""
        if peer_id in self.peers_ativos:
            del self.peers_ativos[peer_id]
            print(f"Peer removido: {peer_id}")
        else:
            print(f"Peer {peer_id} não encontrado para remoção")

    def listar_peers_ativos(self):
        """Retorna uma lista de dicionários com todos os peers ativos."""
        return list(self.peers_ativos.values())

    def obter_peer(self, peer_id):
        """Retorna os dados de um peer específico, ou None se não existir."""
        return self.peers_ativos.get(peer_id, None)

    def total_peers(self):
        """Retorna o número total de peers ativos."""
        return len(self.peers_ativos)

    def limpar_peers_inativos(self, timeout=300):
        """Remove peers que estão inativos há mais de 'timeout' segundos."""
        tempo_atual = time.time()
        inativos = [
            peer_id for peer_id, dados in self.peers_ativos.items()
            if tempo_atual - dados['timestamp'] > timeout
        ]
        for peer_id in inativos:
            self.remover_peer(peer_id)
            print(f"Peer inativo removido: {peer_id}")

    def atualizar_timestamp(self, peer_id):
        """Atualiza o timestamp de um peer existente."""
        if peer_id in self.peers_ativos:
            self.peers_ativos[peer_id]['timestamp'] = time.time()

    def __str__(self):
        return f"GerenciadorPeers: {len(self.peers_ativos)} peers ativos"
