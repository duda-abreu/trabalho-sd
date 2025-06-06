import socket
import json
import logging
import time
from threading import Thread

BUFFER_SIZE = 4096

class P2PCommunicator:
    def __init__(self, peer_node):
        self.peer_node = peer_node
        self.host = self.peer_node.host
        self.port = self.peer_node.port
        self.server_thread = None
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def start_server(self):
        self.server_thread = Thread(target=self._listen_for_peers, daemon=True)
        self.server_thread.start()
        logging.info(f"[{self.peer_node.id}] Servidor P2P iniciado e ouvindo em {self.host}:{self.port}")

    def _listen_for_peers(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(10)
            while self.peer_node.running:
                try:
                    conn, addr = server_socket.accept()
                    handler_thread = Thread(target=self._handle_connection, args=(conn, addr), daemon=True)
                    handler_thread.start()
                except OSError:
                    break
        except Exception as e:
            logging.error(f"[{self.peer_node.id}] Erro critico no servidor P2P: {e}")
        finally:
            server_socket.close()
            logging.info(f"[{self.peer_node.id}] Servidor P2P encerrado.")

    def _handle_connection(self, conn: socket.socket, addr):
        try:
            header_data = b""
            while b"\n\n" not in header_data:
                chunk = conn.recv(BUFFER_SIZE)
                if not chunk: break
                header_data += chunk
            if not header_data: return
            header_str, _, extra_data = header_data.partition(b'\n\n')
            message = json.loads(header_str.decode())
            msg_type = message.get("type")
            payload = message.get("payload", {})
            requester_peer_id = message.get("peer_id")

            if msg_type == "REQUEST_BLOCK":
                block_id = payload.get("block_id")
                logging.info(f"[{self.peer_node.id}] Recebeu pedido do bloco {block_id} de {requester_peer_id}")
                self._handle_request_block(conn, requester_peer_id, block_id)
            elif msg_type == "ANNOUNCE_BLOCKS":
                blocks = set(payload.get("blocks", []))
                logging.info(f"[{self.peer_node.id}] {requester_peer_id} anunciou ter {len(blocks)} blocos.")
                self.peer_node.update_peer_block_map(requester_peer_id, blocks)
        except Exception as e:
            logging.error(f"[{self.peer_node.id}] Erro na conexao com {addr}: {e}")
        finally:
            conn.close()

    def _handle_request_block(self, conn: socket.socket, requester_peer_id: str, block_id: int):
        if not self.peer_node.choking_manager.esta_peer_unchoked(requester_peer_id):
            logging.warning(f"[{self.peer_node.id}] Pedido do bloco {block_id} negado para {requester_peer_id} (choked).")
            error_msg = self._criar_mensagem("ERROR", {"message": "choked"})
            conn.sendall(error_msg)
            return
        if self.peer_node.tem_bloco_completo(block_id):
            block_data = self.peer_node.get_block_data(block_id)
            header = self._criar_mensagem("SEND_BLOCK", {"block_id": block_id, "block_size": len(block_data)})
            conn.sendall(header)
            conn.sendall(block_data)
            logging.info(f"[{self.peer_node.id}] Enviou o bloco {block_id} para {requester_peer_id}.")
        else:
            error_msg = self._criar_mensagem("ERROR", {"message": "block not found"})
            conn.sendall(error_msg)
            
    def _criar_mensagem(self, msg_type: str, payload: dict) -> bytes:
        message = {"type": msg_type, "peer_id": self.peer_node.id, "payload": payload}
        return (json.dumps(message) + "\n\n").encode()

    def request_block(self, target_peer_info: dict, block_id: int) -> bytes | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((target_peer_info['ip'], target_peer_info['porta']))
                request_msg = self._criar_mensagem("REQUEST_BLOCK", {"block_id": block_id})
                s.sendall(request_msg)
                header_data = b""
                while b"\n\n" not in header_data:
                    chunk = s.recv(BUFFER_SIZE)
                    if not chunk: raise ConnectionError("Conexao fechada.")
                    header_data += chunk
                header_str, _, extra_data = header_data.partition(b'\n\n')
                response_msg = json.loads(header_str.decode())
                if response_msg.get("type") == "SEND_BLOCK":
                    block_size = response_msg["payload"]["block_size"]
                    block_data = extra_data
                    while len(block_data) < block_size:
                        chunk = s.recv(BUFFER_SIZE)
                        if not chunk: raise ConnectionError("Conexao fechada durante download.")
                        block_data += chunk
                    logging.info(f"[{self.peer_node.id}] Bloco {block_id} recebido de {target_peer_info['peer_id']}.")
                    return block_data
                else:
                    logging.warning(f"[{self.peer_node.id}] Erro ao pedir bloco {block_id}: {response_msg.get('payload', {}).get('message')}")
                    return None
        except Exception as e:
            logging.error(f"[{self.peer_node.id}] Falha ao pedir bloco {block_id} de {target_peer_info['peer_id']}: {e}")
            return None

    def announce_blocks(self, target_peer_info: dict):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((target_peer_info['ip'], target_peer_info['porta']))
                announcement_msg = self._criar_mensagem("ANNOUNCE_BLOCKS", {"blocks": list(self.peer_node.blocos_que_tenho)})
                s.sendall(announcement_msg)
        except Exception:
            pass