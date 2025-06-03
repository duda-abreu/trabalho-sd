import socket
import logging
from threading import Thread

class P2PCommunication:
    @staticmethod
    def start_server(peer_node, port=5000):
        """Inicia servidor para receber blocos"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
            s.listen()
            logging.info(f"Peer {peer_node.id} ouvindo em porta {port}")
            while peer_node.running:
                conn, addr = s.accept()
                Thread(target=P2PCommunication.handle_connection, args=(conn, peer_node)).start()

    @staticmethod
    def handle_connection(conn, peer_node):
        """Processa mensagens de outros peers"""
        try:
            data = conn.recv(1024).decode()
            if data.startswith("REQUEST_BLOCK:"):
                block_name = data.split(":")[1]
                if block_name in peer_node.blocks:
                    conn.send(peer_node.blocks[block_name])
        except Exception as e:
            logging.error(f"Erro na conexão: {e}")
        finally:
            conn.close()

    @staticmethod
    def request_block(peer_address, block_name):
        """Solicita bloco de outro peer"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(peer_address)
            s.send(f"REQUEST_BLOCK:{block_name}".encode())
            return s.recv(1024)  