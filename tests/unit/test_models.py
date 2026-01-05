import pytest
from pydantic import ValidationError

from backend.models import (
    ExtractionResult,
    PreprocessResult,
    RequirementItem,
    RequirementsResult,
    StructureDetectionResult,
    BuildQuery,
    Question,
    Answer,
    ConversationContext,
)


class TestExtractionResult:
    
    def test_valid_extraction_result(self):
        result = ExtractionResult(
            language="en",
            translated_text="Extracted text",
            key_requirements_summary="- Requirement 1"
        )
        assert result.language == "en"
        assert result.translated_text == "Extracted text"
        assert result.key_requirements_summary == "- Requirement 1"
    
    def test_extraction_result_defaults(self):
        result = ExtractionResult(language="en")
        assert result.translated_text == ""
        assert result.raw_structured == {}


class TestPreprocessResult:
    
    def test_valid_preprocess_result(self):
        result = PreprocessResult(
            language="en",
            cleaned_text="Cleaned text content",
            removed_text="Removed content",
            key_requirements_summary="- Summary",
            comparison_agreement=True
        )
        assert result.language == "en"
        assert result.comparison_agreement is True
    
    def test_preprocess_result_to_dict(self):
        result = PreprocessResult(
            language="en",
            cleaned_text="Test"
        )
        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["language"] == "en"
        assert data["cleaned_text"] == "Test"


class TestRequirementItem:
    
    def test_valid_requirement_item(self):
        item = RequirementItem(
            id="SOL-001",
            source_text="Requirement text",
            category="Technical"
        )
        assert item.id == "SOL-001"
        assert item.category == "Technical"
    
    def test_requirement_item_extra_fields_ignored(self):
        item = RequirementItem(
            id="SOL-001",
            source_text="Text",
            category="Tech",
            extra_field="should be ignored"
        )
        assert not hasattr(item, "extra_field")


class TestRequirementsResult:
    
    def test_valid_requirements_result(self):
        result = RequirementsResult(
            solution_requirements=[
                RequirementItem(id="SOL-001", source_text="Text", category="Tech")
            ],
            response_structure_requirements=[],
            notes="Test notes"
        )
        assert len(result.solution_requirements) == 1
        assert result.notes == "Test notes"
    
    def test_requirements_result_with_structure_detection(self, sample_requirements_result):
        assert sample_requirements_result.structure_detection is not None
        assert sample_requirements_result.structure_detection.has_explicit_structure is True


class TestStructureDetectionResult:
    
    def test_valid_structure_detection(self):
        result = StructureDetectionResult(
            has_explicit_structure=True,
            structure_type="explicit",
            detected_sections=["Section 1", "Section 2"],
            confidence=0.8
        )
        assert result.confidence == 0.8
        assert len(result.detected_sections) == 2
    
    def test_confidence_bounds(self):
        result = StructureDetectionResult(
            has_explicit_structure=True,
            structure_type="explicit",
            confidence=0.5
        )
        assert result.confidence == 0.5
        
        with pytest.raises(ValidationError):
            StructureDetectionResult(
                has_explicit_structure=True,
                structure_type="explicit",
                confidence=1.5  # > 1.0
            )


class TestBuildQuery:
    
    def test_valid_build_query(self):
        query = BuildQuery(
            query_text="Build query text",
            solution_requirements_summary="Solution summary",
            response_structure_requirements_summary="Structure summary",
            extraction_data={"language": "en"}
        )
        assert query.confirmed is False
        assert query.extraction_data["language"] == "en"
    
    def test_build_query_confirmed(self):
        query = BuildQuery(
            query_text="Text",
            solution_requirements_summary="Summary",
            response_structure_requirements_summary="Structure",
            extraction_data={},
            confirmed=True
        )
        assert query.confirmed is True


class TestQuestion:
    
    def test_valid_question(self):
        question = Question(
            question_id="Q1",
            question_text="What is the deadline?",
            context="Need to know timeline",
            category="business",
            priority="high"
        )
        assert question.question_id == "Q1"
        assert question.answered is False
        assert question.requirement_id is None


class TestAnswer:
    
    def test_valid_answer(self):
        answer = Answer(
            question_id="Q1",
            answer_text="The deadline is Q2 2024"
        )
        assert answer.question_id == "Q1"
        assert answer.answer_text == "The deadline is Q2 2024"


class TestConversationContext:
    
    def test_valid_conversation_context(self):
        context = ConversationContext(
            session_id="session-123",
            questions=[
                Question(
                    question_id="Q1",
                    question_text="Question?",
                    context="Context",
                    category="tech",
                    priority="high"
                )
            ],
            answers=[]
        )
        assert context.session_id == "session-123"
        assert len(context.questions) == 1
    
    def test_get_answer_for_question(self):
        context = ConversationContext(
            session_id="session-123",
            questions=[
                Question(
                    question_id="Q1",
                    question_text="Question?",
                    context="Context",
                    category="tech",
                    priority="high"
                )
            ],
            answers=[
                Answer(question_id="Q1", answer_text="Answer")
            ]
        )
        answer = context.get_answer_for_question("Q1")
        assert answer == "Answer"
        assert context.get_answer_for_question("Q2") is None
    
    def test_get_qa_context(self):
        context = ConversationContext(
            session_id="session-123",
            questions=[
                Question(
                    question_id="Q1",
                    question_text="What is the deadline?",
                    context="Context",
                    category="business",
                    priority="high"
                )
            ],
            answers=[
                Answer(question_id="Q1", answer_text="Q2 2024")
            ]
        )
        qa_context = context.get_qa_context()
        assert "Q: What is the deadline?" in qa_context
        assert "A: Q2 2024" in qa_context
    
    def test_get_qa_context_empty(self):
        context = ConversationContext(session_id="session-123")
        qa_context = context.get_qa_context()
        assert qa_context == ""

