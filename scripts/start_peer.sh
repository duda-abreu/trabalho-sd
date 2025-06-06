#!/bin/bash
#
# este script inicia um no peer com um id e uma porta p2p aleatorios.
#

# --- configuracoes ---
HOST="127.0.0.1"
TRACKER_URL="http://localhost:5000"
PORTA_BASE=8001 

# --- geracao de dados unicos para o peer ---
PEER_ID="peer_$RANDOM"
OFFSET_PORTA_ALEATORIA=$(($RANDOM % 1000))
PEER_PORTA=$(($PORTA_BASE + $OFFSET_PORTA_ALEATORIA))

# --- execucao ---
echo "=============================================="
echo "Tentando iniciar um novo Peer..."
echo "  ID Gerado:    $PEER_ID"
echo "  Host P2P:     $HOST"
echo "  Porta P2P:    $PEER_PORTA"
echo "  Tracker URL:  $TRACKER_URL"
echo "=============================================="

cd "$(dirname "$0")/.."

# executa o script principal do peer passando os argumentos na ordem correta
python3 run_peer.py "$PEER_ID" "$HOST" "$PEER_PORTA" "$TRACKER_URL"