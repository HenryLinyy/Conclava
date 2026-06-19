"""CLI entry point for Conclava Gateway."""

import uvicorn
from conclava.config import FusionConfig


def main():
    config = FusionConfig()
    uvicorn.run(
        "conclava.server:app",
        host=config.conclava_host,
        port=config.conclava_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
