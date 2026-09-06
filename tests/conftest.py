"""Shared configuration and fixtures for AgentForge unit and E2E tests."""

import asyncio
import inspect
import pytest


def pytest_pyfunc_call(pyfuncitem):
    """Enable native execution of async def test functions via asyncio.run()."""
    test_obj = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_obj):
        test_args = {
            arg: pyfuncitem.funcargs[arg]
            for arg in pyfuncitem._fixtureinfo.argnames
            if arg in pyfuncitem.funcargs
        }
        asyncio.run(test_obj(**test_args))
        return True
    return None
