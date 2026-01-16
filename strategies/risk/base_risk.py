"""
Classe base per risk management (gestione rischio).
"""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseRiskManager(ABC):
    """
    Template per gestione rischio e position sizing.
    
    Determina QUANTO rischiare per ogni trade.
    """
    
    def __init__(self, params=None):
        """
        Args:
            params (dict): Parametri dal config.yaml
                         Es: {"risk_per_trade": 0.02} per rischio 2%
        """
        self.params = params or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def calculate_position_size(self, capital, entry_price, stop_loss_price=None, 
                               direction="LONG", volatility=None):
        """
        Calcola la dimensione della posizione.
        
        Args:
            capital (float): Capitale disponibile
            entry_price (float): Prezzo di entry proposto
            stop_loss_price (float, opzionale): Prezzo di stop loss (se disponibile)
            direction (str): "LONG" o "SHORT"
            volatility (float, opzionale): Volatilità corrente (es: ATR)
        
        Returns:
            float: Quantità da tradare (es: 0.5 BTC)
                   o valore monetario (es: 500 USD)
        """
        raise NotImplementedError(
            f"Il risk manager {self.__class__.__name__} deve implementare calculate_position_size()"
        )
    
    def can_trade(self, capital, current_drawdown, market_conditions=None):
        """
        (Opzionale) Determina se è permesso aprire nuovi trade.
        
        Args:
            capital (float): Capitale attuale
            current_drawdown (float): Drawdown corrente in percentuale
            market_conditions (dict, opzionale): Condizioni di mercato
        
        Returns:
            bool: True se possono essere aperti nuovi trade
        """
        # Esempio: blocca trading se drawdown > 10%
        if current_drawdown > 0.10:
            logger.warning(f"Trading bloccato: drawdown {current_drawdown:.1%} > 10%")
            return False
        
        return True
    
    def adjust_for_volatility(self, base_position_size, volatility, avg_volatility):
        """
        (Opzionale) Aggiusta position size in base alla volatilità.
        
        Esempio: riduci position size se volatilità è alta.
        """
        if volatility and avg_volatility:
            volatility_ratio = volatility / avg_volatility
            # Se volatilità è 2x la media, riduci position size del 50%
            if volatility_ratio > 2.0:
                return base_position_size * 0.5
        
        return base_position_size