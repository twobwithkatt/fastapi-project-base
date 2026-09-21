import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.models.posts import Post
from datetime import datetime

client = TestClient(app)

def test_api_post_with_singleflight():
    mock_post_data = {
        "id": 1,
        "title": "Title 1",
        "content": "Content 1",
        "category_id": 10,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    with patch("app.repository.post_repo.PostRepository.get_post_by_id") as mock_get:
        mock_post = MagicMock()
        setattr(mock_post, "__to_dict__", lambda: mock_post_data)
        mock_get.return_value = mock_post

        # Gọi endpoint GET /api/posts/1
        response = client.get("/api/posts/1")
        assert response.status_code == 200
        assert response.json()["title"] == "Title 1"


def test_api_async_singleflight_endpoint():
    mock_post_data = {
        "id": 2,
        "title": "Async Title",
        "content": "Async Content",
        "category_id": 10,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    with patch("app.repository.post_repo.PostRepository.get_post_by_id") as mock_get:
        mock_post = MagicMock()
        setattr(mock_post, "__to_dict__", lambda: mock_post_data)
        mock_get.return_value = mock_post

        response = client.get("/api/posts/2/async-singleflight")
        assert response.status_code == 200
        assert response.json()["title"] == "Async Title"

