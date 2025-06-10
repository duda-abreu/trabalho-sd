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
            logging.info(f"{peer_node.id} ouvindo em porta {port}")
            while peer_node.running:
                conn, addr = s.accept()
                Thread(target=P2PCommunication.handle_connection, args=(conn, peer_node)).start()

    @staticmethod
    def handle_connection(conn, peer_node):
        """Processa mensagens de outros peers"""
        try:
            data = conn.recv(1024).decode()
            if data.startswith("REQUEST_BLOCK:"):
                try:
                    block_id = int(data.split(":")[1])
                except ValueError:
                    logging.warning(f"{peer_node.id} recebeu um ID inválido de bloco: {data}")
                    conn.close()
                    return

                logging.info(f"{peer_node.id} recebeu requisição por bloco: {block_id}")

                if block_id in peer_node.blocks:
                    bloco = peer_node.blocks[block_id]
                    if bloco is not None:
                        conn.send(bloco)
                        logging.info(f"{peer_node.id} enviou bloco {block_id}")
                    else:
                        logging.warning(f"{peer_node.id} tem o bloco {block_id}, mas está vazio (None)")
                else:
                    logging.warning(f"{peer_node.id} não possui o bloco {block_id}")
        except Exception as e:
            logging.error(f"Erro na conexão: {e}")
        finally:
            conn.close()

    @staticmethod
    def request_block(peer_address, block_id):
        """Solicita bloco de outro peer"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(peer_address)
                s.send(f"REQUEST_BLOCK:{block_id}".encode())
                response = s.recv(1024)
                logging.info(f"Recebeu {len(response)} bytes do bloco {block_id} de {peer_address}")
                return response
            except Exception as e:
                logging.error(f"Erro ao conectar com peer {peer_address} para requisitar bloco {block_id}: {e}")
                return None
