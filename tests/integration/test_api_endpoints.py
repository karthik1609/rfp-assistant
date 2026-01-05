import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestProcessRFP:
    
    @patch("backend.app.extract_text_from_file")
    def test_process_rfp_success(self, mock_extract, client, mock_file_upload):
        mock_extract.return_value = "Sample RFP text"
        
        # FastAPI expects files parameter name to match the endpoint parameter
        # The endpoint uses `files: List[UploadFile] = File(...)`
        files = {"files": ("test.pdf", mock_file_upload.read(), "application/pdf")}
        mock_file_upload.seek(0)  # Reset file pointer
        
        response = client.post("/process-rfp", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "ocr_source_text" in data
        assert data["ocr_source_text"] == "Sample RFP text"
    
    def test_process_rfp_no_file(self, client):
        response = client.post("/process-rfp")
        assert response.status_code == 422


class TestPreprocessEndpoint:
    
    @patch("backend.app.run_preprocess_agent")
    def test_run_preprocess_success(self, mock_preprocess, client, sample_rfp_text):
        from backend.models import PreprocessResult
        
        mock_preprocess.return_value = PreprocessResult(
            language="en",
            cleaned_text="Cleaned text",
            removed_text="Removed",
            key_requirements_summary="- Summary"
        )
        
        payload = {
            "ocr_text": sample_rfp_text
        }
        response = client.post("/run-preprocess", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "language" in data
        assert data["language"] == "en"
    
    def test_run_preprocess_invalid_payload(self, client):
        response = client.post("/run-preprocess", json={})
        assert response.status_code == 422


class TestRequirementsEndpoint:
    @patch("backend.app.run_requirements_agent")
    @patch("backend.app.detect_structure")
    def test_run_requirements_success(self, mock_detect, mock_requirements, client, sample_preprocess_result):
        from backend.models import RequirementsResult, RequirementItem, StructureDetectionResult
        
        mock_requirements.return_value = RequirementsResult(
            solution_requirements=[
                RequirementItem(
                    id="SOL-001",
                    source_text="Requirement text",
                    category="Technical"
                )
            ],
            response_structure_requirements=[]
        )
        mock_detect.return_value = {
            "has_explicit_structure": False,
            "structure_type": "none",
            "detected_sections": [],
            "confidence": 0.0
        }
        
        payload = {
            "essential_text": sample_preprocess_result.cleaned_text
        }
        response = client.post("/run-requirements", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "solution_requirements" in data


class TestBuildQueryEndpoint:
    
    @patch("backend.app.build_query")
    def test_build_query_success(self, mock_build_query, client, sample_preprocess_result, sample_requirements_result):
        from backend.models import BuildQuery
        
        mock_build_query.return_value = BuildQuery(
            query_text="Build query text",
            solution_requirements_summary="Summary",
            response_structure_requirements_summary="Structure",
            extraction_data={"language": "en"}
        )
        
        payload = {
            "preprocess": sample_preprocess_result.to_dict(),
            "requirements": sample_requirements_result.to_dict()
        }
        response = client.post("/build-query", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "query_text" in data


class TestGenerateResponseEndpoint:
    @patch("backend.app._generate_per_requirement_response")
    @patch("backend.app._generate_structured_response")
    def test_generate_response_success(
        self, mock_structured, mock_per_req, client,
        sample_preprocess_result, sample_requirements_result
    ):
        from fastapi.responses import JSONResponse
        
        # Mock both response paths (structured and per-requirement)
        mock_response_data = {
            "responses": [
                {
                    "requirement_id": "SOL-001",
                    "response_text": "Generated response",
                    "quality_score": 0.9
                }
            ],
            "total_requirements": 1
        }
        mock_per_req.return_value = JSONResponse(content=mock_response_data)
        mock_structured.return_value = JSONResponse(content={"response_text": "Structured response"})
        
        payload = {
            "preprocess": sample_preprocess_result.to_dict(),
            "requirements": sample_requirements_result.to_dict(),
            "use_rag": True
        }
        response = client.post("/generate-response", json=payload)
        
        assert response.status_code == 200


class TestQuestionEndpoints:
    
    @patch("backend.app.analyze_build_query_for_questions_legacy")
    @patch("backend.app._setup_rag_and_kb")
    def test_generate_questions_success(self, mock_setup, mock_analyze, client, mock_rag_system):
        from backend.models import BuildQuery
        
        mock_setup.return_value = (mock_rag_system, None)
        mock_analyze.return_value = [
            {
                "question_text": "What is the deadline?",
                "context": "Context",
                "category": "business",
                "priority": "high"
            }
        ]
        
        build_query_obj = BuildQuery(
            query_text="Query text",
            solution_requirements_summary="Summary",
            response_structure_requirements_summary="Structure",
            extraction_data={"language": "en"}
        )
        
        payload = {
            "build_query": build_query_obj.model_dump()
        }
        response = client.post("/generate-questions", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
    
    @patch("backend.app.get_next_critical_question")
    @patch("backend.app._setup_rag_and_kb")
    @patch("backend.app.get_company_kb")
    def test_get_next_question_success(self, mock_get_kb, mock_setup, mock_get_next, client, sample_requirements_result, mock_knowledge_base, mock_rag_system):
        mock_get_kb.return_value = mock_knowledge_base
        mock_setup.return_value = (mock_rag_system, None)
        
        # get_next_critical_question returns (question_dict, remaining_gaps, updated_rag)
        mock_get_next.return_value = (
            {
                "question_text": "Next question?",
                "context": "Context",
                "category": "tech",
                "priority": "high"
            },
            2,  # remaining_gaps
            {}  # updated_rag
        )
        
        payload = {
            "requirements": sample_requirements_result.to_dict(),
            "session_id": "test-session"
        }
        response = client.post("/get-next-question", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "question" in data or "message" in data


class TestChatEndpoints:
    
    def test_create_chat_session(self, client):
        payload = {}
        response = client.post("/chat/session", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    def test_get_chat_session(self, client):
        # Create a session first
        create_response = client.post("/chat/session", json={})
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]
        
        # Then retrieve it
        response = client.get(f"/chat/session/{session_id}")
        assert response.status_code == 200

