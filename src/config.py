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
    venice_api_key: str = Field("", alias="VENICE_API_KEY")
    venice_endpoint: str = Field("https://api.venice.ai/v1/chat/completions", alias="VENICE_ENDPOINT")
    venice_model: str = Field("mistral-31-24b", alias="VENICE_MODEL")
    rpc_url: str = Field("", alias="RPC_URL")
    wallet_address: str = Field("", alias="WALLET_ADDRESS")
    private_key: str = Field("", alias="PRIVATE_KEY")
    account_address: str = Field("", alias="ACCOUNT_ADDRESS")  # Main wallet that API wallet trades for
    trading_pair: str = Field("ETH")  # Hyperliquid uses just "ETH" not "ETH-USDC"
    timeframe: str = Field("5m", alias="TIMEFRAME")
    candle_limit: int = Field(350, ge=50, le=1000, alias="CANDLE_LIMIT")
    max_position_fraction: float = Field(0.95, ge=0, le=1, alias="MAX_POSITION_FRACTION")
    max_trades_per_hour: int = Field(2, ge=0)
    cooldown_minutes: int = Field(30, ge=0)
    # Risk controls
    daily_loss_limit_pct: float = Field(0.06, ge=0, le=1, alias="DAILY_LOSS_LIMIT_PCT")
    pause_consecutive_losses: int = Field(3, ge=1, alias="PAUSE_CONSECUTIVE_LOSSES")
    pause_duration_hours: int = Field(24, ge=1, alias="PAUSE_DURATION_HOURS")
    shutdown_duration_hours: int = Field(24, ge=1, alias="SHUTDOWN_DURATION_HOURS")
    volatility_threshold_pct: float = Field(0.02, ge=0, le=1, alias="VOLATILITY_THRESHOLD_PCT")
    paper_mode: bool = Field(False, alias="PAPER_MODE")
    paper_initial_equity: float = Field(10000.0, ge=0, alias="PAPER_INITIAL_EQUITY")
    telegram_token: str = Field("", alias="TELEGRAM_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")
    # Stats preferences
    stats_count_partials_as_wins: bool = Field(True, alias="STATS_COUNT_PARTIALS_AS_WINS")
    stats_basis: str = Field("net", alias="STATS_BASIS")  # "net" or "R"
    include_fees_in_stats: bool = Field(True, alias="INCLUDE_FEES_IN_STATS")


def load_settings() -> Settings:
    try:
        return Settings(**os.environ)
    except ValidationError as exc:
        missing = {err['loc'][0] for err in exc.errors()}
        msg = f"Missing or invalid env vars: {', '.join(sorted(missing))}"
        raise RuntimeError(msg) from exc
