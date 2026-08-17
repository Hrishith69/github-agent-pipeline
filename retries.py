from tenacity import retry, stop_after_attempt, wait_exponential
from logger import logger

def log_retry_attempt(retry_state):
    """Callback function that logs warning whenever an API call fails and retries."""
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    next_wait = retry_state.next_action.sleep
    logger.warning(
        f"⚠️ API call failed (Attempt {attempt}/3). Retrying in {next_wait:.1f}s... Error: {exception}"
    )

# Standard retry strategy: 3 attempts total, waiting 2s -> 4s -> 8s between retries
api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=log_retry_attempt,
    reraise=True
)