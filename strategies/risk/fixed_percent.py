"""
Fixed Percent Risk Management.
Risk a fixed percentage of capital per trade.
"""

from .base_risk import BaseRiskManager
import logging

logger = logging.getLogger(__name__)


class FixedPercentRisk(BaseRiskManager):
    """
    Risk a fixed percentage of capital per trade.
    
    Parameters:
        risk_per_trade: Percentage of capital to risk (default: 0.02 for 2%)
        max_position_pct: Maximum position size as % of capital (optional)
        min_position_size: Minimum position size (optional)
    """
    
    def __init__(self, params=None):
        """
        Initialize FixedPercentRisk.
        
        Args:
            params (dict): Parameters from config.yaml
        """
        super().__init__(params)
        
        # Extract parameters with defaults
        self.risk_per_trade = self.params.get('risk_per_trade', 0.02)
        self.max_position_pct = self.params.get('max_position_pct', 1.0)  # 100%
        self.min_position_size = self.params.get('min_position_size', 0.0)
        
        logger.info(f"Initialized FixedPercentRisk: risk={self.risk_per_trade*100:.1f}%, "
                   f"max_position={self.max_position_pct*100:.0f}%")
    
    def calculate_position_size(self, capital, entry_price, stop_loss_price=None, 
                               direction="LONG", volatility=None):
        """
        Calculate position size based on fixed percentage risk.
        
        Args:
            capital (float): Available capital
            entry_price (float): Proposed entry price
            stop_loss_price (float, optional): Stop loss price (if available)
            direction (str): "LONG" or "SHORT"
            volatility (float, optional): Current volatility (e.g., ATR)
        
        Returns:
            float: Quantity to trade (e.g., 0.5 BTC)
        """
        # Default stop loss if not provided (10% for now, will be improved)
        if stop_loss_price is None:
            if direction == "LONG":
                stop_loss_price = entry_price * 0.9  # 10% stop loss
            else:
                stop_loss_price = entry_price * 1.1  # 10% stop loss
        
        # Calculate risk per unit
        if direction == "LONG":
            risk_per_unit = entry_price - stop_loss_price
        else:  # SHORT
            risk_per_unit = stop_loss_price - entry_price
        
        # Avoid division by zero
        if risk_per_unit <= 0:
            logger.warning(f"Invalid risk per unit: {risk_per_unit}. Using 1% of capital.")
            # Fallback: use 1% of capital
            position_value = capital * 0.01
            return position_value / entry_price
        
        # Calculate risk amount (capital * risk percentage)
        risk_amount = capital * self.risk_per_trade
        
        # Calculate position size based on risk
        position_size = risk_amount / risk_per_unit
        
        # Apply max position size constraint (as % of capital)
        max_position_value = capital * self.max_position_pct
        current_position_value = position_size * entry_price
        
        if current_position_value > max_position_value:
            logger.debug(f"Position size reduced from ${current_position_value:.2f} to ${max_position_value:.2f} (max {self.max_position_pct*100:.0f}% of capital)")
            position_size = max_position_value / entry_price
        
        # Apply minimum position size
        if position_size < self.min_position_size:
            logger.debug(f"Position size below minimum: {position_size:.6f} < {self.min_position_size}")
            return 0.0
        
        # Adjust for volatility if provided (optional)
        if volatility is not None:
            position_size = self.adjust_for_volatility(position_size, volatility, volatility * 2)  # Placeholder
        
        logger.debug(f"Calculated position size: {position_size:.6f} units, "
                    f"Risk: ${risk_amount:.2f} ({self.risk_per_trade*100:.1f}%), "
                    f"Entry: ${entry_price:.2f}, SL: ${stop_loss_price:.2f}")
        
        return position_size
    
    def can_trade(self, capital, current_drawdown, market_conditions=None):
        """
        Determine if trading is allowed.
        
        Args:
            capital (float): Current capital
            current_drawdown (float): Current drawdown percentage
            market_conditions (dict, optional): Market conditions
        
        Returns:
            bool: True if new trades can be opened
        """
        # Call parent implementation
        if not super().can_trade(capital, current_drawdown, market_conditions):
            return False
        
        # Additional checks for fixed percent risk
        # Example: don't trade if capital below minimum
        min_capital = self.params.get('min_capital', 100)
        if capital < min_capital:
            logger.warning(f"Trading blocked: capital ${capital:.2f} < min ${min_capital}")
            return False
        
        return True
