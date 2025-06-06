import logging
import time
import random
from threading import Thread, RLock
import requests
from .p2p_communication import P2PCommunicator
from .file_manager import FileManager
from .strategies.choking_manager import ChokingManager
from .strategies import rarest_first

INTERVALO_ATUALIZAR_PEERS_S = 60
INTERVALO_DOWNLOAD_S = 5
INTERVALO_ANUNCIAR_S = 30

class PeerNode:
    def __init__(self, peer_id: str, host: str, port: int, tracker_url: str, total_blocos_arquivo: int = 20):
        self.id = peer_id
        self.host = host
        self.port = port
        self.tracker_url = tracker_url
        self.total_blocos_arquivo = total_blocos_arquivo
        self.running = True
        self.blocos_que_tenho: set[int] = set()
        self.dados_dos_blocos: dict[int, bytes] = {}
        self.peers_conhecidos: dict[str, dict] = {}
        self.mapa_de_blocos_global: dict[str, set[int]] = {}
        self.lock = RLock()
        self.file_manager = FileManager()
        self.communicator = P2PCommunicator(self)
        self.choking_manager = ChokingManager(self.id)
        logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - [{self.id}] - %(levelname)s - %(message)s')

    def start(self):
        logging.info("Peer iniciando...")
        if not self._register_with_tracker():
            self.shutdown()
            return
        self.communicator.start_server()
        self.logic_thread = Thread(target=self.run, daemon=True)
        self.logic_thread.start()
        logging.info("Peer totalmente operacional.")

    def run(self):
        last_peer_update = 0
        last_announce = 0
        while self.running:
            try:
                ts = time.time()
                if ts - last_peer_update > INTERVALO_ATUALIZAR_PEERS_S:
                    self._update_peers_from_tracker()
                    last_peer_update = ts
                if ts - last_announce > INTERVALO_ANUNCIAR_S:
                    self._announce_to_peers()
                    last_announce = ts
                self.choking_manager.executar_ciclo_unchoking(
                    ts, self.mapa_de_blocos_global, self.blocos_que_tenho, self._get_todos_blocos_set()
                )
                if not self.tem_arquivo_completo():
                    self._tentar_baixar_bloco()
                else:
                    logging.info("Arquivo completo! Apenas servindo...")
                    self._reconstruir_e_encerrar()
                    break
                time.sleep(INTERVALO_DOWNLOAD_S)
            except Exception as e:
                logging.error(f"Erro no loop principal: {e}")
                time.sleep(5)

    def shutdown(self):
        if self.running:
            logging.info("Encerrando o peer...")
            self.running = False
            self._disconnect_from_tracker()
            logging.info("Peer encerrado.")

    def _register_with_tracker(self) -> bool:
        try:
            logging.info(f"Registrando no tracker em {self.tracker_url}...")
            response = requests.post(f"{self.tracker_url}/registrar_peer", json={"peer_id": self.id, "ip": self.host, "porta": self.port}, timeout=5)
            response.raise_for_status()
            data = response.json()
            with self.lock:
                self.blocos_que_tenho = set(data.get("blocos_iniciais", []))
            logging.info(f"Registrado! Recebi {len(self.blocos_que_tenho)} blocos iniciais.")
            self._simular_dados_blocos_iniciais()
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Falha ao registrar no tracker: {e}")
            return False

    def _update_peers_from_tracker(self):
        try:
            response = requests.get(f"{self.tracker_url}/listar_peers", params={"peer_id": self.id}, timeout=5)
            response.raise_for_status()
            peers = response.json().get("peers", [])
            with self.lock:
                self.peers_conhecidos = {p['peer_id']: p for p in peers}
                self.choking_manager.peers_conhecidos = set(self.peers_conhecidos.keys())
            logging.info(f"Lista de peers atualizada. {len(self.peers_conhecidos)} peers conhecidos.")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Nao foi possivel atualizar a lista de peers: {e}")

    def _disconnect_from_tracker(self):
        try:
            requests.post(f"{self.tracker_url}/desconectar_peer", json={"peer_id": self.id}, timeout=3)
            logging.info("Notificacao de desconexao enviada ao tracker.")
        except requests.exceptions.RequestException: pass

    def _tentar_baixar_bloco(self):
        with self.lock:
            bloco_id_alvo = rarest_first.escolher_bloco_mais_raro(self.blocos_que_tenho, self._get_todos_blocos_set(), self.mapa_de_blocos_global)
        if bloco_id_alvo is None:
            logging.info("Nenhum bloco necessario disponivel para download.")
            return
        peers_com_bloco = [pid for pid, blocos in self.mapa_de_blocos_global.items() if bloco_id_alvo in blocos]
        random.shuffle(peers_com_bloco)
        for peer_id in peers_com_bloco:
            if peer_id in self.peers_conhecidos:
                logging.info(f"Tentando baixar bloco {bloco_id_alvo} do peer {peer_id}...")
                dados_recebidos = self.communicator.request_block(self.peers_conhecidos[peer_id], bloco_id_alvo)
                if dados_recebidos:
                    self.armazenar_bloco_recebido(bloco_id_alvo, dados_recebidos)
                    self._announce_to_peers()
                    return

    def _announce_to_peers(self):
        with self.lock:
            peers_para_anunciar = random.sample(list(self.peers_conhecidos.values()), min(len(self.peers_conhecidos), 5))
        logging.info(f"Anunciando meus {len(self.blocos_que_tenho)} blocos para {len(peers_para_anunciar)} peers...")
        for peer_info in peers_para_anunciar:
            self.communicator.announce_blocks(peer_info)

    def _reconstruir_e_encerrar(self):
        logging.info("Todos os blocos baixados! Reconstruindo o arquivo final...")
        with self.lock:
            blocos_ordenados = sorted(self.dados_dos_blocos.keys())
            dados_completos = b"".join(self.dados_dos_blocos[i] for i in blocos_ordenados)
        self.file_manager.save_block(f"arquivo_final_{self.id}.txt", dados_completos)
        logging.info(f"Arquivo final 'arquivo_final_{self.id}.txt' salvo!")
        self.shutdown()

    def tem_arquivo_completo(self) -> bool:
        with self.lock: return len(self.blocos_que_tenho) == self.total_blocos_arquivo
    def tem_bloco_completo(self, block_id: int) -> bool:
        with self.lock: return block_id in self.dados_dos_blocos and self.dados_dos_blocos[block_id] is not None
    def get_block_data(self, block_id: int) -> bytes | None:
        with self.lock: return self.dados_dos_blocos.get(block_id)
    def update_peer_block_map(self, peer_id: str, blocos: set[int]):
        with self.lock:
            self.mapa_de_blocos_global[peer_id] = blocos
            if peer_id not in self.peers_conhecidos:
                self.choking_manager.peer_entrou_na_rede(peer_id)
    def armazenar_bloco_recebido(self, block_id: int, data: bytes):
        with self.lock:
            if block_id not in self.blocos_que_tenho:
                self.blocos_que_tenho.add(block_id)
                self.dados_dos_blocos[block_id] = data
                self.file_manager.save_block(f"bloco_{self.id}_{block_id}.dat", data)
                logging.info(f"Sucesso! Baixei o bloco {block_id}. Total: {len(self.blocos_que_tenho)}/{self.total_blocos_arquivo}")
    def _get_todos_blocos_set(self) -> set[int]:
        return set(range(self.total_blocos_arquivo))
    def _simular_dados_blocos_iniciais(self):
        for block_id in self.blocos_que_tenho:
            if not self.tem_bloco_completo(block_id):
                dados_simulados = f"dados do bloco #{block_id}".encode('utf-8')
                self.dados_dos_blocos[block_id] = dados_simulados
                self.file_manager.save_block(f"bloco_{self.id}_{block_id}.dat", dados_simulados)