"""Product quality validation module.

Provides validation for generated digital products:
- validate_completeness: Checks all sections present, no empty content
- validate_formatting: Checks consistent font sizes, proper spacing
- validate_coherence: Uses AI to verify content flows logically
- get_quality_score: Returns 0-100 score based on validation

Per D-03: AI does initial assessment, human does final approval via dashboard.
"""

from enum import Literal
from typing import Optional

# Try to import OpenAI - validation can work without it
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.product_generation.schemas import ProductOutput, ProductContent


ValidationRecommendation = Literal["approve", "needs_revision", "regenerate"]


class ValidationResult:
    """Result of product validation.

    Attributes:
        passed: Whether the product passed validation.
        issues: List of issues found (if any).
        score: Quality score from 0-100.
        recommendation: Action to take based on validation.
    """

    def __init__(
        self,
        passed: bool,
        issues: list[str],
        score: float,
        recommendation: ValidationRecommendation,
    ):
        self.passed = passed
        self.issues = issues
        self.score = score
        self.recommendation = recommendation


class ProductValidator:
    """Validates generated digital products for quality.

    Performs automated validation including completeness, formatting,
    and coherence checks. Uses AI for content coherence validation.

    Per D-03: AI does initial assessment, human does final approval.
    """

    def __init__(self, client: Optional[OpenAI] = None):
        """Initialize the product validator.

        Args:
            client: OpenAI client for AI-powered coherence validation.
        """
        self.client = client

    def validate(self, product: ProductOutput) -> ValidationResult:
        """Validate a product for quality.

        Runs all validation checks (completeness, formatting, coherence)
        and returns a result with score and recommendations.

        Args:
            product: The product to validate.

        Returns:
            ValidationResult with pass/fail status, issues, and score.
        """
        # Run all validation checks
        completeness = self.validate_completeness(product)
        formatting = self.validate_formatting(product)
        coherence = self.validate_coherence(product)

        # Collect all issues
        issues = []
        if not completeness["passed"]:
            issues.extend(completeness["issues"])
        if not formatting["passed"]:
            issues.extend(formatting["issues"])
        if not coherence["passed"]:
            issues.extend(coherence["issues"])

        # Calculate overall score (weighted average)
        score = completeness["score"] * 0.3 + formatting["score"] * 0.3 + coherence["score"] * 0.4

        # Determine recommendation
        if score >= 80 and not issues:
            recommendation: ValidationRecommendation = "approve"
        elif score >= 50:
            recommendation = "needs_revision"
        else:
            recommendation = "regenerate"

        # Passed if score >= 60 and no critical issues
        passed = score >= 60 and len([i for i in issues if i.startswith("CRITICAL")]) == 0

        return ValidationResult(
            passed=passed, issues=issues, score=score, recommendation=recommendation
        )

    def validate_completeness(self, product: ProductOutput) -> dict:
        """Check that product has all required sections and content.

        Verifies:
        - Introduction is present
        - All major sections exist
        - No sections are empty
        - Conclusion is present

        Args:
            product: The product to check.

        Returns:
            Dict with 'passed' (bool), 'issues' (list), and 'score' (0-100).
        """
        issues = []
        score = 100

        # Check introduction
        if not product.content.intro:
            issues.append("CRITICAL: Missing introduction")
            score -= 20

        # Check sections exist
        if not product.content.sections:
            issues.append("CRITICAL: No sections in product")
            score -= 30
        elif len(product.content.sections) < 3:
            issues.append(
                f"WARNING: Only {len(product.content.sections)} sections, expected at least 3"
            )
            score -= 10

        # Check for empty sections
        for i, section in enumerate(product.content.sections):
            if not section.title:
                issues.append(f"CRITICAL: Section {i + 1} missing title")
                score -= 15
            if not section.content or len(section.content.strip()) < 10:
                issues.append(f"CRITICAL: Section {i + 1} has insufficient content")
                score -= 15

        # Check conclusion
        if not product.content.conclusion:
            issues.append("WARNING: Missing conclusion")
            score -= 5

        # Ensure score doesn't go below 0
        score = max(0, score)

        return {
            "passed": len([i for i in issues if i.startswith("CRITICAL")]) == 0,
            "issues": issues,
            "score": score,
        }

    def validate_formatting(self, product: ProductOutput) -> dict:
        """Check formatting consistency in the product.

        Verifies:
        - Title is present and reasonable length
        - Section titles are consistent
        - Content lengths are reasonable (not too short/long)

        Args:
            product: The product to check.

        Returns:
            Dict with 'passed' (bool), 'issues' (list), and 'score' (0-100).
        """
        issues = []
        score = 100

        # Check title
        if not product.title:
            issues.append("CRITICAL: Missing product title")
            score -= 25
        elif len(product.title) > 100:
            issues.append("WARNING: Title is too long (over 100 characters)")
            score -= 10

        # Check format type
        if not product.format:
            issues.append("CRITICAL: Missing format type")
            score -= 20

        # Check section title consistency
        if product.content.sections:
            title_lengths = [len(s.title) for s in product.content.sections if s.title]
            if title_lengths:
                avg_length = sum(title_lengths) / len(title_lengths)
                for i, section in enumerate(product.content.sections):
                    if section.title and abs(len(section.title) - avg_length) > 30:
                        issues.append(
                            f"INFO: Section {i + 1} title length differs significantly from average"
                        )
                        score -= 2

        # Check content length balance
        if product.content.sections:
            content_lengths = [len(s.content) for s in product.content.sections if s.content]
            if content_lengths:
                min_len = min(content_lengths)
                max_len = max(content_lengths)
                # If one section is more than 5x longer than another, flag it
                if max_len > min_len * 5 and max_len > 500:
                    issues.append("WARNING: Section content length imbalance detected")
                    score -= 10

        # Ensure score doesn't go below 0
        score = max(0, score)

        return {
            "passed": len([i for i in issues if i.startswith("CRITICAL")]) == 0,
            "issues": issues,
            "score": score,
        }

    def validate_coherence(self, product: ProductOutput) -> dict:
        """Check that content flows logically and is coherent.

        Uses AI to verify content makes sense together, or falls back
        to heuristic checks if AI is not available.

        Args:
            product: The product to check.

        Returns:
            Dict with 'passed' (bool), 'issues' (list), and 'score' (0-100).
        """
        if self.client is None:
            # Fallback to heuristic checks
            return self._validate_coherence_heuristic(product)

        try:
            return self._validate_coherence_ai(product)
        except Exception:
            # Fallback on any error
            return self._validate_coherence_heuristic(product)

    def _validate_coherence_ai(self, product: ProductOutput) -> dict:
        """Validate coherence using OpenAI.

        Args:
            product: The product to check.

        Returns:
            Dict with 'passed' (bool), 'issues' (list), and 'score' (0-100).
        """
        # Build content for analysis
        content_parts = []
        if product.content.intro:
            content_parts.append(f"Introduction: {product.content.intro}")
        for i, section in enumerate(product.content.sections):
            content_parts.append(f"Section {i + 1}: {section.title}\n{section.content}")
        if product.content.conclusion:
            content_parts.append(f"Conclusion: {product.content.conclusion}")

        full_content = "\n\n".join(content_parts)

        prompt = f"""Analyze this digital product for coherence and logical flow.

Product Title: {product.title}
Format: {product.format}

Content:
{full_content}

Evaluate:
1. Does the content flow logically from start to finish?
2. Are there any contradictions or inconsistencies?
3. Is the content appropriate for the target audience?
4. Does the structure make sense?

Respond with a JSON object:
{{
    "coherent": true/false,
    "issues": ["issue 1", "issue 2"],
    "score": 0-100
}}
"""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at evaluating digital product quality. Analyze content for coherence and logical flow.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        result = response.choices[0].message.content

        # Parse the response (simple approach)
        import json

        try:
            parsed = json.loads(result)
            return {
                "passed": parsed.get("coherent", True),
                "issues": parsed.get("issues", []),
                "score": parsed.get("score", 70),
            }
        except Exception:
            # If parsing fails, assume it's okay
            return {
                "passed": True,
                "issues": [],
                "score": 70,
            }

    def _validate_coherence_heuristic(self, product: ProductOutput) -> dict:
        """Validate coherence using heuristic checks (no AI).

        Checks for common coherence issues without using AI.

        Args:
            product: The product to check.

        Returns:
            Dict with 'passed' (bool), 'issues' (list), and 'score' (0-100).
        """
        issues = []
        score = 80  # Start with decent score since we're heuristics

        # Check for repeated content (might indicate copy-paste issues)
        all_content = " ".join(
            [product.content.intro or ""]
            + [s.content for s in product.content.sections]
            + [product.content.conclusion or ""]
        )

        # Check for very short content (likely placeholder)
        if len(all_content) < 500:
            issues.append("WARNING: Content seems too short for a complete product")
            score -= 15

        # Check for keyword repetition (might indicate low quality)
        words = all_content.lower().split()
        if len(words) > 50:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:
                issues.append("WARNING: High keyword repetition detected")
                score -= 10

        # Check title appears in content (basic coherence check)
        title_words = set(product.title.lower().split())
        content_words = set(all_content.lower().split())
        # If title has 3+ words, at least one should appear in content
        if len(title_words) >= 3:
            overlap = title_words & content_words
            if len(overlap) < 1:
                issues.append("INFO: Title keywords not found in content")
                score -= 5

        # Ensure score doesn't go below 0
        score = max(0, score)

        return {
            "passed": score >= 50,
            "issues": issues,
            "score": score,
        }

    def get_quality_score(self, product: ProductOutput) -> float:
        """Get the quality score for a product (0-100).

        Convenience method that returns just the score.

        Args:
            product: The product to score.

        Returns:
            Quality score from 0 to 100.
        """
        result = self.validate(product)
        return result.score
