import asyncio
import signal
import sys
import traceback
import platform
from typing import Any, List, Optional, Tuple

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from uvicorn import Config, Server

from database import engine, Base
from models import User
from auth import router as auth_router

from nox.core.engine import Engine
from nox.core.registry import Registry
from nox.core.event_bus import EventBus
from nox.core.plugin_manager import PluginManager
from nox.core.memory import Memory

from nox.runtime.async_runtime import AsyncRuntimeLoop
from nox.worlds.world_manager import WorldManager
from nox.worlds.world_runtime import WorldRuntime

from nox.economy.ledger import IntelligenceLedger
from nox.economy.cost_model import CostModel
from nox.runtime.economy_gate import EconomyGate

from nox.utils.logger import logger, setup_logger

from nox.core.routes import router as http_router
from nox.core.routes import ws_router

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent

# ─────────────────────────────────────────────────────────────
# FastAPI
# ─────────────────────────────────────────────────────────────

app = FastAPI()

app.include_router(http_router)
app.include_router(ws_router)
app.include_router(auth_router)

app.mount("/static", StaticFiles(directory=BASE_DIR), name="static")

# ─────────────────────────────────────────────────────────────
# Database Initialization (Added as requested)
# ─────────────────────────────────────────────────────────────
def init_database():
    """Initialize database tables"""
    try:
        logger.info("Initializing database schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}", exc_info=True)

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

def setup_logging_once() -> None:
    setup_logger()

# ─────────────────────────────────────────────────────────────
# Runtime Shutdown
# ─────────────────────────────────────────────────────────────

async def stop_runtimes(runtimes: Optional[List[Any]]) -> None:
    if not runtimes:
        return

    logger.info("Stopping runtimes...")

    tasks = [
        asyncio.create_task(runtime.stop())
        for runtime in runtimes
        if hasattr(runtime, "stop") and callable(runtime.stop)
    ]

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error("Runtime stop error", exc_info=result)

    logger.info("All runtimes stopped.")


async def graceful_shutdown(
    runtimes: Optional[List[Any]] = None,
    server: Optional[Server] = None,
) -> None:

    logger.info("Shutdown signal received.")

    await stop_runtimes(runtimes)

    if server and not server.should_exit:
        logger.info("Signaling uvicorn to shutdown...")
        server.should_exit = True

# ─────────────────────────────────────────────────────────────
# System Bootstrap
# ─────────────────────────────────────────────────────────────

async def bootstrap_system() -> Tuple[Engine, Registry, List[Any], Memory]:

    logger.info("🌌 Bootstrapping NOX Core...")

    # Initialize database before anything else
    init_database()

    registry = Registry()
    event_bus = EventBus()

    # 🧠 Global Memory
    memory = Memory()

    # 💰 Economy System
    ledger = IntelligenceLedger()
    ledger.create_account("default")

    cost_model = CostModel()
    economy_gate = EconomyGate(ledger, cost_model)

    # ⚙️ Engine
    engine = Engine(registry, event_bus, economy_gate, memory)

    engine.memory = memory

    # 🔌 Plugin System
    plugin_manager = PluginManager(registry)

    plugin_manager.load_plugins()

    logger.info(f"🔌 Loaded {len(plugin_manager.plugins)} plugins")

    # Allow plugins to initialize with engine context
    for plugin in plugin_manager.plugins.values():

        if hasattr(plugin, "initialize"):
            try:
                plugin.initialize(
                    engine=engine,
                    registry=registry,
                    event_bus=event_bus,
                    memory=memory,
                )
                logger.info(f"Plugin initialized: {plugin.name}")

            except Exception:
                logger.error(
                    f"Plugin initialization failed: {plugin.name}",
                    exc_info=True
                )

    # 🌍 Worlds
    world_manager = WorldManager()

    for name in ["default", "research_simulation"]:
        world_manager.create_world(name)

    active_worlds = list(getattr(world_manager, "worlds", {}).keys())

    logger.info(f"Active worlds: {active_worlds}")

    # 🔁 Runtimes
    async_runtime = AsyncRuntimeLoop(engine)

    world_runtime = WorldRuntime(engine, world_manager)

    runtimes = [async_runtime, world_runtime]

    return engine, registry, runtimes, memory

# ─────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────

async def run_nox_with_api() -> None:

    setup_logging_once()

    logger.info("🚀 NOX Core starting...")

    runtimes: Optional[List[Any]] = None
    server: Optional[Server] = None

    try:

        engine, registry, runtimes, memory = await bootstrap_system()

        # Inject services into FastAPI
        app.state.registry = registry
        app.state.engine = engine
        app.state.runtimes = runtimes
        app.state.memory = memory

        config = Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            loop="asyncio",
            lifespan="on",
        )

        server = Server(config=config)

        loop = asyncio.get_running_loop()

        if platform.system() != "Windows":

            for sig in (signal.SIGINT, signal.SIGTERM):

                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(
                        graceful_shutdown(runtimes, server)
                    ),
                )

        else:

            logger.debug(
                "Windows detected — relying on KeyboardInterrupt"
            )

        logger.info("Starting NOX runtimes + FastAPI server...")

        await asyncio.gather(
            *(runtime.start() for runtime in runtimes),
            server.serve(),
        )

    except KeyboardInterrupt:

        logger.info("KeyboardInterrupt received.")

        await graceful_shutdown(runtimes, server)

    except Exception:

        logger.critical("Fatal error in main loop", exc_info=True)

        print("\n" + "═" * 80)
        print("❌ Critical error during execution")
        print(traceback.format_exc())
        print("═" * 80)

        await graceful_shutdown(runtimes, server)

        raise

# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

def main() -> None:

    try:

        asyncio.run(run_nox_with_api())

    except KeyboardInterrupt:

        logger.info("Shutdown complete.")

    except Exception:

        logger.critical("Unhandled exception in main()", exc_info=True)

        print("\n" + "═" * 80)
        print("❌ Unhandled top-level exception")
        print(traceback.format_exc())
        print("═" * 80)

        sys.exit(1)


if __name__ == "__main__":
    main()