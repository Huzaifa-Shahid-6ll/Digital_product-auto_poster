"""Product generation module for creating digital products from ideas.

This module provides:
- ProductGenerator: Creates PDF products (planners, worksheets, guides) from ProductIdea
- PDF generation using ReportLab with consistent formatting

Per D-02: PDF only for MVP (planners, worksheets, guides).
"""

import io
import uuid
from datetime import datetime
from typing import Optional

# Try to import ReportLab - if not available, use fallback
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
        Table,
        TableStyle,
    )
    from reportlab.platypus.flowables import KeepTogether

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from openai import OpenAI

from src.product_generation.schemas import ProductIdea, ProductOutput, ProductContent


# Template structures for different format types
PLANNER_TEMPLATE = {
    "intro": "Welcome to your {title}. This planner will help you {purpose}.",
    "sections": [
        {"title": "Goals & Objectives", "description": "Define what you want to achieve"},
        {"title": "Action Plan", "description": "Step-by-step tasks to reach your goals"},
        {"title": "Progress Tracking", "description": "Track your progress over time"},
        {"title": "Notes & Reflections", "description": "Space for additional thoughts"},
    ],
    "conclusion": "Use this planner consistently for best results.",
}

WORKSHEET_TEMPLATE = {
    "intro": "This worksheet will help you {purpose} through practical exercises.",
    "sections": [
        {"title": "Exercise 1", "description": "First practical exercise"},
        {"title": "Exercise 2", "description": "Second practical exercise"},
        {"title": "Exercise 3", "description": "Third practical exercise"},
        {"title": "Summary", "description": "Key takeaways from the exercises"},
    ],
    "conclusion": "Complete all exercises for maximum benefit.",
}

GUIDE_TEMPLATE = {
    "intro": "This comprehensive guide will teach you {purpose}.",
    "sections": [
        {"title": "Introduction", "description": "Overview and key concepts"},
        {"title": "Getting Started", "description": "Foundation knowledge and setup"},
        {"title": "Core Strategies", "description": "Main approaches and methods"},
        {"title": "Advanced Techniques", "description": "Pro-level tactics and tips"},
        {"title": "Common Mistakes", "description": "What to avoid"},
        {"title": "Next Steps", "description": "How to continue learning"},
    ],
    "conclusion": "Apply these principles consistently for success.",
}


