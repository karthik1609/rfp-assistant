import os
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Generator
import tempfile
import shutil

os.environ["TESTING"] = "true"
os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com"
os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = "test-deployment"
os.environ["HF_TOKEN"] = "test-hf-token"


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir(project_root: Path) -> Path:
    return project_root / "test_documents"


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_llm_client():
    mock = AsyncMock()
    mock.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[
                Mock(
                    message=Mock(
                        content="Mocked LLM response",
                        role="assistant"
                    )
                )
            ]
        )
    )
    return mock


@pytest.fixture
def mock_azure_openai_client():
    mock = MagicMock()
    mock.chat.completions.create = AsyncMock(
        return_value=Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='{"result": "test"}',
                        role="assistant"
                    )
                )
            ],
            usage=Mock(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30
            )
        )
    )
    return mock


@pytest.fixture
def sample_rfp_text() -> str:
    return """
    REQUEST FOR PROPOSAL
    
    We are seeking proposals for a Business Process Management (BPM) solution.
    
    Requirements:
    1. The solution must support workflow automation
    2. Must integrate with existing ERP systems
    3. Must provide real-time analytics and reporting
    4. Security: Must comply with ISO 27001 standards
    
    Response Structure:
    Please provide your response in the following format:
    - Executive Summary
    - Technical Architecture
    - Implementation Plan
    - Pricing
    """


@pytest.fixture
def sample_preprocess_result():
    from backend.models import PreprocessResult
    
    return PreprocessResult(
        language="en",
        cleaned_text="We are seeking proposals for a Business Process Management solution.",
        removed_text="Contact: admin@example.com",
        key_requirements_summary="- BPM solution\n- Workflow automation",
        comparison_agreement=True,
        comparison_notes="Removed contact information"
    )


@pytest.fixture
def sample_requirements_result():
    from backend.models import RequirementsResult, RequirementItem, StructureDetectionResult
    
    return RequirementsResult(
        solution_requirements=[
            RequirementItem(
                id="SOL-001",
                source_text="The solution must support workflow automation",
                category="Technical"
            ),
            RequirementItem(
                id="SOL-002",
                source_text="Must integrate with existing ERP systems",
                category="Integration"
            )
        ],
        response_structure_requirements=[
            RequirementItem(
                id="RESP-001",
                source_text="Please provide Executive Summary",
                category="Structure"
            )
        ],
        structure_detection=StructureDetectionResult(
            has_explicit_structure=True,
            structure_type="explicit",
            detected_sections=["Executive Summary", "Technical Architecture"],
            confidence=0.8
        )
    )


@pytest.fixture
def mock_rag_system():
    mock = MagicMock()
    mock.search = Mock(return_value=[
        {"text": "Relevant context 1", "score": 0.9},
        {"text": "Relevant context 2", "score": 0.85}
    ])
    mock.get_stats = Mock(return_value={
        "index_built": True,
        "num_documents": 5,
        "num_vectors": 100,
        "embedding_dimension": 1536,
        "embedding_model": "text-embedding-3-large"
    })
    return mock


@pytest.fixture
def mock_knowledge_base():
    mock = MagicMock()
    mock.capabilities = [
        {"name": "Workflow Automation", "description": "Advanced workflow capabilities"}
    ]
    mock.case_studies = [
        {"title": "Case Study 1", "description": "Success story"}
    ]
    mock.accelerators = [
        {"name": "Accelerator 1", "description": "Quick start solution"}
    ]
    return mock


@pytest.fixture
def mock_file_upload():
    from io import BytesIO
    
    content = b"Test file content"
    file_obj = BytesIO(content)
    file_obj.name = "test_rfp.pdf"
    
    return file_obj

