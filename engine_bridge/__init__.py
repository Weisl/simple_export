"""Pure-logic package for MCP-based post-export engine verification.

Contains no bpy.types classes and is never added to the addon's
register()/unregister() chain - the same precedent as functions/. Only the
thin wrapper modules in preferences/, operators/ and ui/ that consume this
package register bpy-facing state.
"""

from .verification import (
    EngineVerificationResult,
    VerificationCancelled,
    available_engine_ids,
    get_adapter_class,
    guess_engine_for_collection,
    run_verification,
)

__all__ = [
    "EngineVerificationResult",
    "VerificationCancelled",
    "available_engine_ids",
    "get_adapter_class",
    "guess_engine_for_collection",
    "run_verification",
]
