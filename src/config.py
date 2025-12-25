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
    trading_pair: str = Field("ETH-USDC")
    max_position_fraction: float = Field(0.5, ge=0, le=1)
    max_trades_per_hour: int = Field(2, ge=0)
    cooldown_minutes: int = Field(30, ge=0)
    paper_mode: bool = Field(False, alias="PAPER_MODE")
    paper_initial_equity: float = Field(10000.0, ge=0, alias="PAPER_INITIAL_EQUITY")


def load_settings() -> Settings:
    try:
        return Settings(**os.environ)
    except ValidationError as exc:
        missing = {err['loc'][0] for err in exc.errors()}
        msg = f"Missing or invalid env vars: {', '.join(sorted(missing))}"
        raise RuntimeError(msg) from exc
