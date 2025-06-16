import logging

import time
import logging 
from typing import Optional, Set, List, Dict
from . import tit_for_tat_strategy
from . import rarest_first 

class ChokingManager:
    """
    gerencia a logica de choking/unchoking do peer, aplicando a estrategia de
    'olho por olho' simplificada.

    ele decide para quais peers o nosso peer vai permitir o envio de blocos (unchoke)
    e para quais vai bloquear (choke). a ideia eh priorizar quem pode nos
    oferecer blocos raros e tambem explorar novos peers de vez em quando.
    """
    def __init__(self, meu_peer_id: str, max_fixos_unchoked: int = 4, intervalo_optimistic_s: int = 10):
        self.meu_peer_id = meu_peer_id 
        self.max_fixos_unchoked = max_fixos_unchoked 
        self.intervalo_optimistic_s = intervalo_optimistic_s 

        self.peers_conhecidos: set[str] = set() 
        
        self.peers_fixos_unchoked: list[str] = [] 
        self.peer_optimistic_unchoked: str | None = None
        
        self.ultimo_timestamp_optimistic: float = 0.0 # para o primeiro ciclo rodar logo

        # print(f"info: ChokingManager para {meu_peer_id} iniciado.")

    def peer_entrou_na_rede(self, peer_id: str):
        """metodo chamado quando descobrimos um novo peer"""
        if peer_id != self.meu_peer_id:
            self.peers_conhecidos.add(peer_id)
            # print(f"info ({self.meu_peer_id}): novo peer conhecido {peer_id}. total: {len(self.peers_conhecidos)}")

    def peer_saiu_da_rede(self, peer_id: str):
        """metodo chamado quando um peer se desconecta ou sai"""
        self.peers_conhecidos.discard(peer_id) # discard nao da erro se o item nao existir
        
        if peer_id in self.peers_fixos_unchoked:
            try:
                self.peers_fixos_unchoked.remove(peer_id)
            except ValueError:
                # pode acontecer se a lista for modificada em outro lugar, embora improvavel aqui
                pass # apenas ignora se ja foi removido
        
        if self.peer_optimistic_unchoked == peer_id:
            self.peer_optimistic_unchoked = None
        # print(f"info ({self.meu_peer_id}): peer {peer_id} removido das listas de choking.")

    def _pode_fazer_optimistic_unchoke(self, timestamp_atual: float) -> bool:
        """verifica se ja passou tempo suficiente para um novo unchoke otimista"""
        # renomeado para _pode_fazer... para indicar uso interno
        return (timestamp_atual - self.ultimo_timestamp_optimistic) >= self.intervalo_optimistic_s

    def executar_ciclo_unchoking(self, timestamp_atual: float, 
                                 mapa_de_blocos_global: Dict[str, Set[int]], 
                                 meus_blocos: Set[int], 
                                 todos_os_blocos_do_arquivo: Set[int]):
        
        

        if self._pode_fazer_optimistic_unchoke(timestamp_atual):
            self.ultimo_timestamp_optimistic = timestamp_atual
            # delegar a escolha do peer aleatorio para o 'optimistic unchoke'
            # para o modulo tit_for_tat_strategy
            # de acordo com o pdf: "A cada intervalo de 10 segundos, cada peer deve desbloquear (unchoke) um novo peer aleatório entre os que conhece" 
            novo_candidato_optimistic = tit_for_tat_strategy.selecionar_candidato_optimistic_aleatorio(
                peers_conhecidos=self.peers_conhecidos,
                peers_fixos_unchoked=set(self.peers_fixos_unchoked), # passar como set para busca rapida
                peer_optimistic_atual=self.peer_optimistic_unchoked,
                meu_peer_id=self.meu_peer_id
            )
            # print(f"info ({self.meu_peer_id}): candidato optimistic escolhido por tit_for_tat: {novo_candidato_optimistic}")
        else:
            # se nao eh hora de escolher um novo otimista, o candidato eh o otimista atual (se houver)
            # para que ele possa ser reavaliado para promocao junto com os fixos
            novo_candidato_optimistic = self.peer_optimistic_unchoked


        # agora, delegar a avaliacao e atualizacao das listas de unchoked (fixos e otimista final)
        # para o modulo tit_for_tat_strategy.
        # esta funcao contera a logica de "Se esse novo peer possuir blocos considerados raros (...), ele poderá ser promovido" 
        # e "A decisão de manter um peer na lista é baseada em quantos blocos raros ele possui em relação aos outros." 
        
        novos_fixos, novo_optimistic_final = tit_for_tat_strategy.avaliar_e_atualizar_listas_unchoked(
            peers_fixos_atuais=list(self.peers_fixos_unchoked), # envia uma copia da lista atual
            peer_candidato_para_avaliacao=novo_candidato_optimistic, # pode ser o novo aleatorio ou o otimista anterior
            max_fixos=self.max_fixos_unchoked,
            mapa_de_blocos_global=mapa_de_blocos_global,
            meus_blocos=meus_blocos,
            todos_os_blocos_do_arquivo=todos_os_blocos_do_arquivo,
            meu_peer_id=self.meu_peer_id
        )

        self.peers_fixos_unchoked = novos_fixos
        self.peer_optimistic_unchoked = novo_optimistic_final
        
        logging.info(f"{self.meu_peer_id}: Unchoked fixos: {self.peers_fixos_unchoked}, Optimista: {self.peer_optimistic_unchoked}")

        # print(f"debug ({self.meu_peer_id}): estado apos ciclo: Fixos: {self.peers_fixos_unchoked}, Optimistic: {self.peer_optimistic_unchoked}")

    def get_peers_unchoked_por_mim(self) -> set[str]:
        """retorna um conjunto de todos os peers que nosso peer decidiu dar unchoke"""
        unchoked = set(self.peers_fixos_unchoked)
        if self.peer_optimistic_unchoked:
            unchoked.add(self.peer_optimistic_unchoked)
        return unchoked

    def esta_peer_unchoked(self, peer_id: str) -> bool:
        """verifica se um peer especifico esta na lista de unchoked pelo nosso peer"""
        # otimizacao: verificar o otimista primeiro se ele for diferente de None
        if peer_id == self.peer_optimistic_unchoked and self.peer_optimistic_unchoked is not None:
            return True
        return peer_id in self.peers_fixos_unchoked