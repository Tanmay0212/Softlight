import asyncio
import logging
import time
from typing import Callable, List

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.dev import ConsoleRenderer, set_exc_info
from structlog.processors import TimeStamper

# Global flag to track if structlog has been configured
_STRUCTLOG_CONFIGURED = False

def setup_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Setup structured logging with pretty console output similar to loguru.

    Args:
        name: The name of the module/logger (usually __name__)

    Returns:
        A configured structlog BoundLogger instance
    """
    global _STRUCTLOG_CONFIGURED
    
    # Only configure structlog once globally
    if not _STRUCTLOG_CONFIGURED:
        timestamper = TimeStamper(fmt="%Y-%m-%d %H:%M:%S")

        shared_processors = [
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            timestamper,
            set_exc_info,
            structlog.processors.CallsiteParameterAdder(
                parameters={
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                }
            ),
            ConsoleRenderer(
                colors=True,
                level_styles=ConsoleRenderer.get_default_level_styles(colors=True),
            ),
        ]

        structlog.configure(
            processors=shared_processors,
            logger_factory=structlog.PrintLoggerFactory(),
            wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
            cache_logger_on_first_use=False,  # Don't cache to allow proper module names
        )
        _STRUCTLOG_CONFIGURED = True

    # Bind the module name to the logger so it's always available
    return structlog.get_logger(name).bind(module=name)


class AsyncLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Callable) -> None:
        super().__init__(app)
        self.logger = setup_logger("app.middleware.request")
        self._log_tasks: List[asyncio.Task] = []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        request_details = {
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
        }

        try:
            response = await call_next(request)

            duration = time.time() - start_time
            # Log success asynchronously
            log_task = asyncio.create_task(
                self._log_request(
                    level="info",
                    event="Request completed",
                    duration=f"{duration:.3f}s",
                    status_code=response.status_code,
                    **request_details,
                )
            )
            self._log_tasks.append(log_task)
            log_task.add_done_callback(lambda t: self._log_tasks.remove(t))
            return response

        except Exception as e:
            duration = time.time() - start_time
            # Log error asynchronously
            log_task = asyncio.create_task(
                self._log_request(
                    level="error",
                    event="Request failed",
                    duration=f"{duration:.3f}s",
                    error=str(e),
                    error_type=type(e).__name__,
                    **request_details,
                )
            )
            self._log_tasks.append(log_task)
            log_task.add_done_callback(lambda t: self._log_tasks.remove(t))
            raise

    async def _log_request(self, level: str, **kwargs) -> None:
        log_method = getattr(self.logger, level)
        log_method(**kwargs)
