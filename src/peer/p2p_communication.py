import socket
import logging
from threading import Thread
import struct # Empacota/desempacota tamanhos de mensagens


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class P2PCommunication:
    # Antes da requisição de bloco enviamos um cabecalho
    # que é um número fixo de bytes (HEADER_LENGTH) que indica o tamanho da mensagem
    # que vira a seguir
    # O struct converte números inteiros em sequências de bytes e vice-versa
    # garantindo que o tamanho seja empacotado e desempacotado corretamente em ambos os lados paraevitar blocos imcompletos e erro de leitura

    # Comprimento da mensagem
    HEADER_LENGTH = 4

    @staticmethod
    def start_server(peer_node, port=5000):
        """Inicia o servidor para receber blocos e outras mensagens P2P."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
            s.bind(('0.0.0.0', port))
            s.listen()
            # Define um timeout para o accept() para que o loop possa checar se o peer está rodando
            s.settimeout(1.0) 
            logging.info(f"{peer_node.id} ouvindo em porta {port}")
            while peer_node.running:
                try:
                    conn, _ = s.accept() 
                    # Inicia uma nova thread para lidar com a conexão recebida
                    Thread(target=P2PCommunication.handle_connection, args=(conn, peer_node)).start()
                except socket.timeout:
                    # Nenhuma conexão em 1 segundo, verifica novamente se o peer está rodando
                    continue
                except Exception as e:
                    logging.error(f"Erro no accept do servidor {peer_node.id}: {e}")
                    break # Sai do loop em caso de erro inesperado
            logging.info(f"{peer_node.id} servidor encerrado.")


    @staticmethod
    def handle_connection(conn, peer_node):
        """Processa mensagens de outros peers."""
        try:
            # 1. Tenta receber o cabeçalho de 4 bytes que indica o tamanho da mensagem que virá.
            header_data = conn.recv(P2PCommunication.HEADER_LENGTH)
            if not header_data:
                logging.warning(f"{peer_node.id}: Conexão fechada pelo remoto ou dados vazios.")
                return

            # 2. Desempacota o tamanho da mensagem
            msg_length = struct.unpack('>I', header_data)[0] 

            # 3. Agora recebe a mensagem completa com base no tamanho lido
            full_data = b''
            bytes_received = 0
            while bytes_received < msg_length:
                # Recebe partes da mensagem até que todos os bytes esperados cheguem
                packet = conn.recv(msg_length - bytes_received)
                if not packet:
                    logging.error(f"{peer_node.id}: Conexão perdida enquanto recebia mensagem.")
                    return
                full_data += packet
                bytes_received += len(packet)
            
            data = full_data.decode('utf-8') # Decodifica a mensagem completa

            if data.startswith("REQUEST_BLOCK:"):
                try:
                    block_id = int(data.split(":")[1])
                except ValueError:
                    logging.warning(f"{peer_node.id} recebeu um ID inválido de bloco: {data}")
                    return

                logging.info(f"{peer_node.id} recebeu requisição por bloco: {block_id}")

                if block_id in peer_node.blocks:
                    bloco_data = peer_node.blocks[block_id] # Pega os dados brutos do bloco
                    if bloco_data is not None:
                        # Prepara a mensagem de resposta: cabeçalho de tamanho + dados do bloco
                        response_header = struct.pack('>I', len(bloco_data))
                        conn.sendall(response_header + bloco_data)
                        logging.info(f"{peer_node.id} enviou bloco {block_id} ({len(bloco_data)} bytes)")
                    else:
                        logging.warning(f"{peer_node.id} tem o bloco {block_id}, mas está vazio (None). Não enviou.")
                else:
                    logging.warning(f"{peer_node.id} não possui o bloco {block_id}. Não enviou.")

            else:
                logging.warning(f"{peer_node.id} recebeu mensagem desconhecida: {data}")

        except ConnectionResetError:
            logging.warning(f"{peer_node.id}: Conexão redefinida pelo peer remoto.")
        except struct.error:
            logging.error(f"{peer_node.id}: Erro ao desempacotar cabeçalho. Dados corrompidos ou incompletos.")
        except Exception as e:
            logging.error(f"Erro inesperado no handle_connection de {peer_node.id}: {e}", exc_info=True)
        finally:
            conn.close()


    @staticmethod
    def request_block(peer_address: tuple[str, int], block_id: int, timeout_s: float = 5.0):
        """Solicita um bloco de outro peer e retorna os dados do bloco."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s) # Define um timeout para a conexão e operações de socket.
            try:
                s.connect(peer_address)
                
                # Prepara a mensagem de requisição: primeiro o cabeçalho de tamanho, depois os dados.
                request_message = f"REQUEST_BLOCK:{block_id}".encode('utf-8')
                request_header = struct.pack('>I', len(request_message)) # Empacota o tamanho da mensagem.
                s.sendall(request_header + request_message) # Envia o cabeçalho e a mensagem.
                logging.info(f"Solicitando bloco {block_id} de {peer_address}")

                # Recebe a resposta do bloco 
                response_header = s.recv(P2PCommunication.HEADER_LENGTH)
                if not response_header:
                    logging.warning(f"Não recebeu cabeçalho de resposta para bloco {block_id} de {peer_address}. Peer pode ter fechado a conexão.")
                    return None

                # Desempacota o tamanho do bloco
                response_length = struct.unpack('>I', response_header)[0]

                # Recebe os dados do bloco em partes até completar o tamanho total
                block_data = b''
                bytes_received = 0
                while bytes_received < response_length:
                    packet = s.recv(response_length - bytes_received) # Recebe o restante dos bytes
                    if not packet:
                        logging.error(f"Conexão perdida enquanto recebia bloco {block_id} de {peer_address}.")
                        return None
                    block_data += packet
                    bytes_received += len(packet)

                logging.info(f"Recebeu {len(block_data)} bytes do bloco {block_id} de {peer_address}")
                return block_data

            except socket.timeout:
                logging.error(f"Timeout ao requisitar bloco {block_id} de {peer_address}.")
                return None
            except ConnectionRefusedError:
                logging.error(f"Conexão recusada por {peer_address} ao requisitar bloco {block_id}. Peer pode não estar ativo.")
                return None
            except Exception as e:
                logging.error(f"Erro inesperado ao requisitar bloco {block_id} de {peer_address}: {e}", exc_info=True)
                return None