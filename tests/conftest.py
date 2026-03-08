import os

import pytest

from app import create_app
from models import db


@pytest.fixture()
def app():
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-bytes-minimum-value"
    os.environ["FLASK_DEBUG"] = "0"

    flask_app = create_app("testing")
    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        db.drop_all()
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def create_user_and_token(client):
    def _create(email, password, full_name, user_type="patient", age=30):
        register_resp = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": full_name,
                "user_type": user_type,
                "age": age,
            },
        )
        assert register_resp.status_code == 201
        data = register_resp.get_json()
        return data["access_token"], data["user"]

    return _create
