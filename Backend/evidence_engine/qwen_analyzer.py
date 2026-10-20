"""
NetraSetu Qwen2.5-0.5B-Instruct Evidence Analysis Adapter.

SAFETY SPECIFICATION:
- Uses Qwen2.5-0.5B-Instruct as a lightweight local model candidate for structured evidence
  extraction and classification.
- NEVER acts as the sole authority for factual claims.
- Validates model outputs directly against source passages.
- If it cannot reliably produce valid structured output, reports the limitation rather than
  silently inventing results.
- Lazy, configurable loading to avoid loading multiple large models unnecessarily.
"""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Dict, List, Optional, Any, Tuple

from .models import (
    EvidenceRole,
    EvidenceStrength,
    Applicability,
    RequirementType,
)

logger = logging.getLogger("netrasetu.evidence_engine.qwen")

DEFAULT_QWEN_MODEL = os.getenv("NETRASETU_QWEN_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")


class QwenEvidenceAnalyzer:
    """
    Lightweight local model adapter for structured evidence analysis.
    """

    def __init__(self, model_name: str = DEFAULT_QWEN_MODEL):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        self._is_loaded = False
        self._load_error: Optional[str] = None

    def is_available(self) -> bool:
        """
        Check if Qwen model is successfully loaded or can be loaded.
        """
        return self._is_loaded or self._load_error is None

    def load_model(self) -> bool:
        """
        Lazily load the Qwen2.5-0.5B-Instruct model and tokenizer.
        """
        if self._is_loaded:
            return True
        if self._load_error:
            return False

        try:
            logger.info("Loading local evidence analyzer candidate: %s", self.model_name)
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            device = "cuda" if torch.cuda.is_available() else "cpu"
            torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            if device == "cpu":
                self._model = self._model.to("cpu")

            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                max_new_tokens=512,
                temperature=0.1,
                do_sample=False,
            )
            self._is_loaded = True
            logger.info("Qwen2.5-0.5B-Instruct loaded successfully on %s", device)
            return True
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning(
                "Unable to load local Qwen model (%s): %s. Will report limitation.",
                self.model_name,
                exc,
            )
            return False

    def validate_grounding_against_source(
        self,
        extracted_text: str,
        source_records: List[Dict[str, Any]],
    ) -> Tuple[bool, List[str]]:
        """
        Validate that any claim or reasoning produced by the model has verifiable grounding
        in the retrieved source text chunks.
        """
        if not extracted_text:
            return False, ["Empty extraction output."]

        # Aggregate all source texts
        full_source_corpus = " ".join([
            str(r.get("text", "")).lower() + " " + str(r.get("title", "")).lower()
            for r in source_records
        ])

        # Token-level overlap verification for reasoning clauses
        words = re.findall(r"\b[a-zA-Z0-9_-]{4,}\b", extracted_text.lower())
        if not words:
            return True, []

        grounded_count = sum(1 for w in words if w in full_source_corpus)
        overlap_ratio = grounded_count / len(words)

        # Require at least 65% token grounding from source documents
        if overlap_ratio < 0.65:
            return False, [
                f"Grounding validation failed: Only {overlap_ratio*100:.1f}% of key terms in reasoning originate from source evidence.",
                "Potential unverified inference detected.",
            ]

        return True, []

    def classify_with_qwen(
        self,
        claim: str,
        evidence_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute structured classification using local Qwen model candidate.
        Validates outputs against source passages and reports explicit limitations.
        """
        if not self._is_loaded:
            success = self.load_model()
            if not success:
                return {
                    "claim": claim,
                    "classifications": [],
                    "all_evidence_classified": False,
                    "missing_classifications": [str(r.get("evidence_id")) for r in evidence_records],
                    "classifier": f"{self.model_name} (Local)",
                    "status": "MODEL_UNAVAILABLE",
                    "limitation": f"Qwen2.5-0.5B-Instruct could not be loaded: {self._load_error}",
                    "recommendation": "Review local environment or fall back to deterministic classification.",
                }

        # Build Qwen chat prompt
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Evidence Extraction and Classification Assistant in NetraSetu. "
                    "Analyze the supplied evidence records for the claim. "
                    "Classify each record with: evidence_id, evidence_role (SUPPORTING, CONTRADICTING, LIMITING, CONTEXTUAL), "
                    "evidence_strength (STRONG, MODERATE, WEAK, INSUFFICIENT), applicability (DIRECT, PARTIAL, UNCERTAIN, NOT_APPLICABLE), "
                    "requirement_type (MANDATORY, ADVISORY, TECHNICAL, UNKNOWN), confidence (0.0 to 1.0), and reasoning. "
                    "Return strictly a JSON object with key 'classifications'. Do not invent outside facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"CLAIM: {claim}\n\n"
                    f"EVIDENCE RECORDS:\n{json.dumps(evidence_records, indent=2, ensure_ascii=False)}"
                ),
            },
        ]

        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        try:
            output = self._pipeline(prompt)
            generated_text = output[0]["generated_text"][len(prompt):].strip()

            # Extract JSON block
            json_match = re.search(r"\{.*\}", generated_text, re.DOTALL)
            if not json_match:
                return {
                    "claim": claim,
                    "classifications": [],
                    "all_evidence_classified": False,
                    "missing_classifications": [str(r.get("evidence_id")) for r in evidence_records],
                    "classifier": f"{self.model_name} (Local)",
                    "status": "UNSTRUCTURED_OUTPUT_LIMITATION",
                    "limitation": "Model did not output a valid JSON classification structure.",
                    "raw_output": generated_text[:300],
                }

            parsed_data = json.loads(json_match.group(0))
            classifications = parsed_data.get("classifications", [])

            # Validate grounding against source records
            validated_classifications = []
            for item in classifications:
                reasoning = item.get("reasoning", "")
                is_grounded, grounding_errors = self.validate_grounding_against_source(reasoning, evidence_records)

                item["grounding_verified"] = is_grounded
                if not is_grounded:
                    item["grounding_warnings"] = grounding_errors

                validated_classifications.append(item)

            return {
                "claim": claim,
                "classifications": validated_classifications,
                "all_evidence_classified": len(validated_classifications) == len(evidence_records),
                "missing_classifications": [],
                "classifier": f"{self.model_name} (Local)",
                "status": "SUCCESS",
                "grounding_audit": "PASSED" if all(c.get("grounding_verified", False) for c in validated_classifications) else "WARNINGS_DETECTED",
            }

        except Exception as exc:
            return {
                "claim": claim,
                "classifications": [],
                "all_evidence_classified": False,
                "missing_classifications": [str(r.get("evidence_id")) for r in evidence_records],
                "classifier": f"{self.model_name} (Local)",
                "status": "INFERENCE_ERROR",
                "limitation": f"Inference failed with exception: {exc}",
            }


# Global singleton instance
_qwen_analyzer_instance: Optional[QwenEvidenceAnalyzer] = None

def get_qwen_analyzer() -> QwenEvidenceAnalyzer:
    global _qwen_analyzer_instance
    if _qwen_analyzer_instance is None:
        _qwen_analyzer_instance = QwenEvidenceAnalyzer()
    return _qwen_analyzer_instance
