import logging
import time
import threading
import random
import requests 
from threading import Thread
from src.peer.p2p_communication import P2PCommunication
from src.peer import file_manager


class ChokingManager:
    def __init__(self):
        self.prioritarios = set()  # Até 4 peers fixos
        self.otimista = None       # 1 peer sorteado por rodada

    def esta_peer_unchoked(self, peer_id):
        return peer_id in self.prioritarios or peer_id == self.otimista

    def rotacionar_peers(self, peers, mapa_blocos):
        if not peers:
            self.prioritarios = set()
            self.otimista = None
            return

        # Seleciona peers com mais blocos raros
        raridade = {}
        for peer in peers:
            peer_id = peer['peer_id']
            blocos = set(peer.get('blocks', []))
            score = sum(1 for b in blocos if self._bloco_raro(b, mapa_blocos))
            raridade[peer_id] = score

        ordenados = sorted(raridade.items(), key=lambda x: -x[1])
        self.prioritarios = set(p for p, _ in ordenados[:4])

        restantes = [p['peer_id'] for p in peers if p['peer_id'] not in self.prioritarios]
        self.otimista = random.choice(restantes) if restantes else None

    def _bloco_raro(self, bloco, mapa):
        contagem = sum(1 for blocos in mapa.values() if bloco in blocos)
        return contagem <= 2  # Define raro como blocos com no máximo 2 ocorrências


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
        self.choking_manager = ChokingManager()  # Gerenciador de choking/unchoking
        self.ultima_rotacao_peers = time.time()  # Marca a última vez que a lista de peers unchoked foi rotacionada

        # Configura o logging formatado com o ID do peer
        logging.basicConfig(
            level=logging.INFO,
            format=f"[{self.id}] %(asctime)s - %(levelname)s - %(message)s"
        )

    def start(self):
        self._register_with_tracker()
        Thread(target=self._listen_for_peers).start()
        self.iniciar_atualizacao_de_peers()
        self.atualizar_blocos_no_tracker()
        self.iniciar_download_de_blocos()
        logging.info(f"Peer iniciado e escutando na porta {self.my_port}")
        

    def _register_with_tracker(self):
        # Registra o peer no tracker enviando id, ip, porta e blocos que possui
        try:
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
            blocos_iniciais = random.sample(range(20), k=6)
            self._store_blocks(blocos_iniciais)
            logging.info(f"Registrado no tracker. Peers conhecidos: {len(self.peers)}")
            logging.info(f"Recebeu blocos iniciais: {blocos_iniciais}")

            blocos_possuidos = set(self.blocks.keys())
            blocos_faltando = sorted(self.todos_os_blocos - blocos_possuidos)
            logging.info(f"Blocos faltando: {blocos_faltando}")

        except Exception as e:
            logging.error(f"Falha ao registrar no tracker: {e}")

    def _listen_for_peers(self):
        # Chama a comunicação P2P para iniciar o servidor que aceita conexões de outros peers
        P2PCommunication.start_server(self, self.my_port)

    def _store_blocks(self, block_names):
        for block in block_names:
            if block not in self.blocks:
                self.blocks[block] = f"[{self.id}] Conteúdo do bloco {block}".encode()

    def _get_mapa_blocos_peers(self):
        return {peer['peer_id']: peer.get('blocks', []) for peer in self.peers}

    def escolher_bloco_mais_raro(self, meus_blocos, todos_os_blocos, mapa_blocos):
        faltando = todos_os_blocos - meus_blocos
        if not faltando:
            return None
        contagem = {b: 0 for b in faltando}
        for blocos in mapa_blocos.values():
            for bloco in blocos:
                if bloco in contagem:
                    contagem[bloco] += 1
        return min(contagem.items(), key=lambda x: x[1])[0]

    def _rotacionar_peers_unchoked(self):
        self.choking_manager.rotacionar_peers(self.peers, self._get_mapa_blocos_peers())
        logging.info(f"Peers prioritários unchoked: {self.choking_manager.prioritarios}")
        logging.info(f"Peer otimista unchoked: {self.choking_manager.otimista}")

    def iniciar_download_de_blocos(self):
        def _get_peer_com_bloco(bloco, mapa):
            # mapa é um dict peer_id -> lista de blocos
            peers_possuem_bloco = [peer_id for peer_id, blocos in mapa.items() if bloco in blocos]
            if not peers_possuem_bloco:
                return None
            peer_id_escolhido = random.choice(peers_possuem_bloco)
            for peer in self.peers:
                if peer['peer_id'] == peer_id_escolhido:
                    return peer
            return None
        
        def loop_de_download():
            while self.running:
                mapa = self._get_mapa_blocos_peers()
                bloco_alvo = self.escolher_bloco_mais_raro(set(self.blocks.keys()), self.todos_os_blocos, mapa)
                if bloco_alvo is None:
                    faltando = sorted(self.todos_os_blocos - set(self.blocks.keys()))
                    logging.info(f"🔄 Ainda faltando {len(faltando)} blocos: {faltando}")
                    time.sleep(5)
                    continue
                
                peer = _get_peer_com_bloco(bloco_alvo, mapa)
                if peer is None:
                    logging.info(f"Nenhum peer possui o bloco {bloco_alvo} no momento.")
                    time.sleep(2)
                    continue

                peer_id = peer['peer_id']
                if not self.choking_manager.esta_peer_unchoked(peer_id):
                    logging.info(f"Peer {peer_id} está choking, pulando...")
                    time.sleep(1)
                    continue

                endereco = (peer['ip'], peer['porta'])
                try:
                    dados = P2PCommunication.request_block(endereco, bloco_alvo)
                    if dados and bloco_alvo not in self.blocks:
                        self.blocks[bloco_alvo] = dados
                        logging.info(f"✅ [Rarest First] Baixou bloco raro {bloco_alvo} de {peer_id}")
                        faltando = sorted(self.todos_os_blocos - set(self.blocks.keys()))
                        logging.info(f"📦 Agora faltam {len(faltando)} blocos: {faltando}")
                except Exception as e:
                    logging.warning(f"Erro ao pedir bloco {bloco_alvo} de {peer_id}: {e}")

                if self._check_file_complete() and not hasattr(self, "_completo"):
                    logging.info("🎉 Arquivo completo! Agora atuando como seeder.")
                    self._completo = True

                # Rotaciona os peers unchoked a cada 10 segundos
                if time.time() - self.ultima_rotacao_peers >= 10:
                    self._rotacionar_peers_unchoked()
                    self.ultima_rotacao_peers = time.time()

                time.sleep(1)

        t = threading.Thread(target=loop_de_download)
        t.daemon = True
        t.start()

    def iniciar_atualizacao_de_peers(self):
        # Loop em thread para periodicamente atualizar a lista de peers no tracker
        def atualizador():
            while self.running:
                try:
                    resp = requests.get(f"{self.tracker_url}/listar_peers?peer_id={self.id}")
                    if resp.status_code == 200:
                        self.peers = resp.json().get("peers", [])
                except Exception as e:
                    logging.warning(f"Falha ao atualizar peers: {e}")
                time.sleep(10)  # Atualiza a cada 10 segundos

        t = threading.Thread(target=atualizador)
        t.daemon = True
        t.start()

    def _check_file_complete(self):
        # Verifica se todos os blocos necessários estão presentes e não são None
        return all(b in self.blocks and self.blocks[b] is not None for b in self.todos_os_blocos)


    def atualizar_blocos_no_tracker(self):
        def atualizador_blocos():
            while self.running:
                try:
                    requests.post(
                        f"{self.tracker_url}/atualizar_blocos",
                        json={
                            "peer_id": self.id,
                            "blocks": list(self.blocks.keys())
                        }
                    )
                except Exception as e:
                    logging.warning(f"Falha ao atualizar blocos no tracker: {e}")
                time.sleep(10)

        t = threading.Thread(target=atualizador_blocos)
        t.daemon = True
        t.start()


    def shutdown(self, force=False):
        # Para a execução, força shutdown mesmo se arquivo incompleto
        if self._check_file_complete() or force:
            self.running = False
            logging.info("Peer finalizado com sucesso.")
        else:
            logging.warning("Ainda faltam blocos. Use shutdown(force=True) para forçar.")

if __name__ == "__main__":
    import sys
    peer_id = sys.argv[1] if len(sys.argv) > 1 else "peer_default"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5001
    tracker_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5000"

    peer = PeerNode(peer_id, tracker_url, port)
    peer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        peer.shutdown(force=True)
