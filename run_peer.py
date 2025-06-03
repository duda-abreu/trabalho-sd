from src.peer.peer_node import PeerNode

peer = PeerNode("peer1", "http://localhost:5000")
peer.start()

# Mantém o peer ativo
import time
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    peer.shutdown()