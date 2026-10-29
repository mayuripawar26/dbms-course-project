"""
retrieval/__init__.py

Retrieval package initialization.
Implements PEP 562 lazy attribute loading so that executing submodules via `python -m retrieval.<module>`
does not trigger runpy RuntimeWarning for pre-imported modules in sys.modules.
"""

from typing import Any

_EXPORTS = {
    "DocumentRetriever": ".document_retriever",
    "GraphRetriever": ".graph_retriever",
    "QueryRouter": ".query_router",
    "GraphRiskAnalyzer": ".risk_analyzer",
    "GraphRAGAnswerGenerator": ".answer_generator",
    "ScenarioAnalyzer": ".scenario_analyzer",
    "EvidenceValidator": ".evidence_validator",
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    if name in _EXPORTS:
        import importlib
        module = importlib.import_module(_EXPORTS[name], package=__package__)
        val = getattr(module, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)
