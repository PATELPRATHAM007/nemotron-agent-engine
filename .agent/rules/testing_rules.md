# Testing Constitution

1. **Test Location**: All test files must reside under `tests/` with the prefix `test_*.py`.
2. **Async Testing**: Use `pytest-asyncio` for async endpoints and services.
3. **Isolation**: Use `tmp_path` fixture for filesystem tests. Never write temporary test artifacts to repo root.
4. **Zero Flakiness**: Tests must be deterministic and runnable in parallel.
