import argparse
from src.peer.peer_node import PeerNode

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="ID único do peer")
    parser.add_argument("--tracker", required=True, help="URL do tracker")
    parser.add_argument("--port", type=int, default=5000, help="Porta P2P")
    args = parser.parse_args()

    peer = PeerNode(args.id, args.tracker)
    peer.p2p.port = args.port
    peer.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nDesligando peer...")