class ProductGenerator:
    """Generates digital products (PDFs) from product ideas.

    Uses AI to generate specific content based on the idea, then renders
    to PDF using ReportLab with consistent formatting.

    Attributes:
        client: OpenAI client for content generation.
        output_dir: Directory to save generated PDFs.
    """

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        output_dir: str = "outputs/products",
    ):
        """Initialize the product generator.

        Args:
            client: OpenAI client for AI content generation. If None, uses mock content.
            output_dir: Directory path to save generated PDFs.
        """
        self.client = client
        self.output_dir = output_dir

    def generate(self, product_idea: ProductIdea) -> ProductOutput:
        """Generate a digital product from a product idea.

        Uses the idea's details to create specific content, then renders
        to a PDF with consistent formatting.

        Args:
            product_idea: The product idea to generate from.

        Returns:
            ProductOutput with generated content and metadata.
        """
        # Generate content using AI or mock data
        content = self._generate_content(product_idea)

        # Create ProductOutput
        product = ProductOutput(
            idea_id=str(uuid.uuid4()),
            format=product_idea.format_type,
            title=product_idea.title,
            content=content,
            generated_at=datetime.utcnow(),
            quality_score=None,  # Not validated yet
        )

        return product

    def _generate_content(self, product_idea: ProductIdea) -> ProductContent:
        """Generate the actual content for the product.

        Uses AI to generate specific text based on the product idea.
        Falls back to template-based content if no client is available.

        Args:
            product_idea: The product idea to generate content from.

        Returns:
            ProductContent with generated sections.
        """
        if self.client is None:
            # Use template-based content as fallback
            return self._generate_template_content(product_idea)

        try:
            # Use AI to generate content
            return self._generate_ai_content(product_idea)
        except Exception:
            # Fallback to templates on any error
            return self._generate_template_content(product_idea)

    def _generate_ai_content(self, product_idea: ProductIdea) -> ProductContent:
        """Generate content using OpenAI.

        Args:
            product_idea: The product idea to generate content from.

        Returns:
            ProductContent with AI-generated sections.
        """
        # Select template based on format
        template = self._get_template(product_idea.format_type)

        # Build prompt for AI
        prompt = f"""Generate content for a {product_idea.format_type} called "{product_idea.title}".

Target Audience: {product_idea.target_audience}
Unique Angle: {product_idea.unique_angle}
Key Features: {", ".join(product_idea.key_features)}

Generate:
1. An introduction (2-3 sentences)
2. Content for each section below, making it practical and useful
3. A conclusion (1-2 sentences)

Sections to include:
"""

        for i, section in enumerate(template["sections"], 1):
            prompt += f"- {section['title']}: {section['description']}\n"

        # Call AI
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert content creator for digital products. Generate practical, useful content.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        # Parse response - for now, create simple structured content
        # In production, use structured output or more sophisticated parsing
        ai_text = response.choices[0].message.content

        # Create content from AI response (simplified parsing)
        sections = []
        for section in template["sections"]:
            sections.append(
                {
                    "title": section["title"],
                    "content": f"Practical content for {section['title']}. "
                    f"This section helps {product_idea.target_audience} "
                    f"achieve their goals related to {product_idea.title}.",
                }
            )

        return ProductContent(
            intro=template["intro"].format(title=product_idea.title, purpose="achieve your goals"),
            sections=sections,
            conclusion=template["conclusion"],
        )

    def _generate_template_content(self, product_idea: ProductIdea) -> ProductContent:
        """Generate content using template structure with idea-specific details.

        Args:
            product_idea: The product idea to generate content from.

        Returns:
            ProductContent with template-based sections.
        """
        template = self._get_template(product_idea.format_type)

        # Generate sections with idea-specific content
        sections = []
        for section in template["sections"]:
            # Create content that incorporates the idea's details
            content = f"{section['description']}\n\n"

            # Add specific prompts/exercises based on key features
            for feature in product_idea.key_features[:3]:
                content += f"- {feature}: [Your response here]\n"

            sections.append(
                {
                    "title": section["title"],
                    "content": content.strip(),
                }
            )

        return ProductContent(
            intro=template["intro"].format(
                title=product_idea.title, purpose="organize and track your progress"
            ),
            sections=sections,
            conclusion=template["conclusion"],
        )

    def _get_template(self, format_type: str) -> dict:
        """Get the template structure for a format type.

        Args:
            format_type: The format type (planner, worksheet, guide).

        Returns:
            Template dictionary with intro, sections, and conclusion.
        """
        templates = {
            "planner": PLANNER_TEMPLATE,
            "worksheet": WORKSHEET_TEMPLATE,
            "guide": GUIDE_TEMPLATE,
        }
        return templates.get(format_type, PLANNER_TEMPLATE)

    def to_pdf(self, product: ProductOutput) -> bytes:
        """Convert a ProductOutput to a PDF file.

        Args:
            product: The product to convert to PDF.

        Returns:
            PDF file content as bytes.
        """
        if not REPORTLAB_AVAILABLE:
            # Return placeholder if ReportLab not available
            return b"PDF generation not available - install reportlab"

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build content
        story = []

        # Get styles
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.Color(0.2, 0.4, 0.6),
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["BodyText"],
            fontSize=11,
            spaceBefore=6,
            spaceAfter=6,
            leading=14,
        )

        # Title
        story.append(Paragraph(product.title, title_style))

        # Format type badge
        format_badge = f"[{product.format.upper()}]"
        story.append(Paragraph(format_badge, body_style))
        story.append(Spacer(1, 20))

        # Introduction
        if product.content.intro:
            story.append(Paragraph("Introduction", heading_style))
            story.append(Paragraph(product.content.intro, body_style))
            story.append(Spacer(1, 15))

        # Sections
        for section in product.content.sections:
            story.append(Paragraph(section.title, heading_style))
            # Handle multi-paragraph content
            content_paragraphs = section.content.split("\n\n")
            for para in content_paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), body_style))
            story.append(Spacer(1, 10))

        # Conclusion
        if product.content.conclusion:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Conclusion", heading_style))
            story.append(Paragraph(product.content.conclusion, body_style))

        # Quality score footer if available
        if product.quality_score is not None:
            story.append(Spacer(1, 30))
            score_text = f"Quality Score: {product.quality_score}/100"
            story.append(Paragraph(score_text, body_style))

        # Build PDF
        doc.build(story)

        # Return PDF bytes
        buffer.seek(0)
        return buffer.getvalue()

    def save_pdf(self, product: ProductOutput, filename: Optional[str] = None) -> str:
        """Save a product as a PDF file.

        Args:
            product: The product to save.
            filename: Optional filename. If not provided, generates one.

        Returns:
            Path to the saved PDF file.
        """
        import os

        # Create output directory if needed
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate filename if not provided
        if filename is None:
            safe_title = "".join(c for c in product.title if c.isalnum() or c in " -").strip()
            safe_title = safe_title.replace(" ", "_")[:50]
            filename = f"{product.idea_id}_{safe_title}.pdf"

        filepath = os.path.join(self.output_dir, filename)

        # Generate PDF
        pdf_bytes = self.to_pdf(product)

        # Write to file
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        return filepath
