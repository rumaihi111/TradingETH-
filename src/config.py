import os
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    hyperliquid_api_key: str = Field("", alias="HYPERLIQUID_API_KEY")
    hyperliquid_secret: str = Field("", alias="HYPERLIQUID_SECRET")
    hyperliquid_base_url: str = Field("", alias="HYPERLIQUID_BASE_URL")
    hyperliquid_testnet: bool = Field(True, alias="HYPERLIQUID_TESTNET")
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    rpc_url: str = Field("", alias="RPC_URL")
    wallet_address: str = Field("", alias="WALLET_ADDRESS")
    private_key: str = Field("", alias="PRIVATE_KEY")
    account_address: str = Field("", alias="ACCOUNT_ADDRESS")  # Main wallet that API wallet trades for
    trading_pair: str = Field("DOGE")  # Hyperliquid uses just "DOGE" not "DOGE-USDC"
    max_position_fraction: float = Field(0.95, ge=0, le=1, alias="MAX_POSITION_FRACTION")  # 95% of equity per trade
    max_trades_per_hour: int = Field(45, ge=0)
    cooldown_minutes: int = Field(0, ge=0)
    paper_mode: bool = Field(False, alias="PAPER_MODE")
    
    # Transaction fees (Hyperliquid fee structure)
    # Limit (maker): 0.01-0.02%  |  Market (taker): 0.04-0.06%
    maker_fee_pct: float = Field(0.015, ge=0)  # 0.015% average maker fee
    taker_fee_pct: float = Field(0.05, ge=0)   # 0.05% average taker fee (~0.035% fee + ~0.015% slippage)
    
    # Slippage estimates for market orders
    # Liquid (ETH/BTC): 0.08-0.15% total | Mid-cap/volatile: 0.08-0.15%
    market_slippage_pct: float = Field(0.10, ge=0)  # 0.10% average slippage on market orders
    paper_initial_equity: float = Field(10000.0, ge=0, alias="PAPER_INITIAL_EQUITY")
    telegram_token: str = Field("", alias="TELEGRAM_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")


def load_settings() -> Settings:
    try:
        return Settings(**os.environ)
    except ValidationError as exc:
        missing = {err['loc'][0] for err in exc.errors()}
        msg = f"Missing or invalid env vars: {', '.join(sorted(missing))}"
        raise RuntimeError(msg) from exc
