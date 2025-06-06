import sys
import time
from src.peer.peer_node import PeerNode

def main():
    """
    funcao principal para configurar e iniciar um no peer.
    espera argumentos da linha de comando para definir o peer.
    """
    if len(sys.argv) != 5:
        print("uso correto: python run_peer.py <peer_id> <host> <porta> <url_do_tracker>")
        print("exemplo: python run_peer.py peer_1 127.0.0.1 8001 http://localhost:5000")
        sys.exit(1)

    peer_id = sys.argv[1]
    host = sys.argv[2]
    try:
        port = int(sys.argv[3])
    except ValueError:
        print("erro: a porta deve ser um numero inteiro.")
        sys.exit(1)
        
    tracker_url = sys.argv[4]

    print("=" * 50)
    print(f"      INICIANDO PEER: {peer_id}")
    print("=" * 50)
    print(f"ID do Peer: {peer_id}")
    print(f"Endereco P2P: {host}:{port}")
    print(f"URL do Tracker: {tracker_url}")
    print("-" * 50)

    peer = PeerNode(peer_id, host, port, tracker_url)
    peer.start()

    try:
        while peer.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\ninfo ({peer_id}): recebido sinal de encerramento (ctrl+c). iniciando shutdown...")
        peer.shutdown()
    
    print(f"info ({peer_id}): thread principal finalizada.")


if __name__ == "__main__":
    main()