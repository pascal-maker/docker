from __future__ import annotations

from document_structuring_agent.agents.parsers.generic import (
    create_generic_parser_agent,
)
from document_structuring_agent.agents.parsers.invoice import (
    create_invoice_parser_agent,
)
from document_structuring_agent.agents.parsers.legal_schedule import (
    create_legal_schedule_parser_agent,
)
from document_structuring_agent.agents.parsers.letter import create_letter_parser_agent
from document_structuring_agent.models.classification import DocumentClassification
from document_structuring_agent.models.registry import ParserRegistry


def build_parser_registry() -> ParserRegistry:
    """Build the mapping from document classification to specialized parser agent."""
    generic = create_generic_parser_agent()
    letter = create_letter_parser_agent()
    legal = create_legal_schedule_parser_agent()
    invoice = create_invoice_parser_agent()

    return ParserRegistry(
        {
            DocumentClassification.LETTER: letter,
            DocumentClassification.LEGAL_SCHEDULE: legal,
            DocumentClassification.CONTRACT: legal,
            DocumentClassification.SEC_FILING: generic,
            DocumentClassification.REPORT: generic,
            DocumentClassification.RECEIPT: generic,
            DocumentClassification.INVOICE: invoice,
            DocumentClassification.UNKNOWN: generic,
        }
    )
