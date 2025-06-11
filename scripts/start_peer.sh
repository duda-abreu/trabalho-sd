#!/bin/bash
python3 -m src.peer.peer_node "peer_$RANDOM" 5001 "http://localhost:5000"
# Garantindo a porta pra que o peer sempre use a 5001 ao iniciar