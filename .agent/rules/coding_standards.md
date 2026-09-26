# Coding Standards & Quality Constitution

1. **Type Annotations**: All public functions and classes MUST have explicit PEP 484 type hints.
2. **Immutability & Pydantic**: Use Pydantic V2 models for structured request/response and configuration schemas.
3. **Docstrings**: Public methods and classes require Google-style docstrings with arguments, returns, and raises.
4. **Error Handling**: Raise explicit custom domain exceptions instead of bare `Exception`.
5. **No Hallucinated Imports**: Only import from dependencies declared in `requirements.txt` or repository packages.
