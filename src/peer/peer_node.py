import logging
from threading import Thread
from .peer import p2p_communication
from .peer import file_manager

class PeerNode:
    def __init__(self, peer_id, tracker_url):
        self.id = peer_id
        self.tracker_url = tracker_url
        self.blocks = {}  # {block_name: data}
        self.peers = []   # Lista de peers conhecidos
        self.running = True
        self.file_manager = file_manager.FileManager()
        logging.basicConfig(level=logging.INFO)

    def start(self):
        """Inicia o peer (registro + servidor P2P)"""
        self._register_with_tracker()
        Thread(target=self._listen_for_peers).start()
        logging.info(f"Peer {self.id} iniciado!")

    def _register_with_tracker(self):
        """Registra peer no tracker e obtém blocos iniciais"""
        try:
            import requests
            response = requests.post(
                f"{self.tracker_url}/register",
                json={"peer_id": self.id, "blocks": list(self.blocks.keys())}
            )
            data = response.json()
            self.peers = data.get("peers", [])
            self._store_blocks(data.get("assigned_blocks", []))
        except Exception as e:
            logging.error(f"Falha ao registrar no tracker: {e}")

    def _listen_for_peers(self, port=5000):
        """Escuta conexões de outros peers"""
        p2p_communication.start_server(self, port)

    def _store_blocks(self, block_names):
        """Armazena blocos recebidos do tracker"""
        for block in block_names:
            if block not in self.blocks:
                self.blocks[block] = None  # Será baixado depois

    def shutdown(self):
        """Encerra o peer após verificar arquivo completo"""
        if self._check_file_complete():
            self.running = False
            logging.info("Peer encerrado corretamente!")
        else:
            logging.warning("Arquivo incompleto! Não pode encerrar.")

    def _check_file_complete(self):
        """Verifica se todos os blocos foram baixados"""
        return all(block_data is not None for block_data in self.blocks.values())