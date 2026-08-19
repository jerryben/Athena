from backend.services.context_service import context_service


def test_editor_questions_detect_favorite_editor_key():
    questions = [
        "What editor do I prefer?",
        "What text editor is my favorite?",
        "Which editor have I chosen as my preferred one?",
        "Which code editor do I normally use?",
        "What is my favorite editor?",
        "Which editor do I use?",
        "What's my preferred code editor?",
    ]

    for question in questions:
        keys = context_service._detect_memory_keys(question)

        assert "favorite_editor" in keys, (
            f"Failed to detect favorite_editor for: {question}"
        )


def test_unrelated_question_does_not_detect_editor_memory():
    question = "Tell me about Docker and Kubernetes."

    keys = context_service._detect_memory_keys(question)

    assert "favorite_editor" not in keys