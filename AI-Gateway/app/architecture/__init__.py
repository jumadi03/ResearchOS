"""
ResearchOS Architecture.

Canonical public namespace for the
Architecture subsystem.
"""

from .models import (
    ArchitectureArtifact,
    ArchitectureFact,
    ArchitectureInventory,
    ArchitectureLaw,
    ArchitectureValidationResult,
    ArchitectureViolation,
    ValidationReport,
)

from .scanner import ArchitectureScanner
from .parser import ArchitectureParser
from .symbol_extractor import SymbolExtractor
from .import_extractor import ImportExtractor
from .class_extractor import ClassExtractor
from .visitor import ArchitectureVisitor
from .node_collector import NodeCollector


__all__ = [
    "ArchitectureArtifact",
    "ArchitectureFact",
    "ArchitectureInventory",
    "ArchitectureLaw",
    "ArchitectureValidationResult",
    "ArchitectureViolation",
    "ValidationReport",
    "ArchitectureScanner",
    "ArchitectureParser",
    "SymbolExtractor",
    "ImportExtractor",
    "ClassExtractor",
    "ArchitectureVisitor",
    "NodeCollector",
]