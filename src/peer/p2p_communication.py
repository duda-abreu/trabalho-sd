import socket
import logging
from threading import Thread

class P2PCommunication:
    @staticmethod
    def start_server(peer_node, port=5000):
        """
        Inicia o servidor para receber conexões e pedidos de blocos de outros peers.
        O servidor fica ouvindo na porta especificada e cria uma thread para cada conexão recebida.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # bind: associa o socket ao endereço IP e porta especificados ('0.0.0.0' significa todas as interfaces)
            s.bind(('0.0.0.0', port))
            # começa a escutar conexões
            s.listen()
            logging.info(f"{peer_node.id} ouvindo em porta {port}")

            # enquanto o peer está rodando, aceita conexões
            while peer_node.running:
                # aceita uma conexão, retorna socket para comunicação (conn) e endereço do cliente (addr)
                conn, addr = s.accept()
                # cria uma nova thread para tratar essa conexão para não bloquear a thread principal
                Thread(target=P2PCommunication.handle_connection, args=(conn, peer_node)).start()

    @staticmethod
    def handle_connection(conn, peer_node):
        """
        Trata a comunicação com um peer conectado.
        Recebe mensagens, interpreta e responde apropriadamente.
        """
        try:
            # recebe dados do peer conectado (buffer de 1024 bytes) e decodifica para string
            data = conn.recv(1024).decode()
            # verifica se a mensagem é uma requisição de bloco
            if data.startswith("REQUEST_BLOCK:"):
                try:
                    # extrai o ID do bloco solicitado, convertendo para inteiro
                    block_id = int(data.split(":")[1])
                except ValueError:
                    # se não for um número válido, registra alerta e fecha conexão
                    logging.warning(f"{peer_node.id} recebeu um ID inválido de bloco: {data}")
                    conn.close()
                    return

                logging.info(f"{peer_node.id} recebeu requisição por bloco: {block_id}")

                # verifica se o peer tem o bloco solicitado
                if block_id in peer_node.blocks:
                    bloco = peer_node.blocks[block_id]
                    # se o bloco não for None, envia o conteúdo
                    if bloco is not None:
                        conn.send(bloco)
                        logging.info(f"{peer_node.id} enviou bloco {block_id}")
                    else:
                        # caso o bloco seja None, registra alerta (block vazio)
                        logging.warning(f"{peer_node.id} tem o bloco {block_id}, mas está vazio (None)")
                else:
                    # se o bloco não existe, registra alerta
                    logging.warning(f"{peer_node.id} não possui o bloco {block_id}")
        except Exception as e:
            # captura exceções inesperadas na conexão e registra erro
            logging.error(f"Erro na conexão: {e}")
        finally:
            # garante que a conexão será fechada após o tratamento
            conn.close()

    @staticmethod
    def request_block(peer_address, block_id):
        """
        Solicita um bloco específico de outro peer.
        Conecta no endereço do peer e envia a requisição, aguardando a resposta.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # conecta no peer destino (ip, porta)
                s.connect(peer_address)
                # envia mensagem de requisição do bloco com formato 'REQUEST_BLOCK:<id>'
                s.send(f"REQUEST_BLOCK:{block_id}".encode())
                # recebe resposta (bloco) do peer
                response = s.recv(1024)
                logging.info(f"Recebeu {len(response)} bytes do bloco {block_id} de {peer_address}")
                return response
            except Exception as e:
                # caso falhe a conexão ou envio, registra erro e retorna None
                logging.error(f"Erro ao conectar com peer {peer_address} para requisitar bloco {block_id}: {e}")
                return None
