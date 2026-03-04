"""
Phase 4: Audit Mode

Verifies claims against source documents with provenance.
Returns: VERIFIED | UNVERIFIED | NOT_FOUND
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger

from src.agents.query_agent import QueryAgent, QueryResult
from src.agents.fact_table import FactTableExtractor
from src.models.schemas import ProvenanceChain


@dataclass
class AuditResult:
    """Result of claim verification"""
    claim: str
    status: str  # "VERIFIED" | "UNVERIFIED" | "NOT_FOUND"
    confidence: float
    provenance: List[ProvenanceChain]
    evidence: str
    source_doc: Optional[str]
    source_page: Optional[int]


class AuditAgent:
    """
    Phase 4: Audit Mode Agent
    
    Verifies claims against source documents.
    
    Example:
        claim = "The report states revenue was $4.2B in Q3"
        result = audit_agent.verify_claim(claim)
        # Returns: VERIFIED with provenance OR NOT_FOUND
    """
    
    def __init__(self, query_agent: QueryAgent, fact_table: FactTableExtractor):
        self.query_agent = query_agent
        self.fact_table = fact_table
        logger.info("AuditAgent initialized")
    
    def verify_claim(self, claim: str, doc_ids: Optional[List[str]] = None) -> AuditResult:
        """
        Verify a claim against source documents
        
        Args:
            claim: The claim to verify (e.g., "Revenue was $4.2B in Q3")
            doc_ids: Optional list of document IDs to search
            
        Returns:
            AuditResult with verification status and provenance
        """
        logger.info(f"Verifying claim: {claim}")
        
        # Step 1: Extract key facts from claim
        extracted_facts = self._extract_claim_facts(claim)
        
        # Step 2: Query FactTable for matching facts
        fact_matches = self._query_fact_table(extracted_facts, doc_ids)
        
        # Step 3: Query documents for supporting evidence
        query_result = self.query_agent.query(claim, doc_ids=doc_ids)
        
        # Step 4: Determine verification status
        status, confidence, evidence = self._determine_status(
            claim, extracted_facts, fact_matches, query_result
        )
        
        # Step 5: Build provenance chain
        provenance = query_result.provenance
        
        # Step 6: Get source info
        source_doc = provenance[0].document_name if provenance else None
        source_page = provenance[0].page_number if provenance else None
        
        result = AuditResult(
            claim=claim,
            status=status,
            confidence=confidence,
            provenance=provenance,
            evidence=evidence,
            source_doc=source_doc,
            source_page=source_page
        )
        
        logger.success(f"Audit complete: {status} (confidence: {confidence:.2f})")
        
        return result
    
    def _extract_claim_facts(self, claim: str) -> Dict[str, str]:
        """
        Extract key facts from claim
        
        Example: "Revenue was $4.2B in Q3" → {"revenue": "$4.2B", "period": "Q3"}
        """
        import re
        
        facts = {}
        
        # Extract monetary values
        money_pattern = r'\$?([\d,.]+[BMK]?)'
        money_match = re.search(money_pattern, claim)
        if money_match:
            facts["value"] = money_match.group(1)
        
        # Extract fiscal periods
        period_pattern = r'(Q[1-4]|FY|Fiscal\s+Year)\s*(\d{4})?'
        period_match = re.search(period_pattern, claim, re.IGNORECASE)
        if period_match:
            facts["period"] = period_match.group(0)
        
        # Extract metric type
        metric_keywords = ['revenue', 'income', 'profit', 'assets', 'liabilities', 'tax']
        for keyword in metric_keywords:
            if keyword in claim.lower():
                facts["metric"] = keyword
                break
        
        return facts
    
    def _query_fact_table(self, facts: Dict[str, str], doc_ids: Optional[List[str]]) -> List[Dict]:
        """Query FactTable for matching facts"""
        matches = []
        
        if "metric" in facts:
            metric_results = self.fact_table.query_facts(facts["metric"], doc_ids[0] if doc_ids else None)
            matches.extend(metric_results)
        
        return matches
    
    def _determine_status(
        self,
        claim: str,
        extracted_facts: Dict[str, str],
        fact_matches: List[Dict],
        query_result: QueryResult
    ) -> tuple:
        """
        Determine verification status
        
        Returns: (status, confidence, evidence)
        """
        # Check if FactTable has matching facts
        if fact_matches:
            # Verify value matches
            for fact in fact_matches:
                if extracted_facts.get("value") in fact["fact_value"]:
                    return (
                        "VERIFIED",
                        0.95,
                        f"FactTable confirms: {fact['fact_key']} = {fact['fact_value']} (Page {fact['page_number']})"
                    )
        
        # Check if query found supporting evidence
        if query_result.confidence > 0.5 and query_result.provenance:
            return (
                "VERIFIED",
                query_result.confidence,
                f"Document evidence: {query_result.answer[:200]}..."
            )
        elif query_result.confidence > 0.2:
            return (
                "UNVERIFIED",
                query_result.confidence,
                f"Weak evidence: {query_result.answer[:200]}..."
            )
        else:
            return (
                "NOT_FOUND",
                0.0,
                "No supporting evidence found in documents"
            )
    
    def batch_verify(self, claims: List[str], doc_ids: Optional[List[str]] = None) -> List[AuditResult]:
        """Verify multiple claims"""
        results = []
        for claim in claims:
            result = self.verify_claim(claim, doc_ids)
            results.append(result)
        return results
    
    def get_audit_report(self, claims: List[str], doc_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate audit report for multiple claims"""
        results = self.batch_verify(claims, doc_ids)
        
        verified = sum(1 for r in results if r.status == "VERIFIED")
        unverified = sum(1 for r in results if r.status == "UNVERIFIED")
        not_found = sum(1 for r in results if r.status == "NOT_FOUND")
        
        return {
            "total_claims": len(claims),
            "verified": verified,
            "unverified": unverified,
            "not_found": not_found,
            "verification_rate": verified / len(claims) if claims else 0,
            "results": [
                {
                    "claim": r.claim,
                    "status": r.status,
                    "confidence": r.confidence,
                    "source": f"{r.source_doc} (p. {r.source_page})" if r.source_doc else None
                }
                for r in results
            ]
        }