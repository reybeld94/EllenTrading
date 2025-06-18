from django.db import models

class Direction(models.TextChoices):
    BUY = "buy", "Buy"
    SELL = "sell", "Sell"

class ExecutionMode(models.TextChoices):
    SIMULATED = "simulated", "Simulated"
    PAPER = "paper", "Paper"
    LIVE = "live", "Live"

class TradeStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    EXECUTED = "executed", "Executed"
    CLOSED = "closed", "Closed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"

class OrderType(models.TextChoices):
    MARKET = "market", "Market"
    LIMIT = "limit", "Limit"
    STOP = "stop", "Stop"
    STOP_LIMIT = "stop_limit", "Stop Limit"

class TimeInForce(models.TextChoices):
    DAY = "day", "Day"
    GTC = "gtc", "GTC"
    OPG = "opg", "Open"
    CLS = "cls", "Close"
    IOC = "ioc", "IOC"
    FOK = "fok", "FOK"

class SignalType(models.TextChoices):
    BUY = "buy", "Buy"
    SELL = "sell", "Sell"
    WATCH = "watch", "Watch"

class ExecutionMode(models.TextChoices):
    SIMULATED = "simulated", "Simulated"
    PAPER = "paper", "Paper"
    LIVE = "live", "Live"

class PriorityLevel(models.TextChoices):
    CONFIRM = "confirm", "Confirm"
    PRIMARY = "primary", "Primary"
    CONTEXT = "context", "Context"


class Timeframe(models.TextChoices):
    ONE_MIN = "1m", "1 Minute"
    FIVE_MIN = "5m", "5 Minutes"
    FIFTEEN_MIN = "15m", "15 Minutes"
    THIRTY_MIN = "30m", "30 Minutes"
    ONE_HOUR = "1h", "1 Hour"
    FOUR_HOUR = "4h", "4 Hours"
    ONE_DAY = "1d", "1 Day"
    ONE_WEEK = "1w", "1 Week"
    ONE_MONTH = "1mo", "1 Month"

class AssetClass(models.TextChoices):
    EQUITY = "equity", "Equity"
    CRYPTO = "crypto", "Crypto"
    FOREX = "forex", "Forex"
    ETF = "etf", "ETF"
    FUTURE = "future", "Future"
    OPTION = "option", "Option"
    INDEX = "index", "Index"
    BOND = "bond", "Bond"

class ExitPriorityLevel(models.TextChoices):
    PRIMARY = "primary", "Primary"
    SECONDARY = "secondary", "Secondary"
    FAILSAFE = "failsafe", "Failsafe"
