import logging
from .base_risk import BaseRiskManager

logger = logging.getLogger(__name__)


class FixedPercent(BaseRiskManager):
    """
    Gestione rischio a percentuale fissa.
    Semplicemente rischia X% dell'equity per ogni trade.
    """
    
    def __init__(self, params=None):
        super().__init__(params)
        self.risk_per_trade = self.params.get("risk_per_trade", 0.02)  # Default 2%
        logger.info(f"FixedPercent Risk Manager: rischio {self.risk_per_trade:.1%} per trade")
    
    def calculate_position_size(self, capital, entry_price, stop_loss_price=None, 
                               direction="LONG", volatility=None):
        """
        Calcola quanto capitale rischiare.
        
        Args:
            capital: Equity corrente
            entry_price: Prezzo di entry (usato solo per calcolare quantità se necessario)
            stop_loss_price: IGNORATO - la strategia gestisce lo stop loss
            direction: IGNORATO - non influisce sul rischio percentuale
            volatility: IGNORATO
        
        Returns:
            float: Importo monetario da rischiare
        """
        # SEMPLICE: X% del capitale
        investment_amount = capital * self.risk_per_trade  # 200€
        
        # 2. Converti in QUANTITÀ
        quantity = investment_amount / entry_price  # 200 / 109.9963 = 1.818 unità
        
        logger.info(f"Position Value: ${investment_amount:.2f} at ${entry_price} ->  {quantity:.4f} units")
        
        # return quantity  # Restituisce QUANTITÀ
        return investment_amount
    
    def can_trade(self, capital, current_drawdown, market_conditions=None):
        """
        Controlli opzionali per bloccare trading in condizioni estreme
        """
        # Esempio: blocca se drawdown > 20%
        max_drawdown = self.params.get("max_drawdown", 0.20)
        
        if current_drawdown > max_drawdown:
            logger.warning(f"Trading bloccato: drawdown {current_drawdown:.1%} > {max_drawdown:.1%}")
            return False
        
        # Esempio: blocca se capitale sotto soglia minima
        min_capital = self.params.get("min_capital", 100)
        if capital < min_capital:
            logger.warning(f"Trading bloccato: capitale {capital:.2f} < {min_capital}")
            return False
        
        return True