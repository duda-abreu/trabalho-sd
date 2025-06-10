import logging
from threading import Thread
from src.peer.p2p_communication import P2PCommunication
from src.peer import file_manager

class PeerNode:
    def __init__(self, peer_id, tracker_url, port):
        self.id = peer_id
        self.tracker_url = tracker_url
        self.blocks = {}
        self.peers = []
        self.running = True
        self.my_port = port
        self.file_manager = file_manager.FileManager()
        self.todos_os_blocos = set(range(20))

        logging.basicConfig(
            level=logging.INFO,
            format=f"[{self.id}] %(asctime)s - %(levelname)s - %(message)s"
        )

    def start(self):
        self._register_with_tracker()
        Thread(target=self._listen_for_peers).start()
        logging.info(f"Peer iniciado e escutando na porta {self.my_port}")
        self.iniciar_download_de_blocos()
        self.iniciar_atualizacao_de_peers()

    def _register_with_tracker(self):
        try:
            import requests
            response = requests.post(
                f"{self.tracker_url}/registrar_peer",
                json={
                    "peer_id": self.id,
                    "ip": "127.0.0.1",
                    "porta": self.my_port,
                    "blocks": list(self.blocks.keys())
                }
            )
            data = response.json()
            self.peers = data.get("peers", [])
            blocos_iniciais = data.get("blocos_iniciais", [])

            self._store_blocks(blocos_iniciais)
            logging.info(f"Registrado no tracker. Peers conhecidos: {len(self.peers)}")
            logging.info(f"Recebeu blocos iniciais: {blocos_iniciais}")
        except Exception as e:
            logging.error(f"Falha ao registrar no tracker: {e}")

    def _listen_for_peers(self):
        P2PCommunication.start_server(self, self.my_port)

    def _store_blocks(self, block_names):
        for block in block_names:
            if block not in self.blocks:
                self.blocks[block] = f"[{self.id}] Conteúdo do bloco {block}".encode()

    def iniciar_download_de_blocos(self):
        import threading
        def loop_de_download():
            import time
            while self.running:
                faltando = [b for b in self.todos_os_blocos if b not in self.blocks or self.blocks[b] is None]
                if faltando:
                    logging.info(f"Faltando {len(faltando)} blocos: {faltando}")
                for bloco in faltando:
                    for peer in self.peers:
                        endereco = (peer['ip'], peer['porta'])
                        try:
                            dados = P2PCommunication.request_block(endereco, bloco)
                            if dados:
                                self.blocks[bloco] = dados
                                logging.info(f"✅ Baixou bloco {bloco} de {peer['peer_id']}")
                                break
                        except Exception as e:
                            logging.warning(f"Erro ao pedir bloco {bloco} de {peer['peer_id']}: {e}")
                if self._check_file_complete():
                    if not hasattr(self, "_completo"):
                        logging.info("🎉 Arquivo completo! Agora atuando como seeder.")
                        self._completo = True
                time.sleep(5)
        t = threading.Thread(target=loop_de_download)
        t.daemon = True
        t.start()

    def iniciar_atualizacao_de_peers(self):
        import threading
        import requests
        def atualizador():
            import time
            while self.running:
                try:
                    resp = requests.get(f"{self.tracker_url}/listar_peers?peer_id={self.id}")
                    if resp.status_code == 200:
                        self.peers = resp.json().get("peers", [])
                except Exception as e:
                    logging.warning(f"Falha ao atualizar peers: {e}")
                time.sleep(10)
        t = threading.Thread(target=atualizador)
        t.daemon = True
        t.start()

    def _check_file_complete(self):
        return all(b in self.blocks and self.blocks[b] is not None for b in self.todos_os_blocos)

    def shutdown(self):
        self.running = False
        logging.info("Peer finalizado com sucesso.")

if __name__ == "__main__":
    import sys
    import time

    peer_id = sys.argv[1] if len(sys.argv) > 1 else "peer_default"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001
    tracker_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5000"

    peer = PeerNode(peer_id, tracker_url, port)
    peer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        peer.shutdown()
