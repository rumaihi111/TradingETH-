from typing import Any, Dict, List, Optional

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


class HyperliquidClient:
    def __init__(
        self,
        private_key_hex: str,
        testnet: bool = True,
        base_url_override: str = "",
        skip_ws: bool = True,
    ):
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex
        self.wallet = Account.from_key(private_key_hex)
        base_url = base_url_override or (constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL)
        self.info = Info(base_url, skip_ws=skip_ws)
        self.exchange = Exchange(self.wallet, base_url, account_address=self.wallet.address)

    def account(self) -> Dict[str, Any]:
        return self.info.user_state(self.wallet.address)

    def positions(self) -> List[Dict[str, Any]]:
        state = self.account()
        positions = []
        for p in state.get("assetPositions", []):
            pos = p.get("position") or {}
            if not pos:
                continue
            positions.append({
                "coin": pos.get("coin"),
                "size": float(pos.get("szi", 0)),
                "entry": float(pos.get("entryPx") or 0),
                "unrealized": float(pos.get("unrealizedPnl") or 0),
            })
        return positions

    def equity(self) -> float:
        state = self.account()
        summary = state.get("marginSummary", {})
        return float(summary.get("accountValue", 0))

    def place_market(self, symbol: str, side: str, size: float, max_slippage_pct: float) -> Dict[str, Any]:
        is_buy = side.lower() == "long"
        slippage = max_slippage_pct / 100
        return self.exchange.market_open(symbol, is_buy=is_buy, sz=size, px=None, slippage=slippage)

    def close_position(self, symbol: str, size: Optional[float] = None, max_slippage_pct: float = 0.5) -> Dict[str, Any]:
        slippage = max_slippage_pct / 100
        return self.exchange.market_close(symbol, sz=size, px=None, slippage=slippage)
