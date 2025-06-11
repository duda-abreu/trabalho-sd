import logging
import time
from threading import Thread, Lock
import requests
import random 

from src.peer.p2p_communication import P2PCommunication
from src.peer.file_manager import FileManager
from src.peer.strategies.choking_manager import ChokingManager
from src.peer.strategies.rarest_first import escolher_bloco_mais_raro
from src.peer.strategies.tit_for_tat_strategy import _calcular_pontuacao_de_raridade_do_peer 


class PeerNode:
    BLOCK_SIZE_BYTES = 16384 

    def __init__(self, peer_id, tracker_url, port, total_blocks=20, download_dir="downloads"):
        self.id = peer_id
        self.tracker_url = tracker_url
        self.blocks: dict[int, bytes] = {} 
        self.peers_info: dict[str, dict] = {} # Dicionário: peer_id -> {'ip': ..., 'porta': ..., 'blocks': set[int]}
        self.running = True
        self.my_port = port
        self.my_ip = "127.0.0.1"
        self.file_manager = FileManager()
        self.todos_os_blocos = set(range(total_blocks)) 
        self.total_blocks = total_blocks # Armazena o total de blocos para referência

        self.choking_manager = ChokingManager(self.id)
        
        # Lock para proteger self.blocks e self.peers_info de acessos concorrentes por threads
        self.data_lock = Lock() 

        self._completo = False 

        logging.basicConfig(
            level=logging.INFO,
            format=f"[{self.id}] %(asctime)s - %(levelname)s - %(message)s"
        )
        logging.info(f"PeerNode {self.id} inicializado na porta {self.my_port}")

    def start(self):
        # Inicia o servidor P2P em uma thread separada
        Thread(target=P2PCommunication.start_server, args=(self, self.my_port), daemon=True).start()
        logging.info(f"Servidor P2P do Peer {self.id} iniciado.")

        self._register_with_tracker()

        # Inicia loops de background em threads separadas
        # e incorpora a lógica de raridade
        Thread(target=self._download_loop, daemon=True).start()
        Thread(target=self._update_peers_from_tracker_loop, daemon=True).start()
        # O loop de choking/unchoking para olho por olho
        Thread(target=self._choking_unchoking_loop, daemon=True).start()

        logging.info(f"Peer {self.id} operacional.")

    def _register_with_tracker(self):
        """Registra-se no tracker e obtém blocos iniciais e peers."""
        try:
            with self.data_lock:
                my_blocks_list = list(self.blocks.keys())

            response = requests.post(
                f"{self.tracker_url}/registrar_peer",
                json={
                    "peer_id": self.id,
                    "ip": self.my_ip,
                    "porta": self.my_port,
                    "blocks": my_blocks_list
                }
            )
            response.raise_for_status()
            data = response.json()
            
            new_peers_data = data.get("peers", [])
            with self.data_lock:
                self.peers_info.clear()
                for p_data in new_peers_data:
                    self.peers_info[p_data['peer_id']] = p_data
                    self.choking_manager.peer_entrou_na_rede(p_data['peer_id'])

            blocos_iniciais = data.get("blocos_iniciais", [])
            self._store_blocks(blocos_iniciais)

            logging.info(f"Registrado no tracker. Peers conhecidos ({len(self.peers_info)}): {list(self.peers_info.keys())}")
            logging.info(f"Recebeu {len(blocos_iniciais)} blocos iniciais.")

            if self.peers_info:
                peers_list_for_log = []
                for peer_id, info in self.peers_info.items():
                    peers_list_for_log.append(
                        f"{peer_id} ({info.get('ip', 'N/A')}:{info.get('porta', 'N/A')}) - Blocos: {sorted(list(info.get('blocks', set())))}"
                    )
                logging.info(f"Detalhes dos peers conhecidos após registro: {'; '.join(peers_list_for_log)}")
            else:
                logging.info("Nenhum outro peer conhecido no momento do registro.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Falha ao registrar no tracker (conexão/HTTP): {e}")
        except Exception as e:
            logging.error(f"Erro inesperado ao registrar no tracker: {e}", exc_info=True)


    def _listen_for_peers(self):
        P2PCommunication.start_server(self, self.my_port)

    def _store_blocks(self, block_ids: list[int], data: bytes = None):
        """
        Armazena blocos no PeerNode.
        Se 'data' for fornecido, é o conteúdo do bloco. Caso contrário, gera conteúdo fictício.
        """
        with self.data_lock: # Protege o acesso a self.blocks
            for block_id in block_ids:
                if block_id not in self.blocks:
                    if data:
                        self.blocks[block_id] = data
                    else: # Se não tem dados, é um bloco inicial gerado pelo tracker
                        self.blocks[block_id] = f"[{self.id}] Conteúdo do bloco {block_id}".encode('utf-8')
                    logging.debug(f"Bloco {block_id} adicionado ao meu inventário.")


    def _download_loop(self):
        """Loop principal para solicitar e baixar blocos."""
        while self.running:
            time.sleep(1)
            
            if self._check_file_complete():
                if not self._completo:
                    logging.info("🎉 Arquivo completo! Agora atuando como seeder.")
                    self._completo = True
                continue 
            else:
                self._completo = False 


            with self.data_lock:
                my_current_blocks = set(self.blocks.keys())
                

                blocos_faltantes = self.todos_os_blocos - my_current_blocks
                if blocos_faltantes: # Só loga se houver blocos faltando
                    logging.info(f"Estado dos blocos: Possui {len(my_current_blocks)} de {self.total_blocks}. Faltam: {sorted(list(blocos_faltantes))}")

                peers_map_for_rarity = {
                    pid: p_data['blocks'] 
                    for pid, p_data in self.peers_info.items() 
                    if pid != self.id 
                }
                
                # Rarest First
                block_to_request = escolher_bloco_mais_raro(
                    meus_blocos=my_current_blocks,
                    todos_os_blocos_do_arquivo=self.todos_os_blocos,
                    mapa_de_blocos_dos_peers=peers_map_for_rarity
                )

            if block_to_request is None:
                continue

            peers_with_block = []
            with self.data_lock: 
                for peer_id, peer_data in self.peers_info.items():
                    if peer_id == self.id: # Não tentar baixar de si mesmo
                        continue
                    if block_to_request in peer_data.get('blocks', set()):
                        peers_with_block.append(peer_data)
            
            if not peers_with_block:
                logging.warning(f"Bloco {block_to_request} identificado como raro, mas nenhum peer conhecido o possui.")
                continue

            # Embaralha para distribuir as requisições, mesmo que o primeiro da lista sempre tenha o bloco
            random.shuffle(peers_with_block) 

            downloaded = False
            for peer_data in peers_with_block:
                peer_address = (peer_data['ip'], peer_data['porta'])
                logging.info(f"Tentando baixar bloco {block_to_request} de {peer_data['peer_id']} ({peer_address}).")
                
                downloaded_data = P2PCommunication.request_block(peer_address, block_to_request)
                
                if downloaded_data:
                    self._store_blocks([block_to_request], downloaded_data)
                    logging.info(f"✅ Baixou bloco {block_to_request} ({len(downloaded_data)} bytes) de {peer_data['peer_id']}.")
                    downloaded = True
                    break # Passa para o próximo ciclo de download
                else:
                    logging.warning(f"Falha ao baixar bloco {block_to_request} de {peer_data['peer_id']}. Tentando próximo peer.")
            
            if not downloaded:
                logging.warning(f"Não foi possível baixar o bloco {block_to_request} de nenhum peer conhecido nesta rodada.")


    def _update_peers_from_tracker_loop(self):
        """Loop para periodicamente atualizar a lista de peers do tracker."""
        while self.running:
            time.sleep(15) 
            try:
                with self.data_lock:
                    my_blocks_list = list(self.blocks.keys())

                resp = requests.get(
                    f"{self.tracker_url}/listar_peers?peer_id={self.id}",
                    json={"blocks": my_blocks_list} # Envia blocos junto com a requisição de peers
                )
                resp.raise_for_status()
                data = resp.json()
                
                new_peers_data = data.get("peers", [])
                
                with self.data_lock: 
                    # Identifica peers que saíram para informar ao choking manager
                    current_peer_ids = set(self.peers_info.keys())
                    updated_peer_ids = {p_data['peer_id'] for p_data in new_peers_data}
                    
                    peers_removed = current_peer_ids - updated_peer_ids
                    for removed_peer_id in peers_removed:
                        logging.info(f"Peer {removed_peer_id} saiu da rede.")
                        self.choking_manager.peer_saiu_da_rede(removed_peer_id)
                        self.peers_info.pop(removed_peer_id, None)

                    # Atualiza/adiciona peers e informa ao choking manager sobre novos peers
                    for p_data in new_peers_data:
                        if p_data['peer_id'] != self.id: # Não adiciona a si mesmo como peer
                            self.peers_info[p_data['peer_id']] = p_data
                            self.choking_manager.peer_entrou_na_rede(p_data['peer_id'])
                

            except requests.exceptions.RequestException as e:
                logging.warning(f"Falha ao atualizar peers do tracker (conexão/HTTP): {e}")
            except Exception as e:
                logging.error(f"Erro inesperado no loop de atualização de peers: {e}", exc_info=True)


    def _choking_unchoking_loop(self):
        """Loop para executar o ciclo de choking/unchoking a cada 10 segundos."""
        while self.running:
            time.sleep(10) 

            with self.data_lock:
                # Passa o mapa de blocos dos peers (excluindo a si mesmo) e os blocos que este peer possui.
                
                mapa_de_blocos_para_choking = {
                    pid: p_data['blocks'] 
                    for pid, p_data in self.peers_info.items() 
                    if 'blocks' in p_data # Garante que a chave 'blocks' existe
                }
                
                current_timestamp = time.time()
                self.choking_manager.executar_ciclo_unchoking(
                    timestamp_atual=current_timestamp,
                    mapa_de_blocos_global=mapa_de_blocos_para_choking,
                    meus_blocos=set(self.blocks.keys()),
                    todos_os_blocos_do_arquivo=self.todos_os_blocos
                )


    def _check_file_complete(self) -> bool:
        """Verifica se o peer possui todos os blocos do arquivo."""
        with self.data_lock:
            return self.todos_os_blocos.issubset(self.blocks.keys())


    def shutdown(self):
        """Encerra o peer de forma controlada."""
        logging.info("Iniciando desligamento do peer...")
        
        # O sistema deve permitir que um peer se desligue somente após reconstruir o arquivo completo
        if not self._check_file_complete():
            logging.warning("Arquivo incompleto. Não foi possível desligar o peer agora.")

        self.running = False # Sinaliza para todas as threads de loop pararem
        time.sleep(2) 
        
        logging.info(f"Peer {self.id} finalizado com sucesso.")


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Peer para o sistema BitTorrent simplificado.")
    parser.add_argument("--id", type=str, required=True, help="ID único do peer (e.g., 'peer1')")
    parser.add_argument("--port", type=int, default=5001, help="Porta para o peer escutar conexões P2P (default: 5001)")
    parser.add_argument("--tracker_url", type=str, default="http://127.0.0.1:5000", help="URL base do tracker (default: http://127.0.0.1:5000)")
    parser.add_argument("--total_blocks", type=int, default=20, help="Número total de blocos do arquivo (default: 20)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    peer = PeerNode(
        peer_id=args.id,
        tracker_url=args.tracker_url,
        port=args.port,
        total_blocks=args.total_blocks
    )
    peer.start()

    try:
        while peer.running:
            time.sleep(1)
            # Verifica se o arquivo está completo para logar ou desligar
            if peer._check_file_complete() and peer._completo:
                # Se o arquivo estiver completo, o peer continua a seedar
                pass 
            
    except KeyboardInterrupt:
        logging.info("Ctrl+C detectado. Iniciando desligamento do peer...")
        peer.shutdown()
    except Exception as e:
        logging.critical(f"Erro fatal no loop principal do peer: {e}", exc_info=True)
        peer.shutdown()