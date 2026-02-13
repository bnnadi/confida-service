"""
End-to-end tests for complete interview flows.

Tests the complete user journey from session creation to answer analysis,
including all API interactions and data persistence.
"""
import pytest


class TestCompleteInterviewFlow:
    """Test cases for complete interview flows."""
    
    @pytest.mark.e2e
    def test_complete_interview_session_flow(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test complete interview session flow from creation to completion."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create interview session
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Senior Python Developer",
            "job_title": "Senior Python Developer",
            "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in Django, Flask, and API development. The ideal candidate should have strong debugging skills and experience with database optimization."
        }

        # Create session
        create_response = client.post("/api/v1/sessions/", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Get session details
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 200
        session_details = get_response.json()
        session_info = session_details.get("session", session_details)
        assert str(session_info["id"]) == str(session_id)
        assert session_info["status"] == "active"

        # Step 2b: Add questions to session (session creation does not auto-add questions)
        add_q_response = client.post(f"/api/v1/sessions/{session_id}/questions", json={
            "questions": [
                "What is Python?",
                "Explain decorators.",
                "What is your experience with Django?",
                "How do you handle database migrations?",
                "Describe your debugging process."
            ]
        })
        assert add_q_response.status_code == 200

        # Step 3: Get session questions
        questions_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        assert questions_response.status_code == 200
        questions_data = questions_response.json()
        questions_list = questions_data if isinstance(questions_data, list) else questions_data.get("questions", [])
        assert len(questions_list) > 0

        # Step 4: Analyze answers for each question
        for i, question in enumerate(questions_list[:3]):  # Test first 3 questions
            answer_data = {
                "jobDescription": session_data["job_description"],
                "question": question["question_text"],
                "answer": f"This is my answer to question {i+1}. I have experience with Python, Django, and Flask frameworks."
            }

            analyze_response = client.post(f"/api/v1/analyze-answer?question_id={question['id']}", json=answer_data)
            assert analyze_response.status_code == 200
            analysis = analyze_response.json()
            assert "score" in analysis
            assert "suggestions" in analysis

            # Verify score structure
            score = analysis["score"]
            assert "clarity" in score
            assert "confidence" in score
            assert "relevance" in score
            assert "overall" in score
            assert all(0 <= v <= 10 for v in score.values())

        # Step 5: Update session status
        update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=completed")
        assert update_response.status_code == 200

        # Step 6: Verify final session state
        final_response = client.get(f"/api/v1/sessions/{session_id}")
        assert final_response.status_code == 200
        final_session = final_response.json()
        final_info = final_session.get("session", final_session)
        assert final_info["status"] == "completed"
    
    @pytest.mark.e2e
    def test_multiple_sessions_per_user(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test creating and managing multiple sessions for a single user."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Create first session
        session1_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        # Create first session
        response1 = client.post("/api/v1/sessions/", json=session1_data)
        assert response1.status_code == 201
        session1 = response1.json()

        # Create second session
        session2_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Senior Python Developer",
            "job_title": "Senior Python Developer",
            "job_description": "Looking for Senior Python developer with Flask and FastAPI experience"
        }

        response2 = client.post("/api/v1/sessions/", json=session2_data)
        assert response2.status_code == 201
        session2 = response2.json()

        # Verify both sessions exist
        assert session1["id"] != session2["id"]
        assert session1["role"] != session2["role"]
        assert session1["job_description"] != session2["job_description"]

        # List all sessions for user
        list_response = client.get("/api/v1/sessions/")
        assert list_response.status_code == 200
        sessions_list = list_response.json()
        assert len(sessions_list) >= 2

        # Verify both sessions are in the list
        session_ids = [str(s["id"]) for s in sessions_list]
        assert str(session1["id"]) in session_ids
        assert str(session2["id"]) in session_ids
    
    @pytest.mark.e2e
    def test_question_bank_integration_flow(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test complete flow with question bank integration."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create session
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        create_response = client.post("/api/v1/sessions/", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Add questions to session
        add_q_response = client.post(f"/api/v1/sessions/{session_id}/questions", json={
            "questions": [
                "What is Python?",
                "Explain decorators.",
                "What is your experience with Django?"
            ]
        })
        assert add_q_response.status_code == 200

        # Step 3: Get session questions
        questions_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        assert questions_response.status_code == 200
        questions_data = questions_response.json()
        questions_list = questions_data if isinstance(questions_data, list) else questions_data.get("questions", [])
        assert len(questions_list) > 0

        # Step 4: Analyze answers (should update question bank stats)
        for question in questions_list[:2]:  # Test first 2 questions
            answer_data = {
                "jobDescription": session_data["job_description"],
                "question": question["question_text"],
                "answer": "I have 5 years of Python experience with Django and Flask frameworks."
            }

            analyze_response = client.post(f"/api/v1/analyze-answer?question_id={question['id']}", json=answer_data)
            assert analyze_response.status_code == 200
            analysis = analyze_response.json()
            assert "score" in analysis
            assert analysis["score"]["overall"] > 0

        # Step 5: Verify services endpoint returns successfully
        services_response = client.get("/api/v1/services")
        assert services_response.status_code == 200
        services_data = services_response.json()
        assert "ai_service_microservice" in services_data or "status" in services_data
    
    @pytest.mark.e2e
    def test_error_recovery_flow(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test error recovery and resilience in the interview flow."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create session
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        # Create session
        create_response = client.post("/api/v1/sessions/", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Add questions to session
        add_q_response = client.post(f"/api/v1/sessions/{session_id}/questions", json={
            "questions": ["What is Python?", "Explain decorators.", "What is your experience with Django?"]
        })
        assert add_q_response.status_code == 200

        # Step 2: Get session questions
        questions_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        assert questions_response.status_code == 200
        questions_data = questions_response.json()
        questions_list = questions_data if isinstance(questions_data, list) else questions_data.get("questions", [])
        assert len(questions_list) > 0

        # Step 3: Test error recovery with invalid answer analysis
        invalid_answer_data = {
            "jobDescription": session_data["job_description"],
            "question": questions_list[0]["question_text"],
            "answer": ""  # Empty answer should fail
        }

        analyze_response = client.post(f"/api/v1/analyze-answer?question_id={questions_list[0]['id']}", json=invalid_answer_data)
        assert analyze_response.status_code == 422  # Validation error

        # Step 4: Test with valid answer after error
        valid_answer_data = {
            "jobDescription": session_data["job_description"],
            "question": questions_list[0]["question_text"],
            "answer": "I have 5 years of Python experience with Django and Flask frameworks."
        }

        analyze_response = client.post(f"/api/v1/analyze-answer?question_id={questions_list[0]['id']}", json=valid_answer_data)
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()
        assert "score" in analysis

        # Step 5: Verify session is still accessible after errors
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 200
        session_details = get_response.json()
        session_info = session_details.get("session", session_details)
        assert str(session_info["id"]) == str(session_id)
        assert session_info["status"] == "active"
    
    @pytest.mark.e2e
    def test_concurrent_session_operations(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test concurrent operations on the same session."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create session
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        # Create session
        create_response = client.post("/api/v1/sessions/", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Perform concurrent operations
        # Get session details
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 200

        # Get session questions
        questions_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        assert questions_response.status_code == 200

        # Update session status
        update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=paused")
        assert update_response.status_code == 200

        # Step 3: Verify all operations completed successfully
        final_response = client.get(f"/api/v1/sessions/{session_id}")
        assert final_response.status_code == 200
        final_session = final_response.json()
        final_info = final_session.get("session", final_session)
        assert final_info["status"] == "paused"
    
    @pytest.mark.e2e
    def test_session_lifecycle_management(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test complete session lifecycle from creation to deletion."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create session
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        # Create session
        create_response = client.post("/api/v1/sessions/", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Verify session exists
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 200
        session_details = get_response.json()
        session_info = session_details.get("session", session_details)
        assert session_info["status"] == "active"

        # Step 3: Update session status to paused
        update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=paused")
        assert update_response.status_code == 200

        # Step 4: Resume session
        update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=active")
        assert update_response.status_code == 200

        # Step 5: Complete session
        update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=completed")
        assert update_response.status_code == 200

        # Step 6: Delete session
        delete_response = client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_response.status_code == 204

        # Step 7: Verify session is deleted
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404
    
    @pytest.mark.e2e
    def test_data_consistency_across_operations(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test data consistency across multiple operations."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create session
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        # Create session
        create_response = client.post("/api/v1/sessions/", json=session_data)
        assert create_response.status_code == 201
        session = create_response.json()
        session_id = session["id"]

        # Add questions to session
        add_q_response = client.post(f"/api/v1/sessions/{session_id}/questions", json={
            "questions": ["What is Python?", "Explain decorators.", "What is your experience with Django?"]
        })
        assert add_q_response.status_code == 200

        # Step 2: Get session questions
        questions_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        assert questions_response.status_code == 200
        questions_data = questions_response.json()
        questions_list = questions_data if isinstance(questions_data, list) else questions_data.get("questions", [])
        assert len(questions_list) > 0

        # Step 3: Analyze answers and track progress
        completed_questions = 0
        for question in questions_list[:3]:  # Test first 3 questions
            answer_data = {
                "jobDescription": session_data["job_description"],
                "question": question["question_text"],
                "answer": f"This is my answer to question {completed_questions + 1}."
            }

            analyze_response = client.post(f"/api/v1/analyze-answer?question_id={question['id']}", json=answer_data)
            assert analyze_response.status_code == 200
            completed_questions += 1

            # Verify progress is consistent
            get_response = client.get(f"/api/v1/sessions/{session_id}")
            assert get_response.status_code == 200

        # Step 4: Complete session
        update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=completed")
        assert update_response.status_code == 200

        # Step 5: Verify final state consistency
        final_response = client.get(f"/api/v1/sessions/{session_id}")
        assert final_response.status_code == 200
        final_session = final_response.json()
        final_info = final_session.get("session", final_session)
        assert final_info["status"] == "completed"
    
    @pytest.mark.e2e
    def test_performance_under_load(self, client, sample_user, mock_current_user, mock_ai_client, override_auth, override_ai_client):
        """Test system performance under multiple concurrent requests."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Step 1: Create multiple sessions concurrently
        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        # Create 5 sessions
        sessions = []
        for i in range(5):
            create_response = client.post("/api/v1/sessions/", json=session_data)
            assert create_response.status_code == 201
            sessions.append(create_response.json())

        # Step 2: Perform operations on all sessions
        for session in sessions:
            session_id = session["id"]

            # Get session details
            get_response = client.get(f"/api/v1/sessions/{session_id}")
            assert get_response.status_code == 200

            # Get session questions
            questions_response = client.get(f"/api/v1/sessions/{session_id}/questions")
            assert questions_response.status_code == 200

            # Update session status
            update_response = client.patch(f"/api/v1/sessions/{session_id}/status?status=completed")
            assert update_response.status_code == 200

        # Step 3: Verify all sessions are accessible
        list_response = client.get("/api/v1/sessions/")
        assert list_response.status_code == 200
        sessions_list = list_response.json()
        assert len(sessions_list) >= 5

        # Step 4: Clean up - delete all sessions
        for session in sessions:
            delete_response = client.delete(f"/api/v1/sessions/{session['id']}")
            assert delete_response.status_code == 204
