import time
from threading import Thread
from .p2p_communication import P2PCommunication
from .file_manager import FileManager

class PeerNode:
    def __init__(self, peer_id: str, tracker_url: str):
        self.id = peer_id
        self.tracker_url = tracker_url
        self.blocks = {} 
        self.peers = []   
        self.p2p = P2PCommunication(self)
        self.file_manager = FileManager()

    def start(self):
        """Inicia serviços do peer"""
        self._register_with_tracker()
        Thread(target=self.p2p.start_server, daemon=True).start()
        Thread(target=self._download_loop, daemon=True).start()

    def _register_with_tracker(self):
        """Registra peer e obtém lista inicial de blocos/peers"""
        import requests
        try:
            response = requests.post(
                f"{self.tracker_url}/register",
                json={
                    "peer_id": self.id,
                    "blocks": list(self.blocks.keys()),
                    "port": self.p2p.port
                }
            )
            data = response.json()
            self.peers = [tuple(p.split(":")) for p in data["peers"]]  
            self._store_blocks(data["assigned_blocks"])
        except Exception as e:
            logging.error(f"Falha no registro: {e}")

    def _download_loop(self):
        """Busca blocos faltantes periodicamente"""
        while True:
            missing_blocks = [b for b, data in self.blocks.items() if data is None]
            for block in missing_blocks:
                self._download_block(block)
            time.sleep(10)  

    def _download_block(self, block_name: str):
        """Tenta baixar bloco de peers disponíveis"""
        for peer in self.peers:
            if peer[0] != self.id:  
                data = self.p2p.request_block((peer[0], int(peer[1])), block_name)
                if data:
                    self._store_block(block_name, data)
                    break

    def _store_block(self, block_name: str, data: bytes):
        """Armazena bloco localmente"""
        self.blocks[block_name] = data
        self.file_manager.save_block(block_name, data)
        logging.info(f"Bloco {block_name} armazenado!")