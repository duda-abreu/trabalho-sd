import socket
import threading
import logging
from typing import Tuple

class P2PCommunication:
    def __init__(self, peer_node, port: int = 5000):
        self.peer_node = peer_node
        self.port = port
        self.running = True
        logging.basicConfig(level=logging.INFO)

    def start_server(self):
        """Inicia servidor TCP para receber conexões"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)  # Timeout para shutdown
            s.bind(('0.0.0.0', self.port))
            s.listen()
            logging.info(f"Peer {self.peer_node.id} ouvindo em {self.port}")
            
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(
                        target=self._handle_connection,
                        args=(conn, addr)
                    ).start()
                except socket.timeout:
                    continue

    def _handle_connection(self, conn, addr):
        """Processa mensagens recebidas"""
        try:
            data = conn.recv(1024).decode().strip()
            if data.startswith("REQUEST:"):
                block_name = data.split(":")[1]
                if block_name in self.peer_node.blocks:
                    conn.send(self.peer_node.blocks[block_name])
        except Exception as e:
            logging.error(f"Erro com {addr}: {e}")
        finally:
            conn.close()

    @staticmethod
    def request_block(peer_address: Tuple[str, int], block_name: str, timeout: int = 5) -> bytes:
        """Solicita bloco de outro peer com timeout"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            try:
                s.connect(peer_address)
                s.send(f"REQUEST:{block_name}".encode())
                return s.recv(1024)  
            except (socket.timeout, ConnectionRefusedError) as e:
                logging.warning(f"Falha ao buscar {block_name} de {peer_address}: {e}")
                return None