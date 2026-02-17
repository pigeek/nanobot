"""Simple HTTP API server for nanobot agent."""

import asyncio
from aiohttp import web
from loguru import logger

from nanobot.agent.loop import AgentLoop


class NanobotAPIServer:
    """
    HTTP API server that exposes the nanobot agent.

    Endpoints:
        POST /api/chat - Send a message to the agent and get a response
        GET /health - Health check
    """

    def __init__(self, agent: AgentLoop, host: str = "0.0.0.0", port: int = 18790):
        self.agent = agent
        self.host = host
        self.port = port
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def start(self) -> None:
        """Start the HTTP server."""
        self._app = web.Application()
        self._app.router.add_post("/api/chat", self._handle_chat)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        logger.info(f"HTTP API server started at http://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._runner:
            await self._runner.cleanup()
            logger.info("HTTP API server stopped")

    async def _handle_chat(self, request: web.Request) -> web.Response:
        """
        Handle POST /api/chat

        Request body:
            {
                "message": "Hello!",
                "session_id": "voice:device123",  // optional
                "channel": "voice",               // optional
                "chat_id": "device123"            // optional
            }

        Response:
            {
                "response": "Hi there! How can I help you?",
                "session_id": "voice:device123"
            }
        """
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response(
                {"error": f"Invalid JSON: {e}"},
                status=400
            )

        message = data.get("message")
        if not message:
            return web.json_response(
                {"error": "Missing 'message' field"},
                status=400
            )

        session_id = data.get("session_id", "api:default")
        channel = data.get("channel", "api")
        chat_id = data.get("chat_id", "default")

        logger.info(f"API chat request: session={session_id}, message={message[:50]}...")

        try:
            response = await self.agent.process_direct(
                content=message,
                session_key=session_id,
                channel=channel,
                chat_id=chat_id,
            )

            logger.info(f"API chat response: {response[:100] if response else '(empty)'}...")

            return web.json_response({
                "response": response or "",
                "session_id": session_id,
            })

        except Exception as e:
            logger.error(f"API chat error: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle GET /health"""
        return web.json_response({"status": "ok"})
