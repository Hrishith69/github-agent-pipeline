import io
import logging
import sys

# Windows console UTF-8 stream fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Configure logger
logger = logging.getLogger("github_agent_pipeline")
logger.setLevel(logging.INFO)

# Formatter: timestamp [LEVEL] logger_name: message
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Stream Handler (Terminal)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# File Handler (Writes to pipeline.log file)
file_handler = logging.FileHandler("pipeline.log", encoding="utf-8")
file_handler.setFormatter(formatter)

# Avoid duplicate handlers on re-initialization
if not logger.handlers:
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)