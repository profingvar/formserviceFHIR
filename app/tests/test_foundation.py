"""Phase 1 foundation tests — verify project setup is functional."""
import importlib
import os


class TestVenvAndDependencies:
    """Verify virtual environment and all dependencies import correctly."""

    def test_flask_imports(self):
        import flask
        assert flask.__version__

    def test_sqlalchemy_imports(self):
        import sqlalchemy
        assert sqlalchemy.__version__

    def test_jwt_imports(self):
        import jwt
        assert jwt.__version__

    def test_bcrypt_imports(self):
        import bcrypt
        assert bcrypt.__version__

    def test_dotenv_imports(self):
        import dotenv
        assert dotenv

    def test_flask_wtf_imports(self):
        import flask_wtf
        assert flask_wtf

    def test_flask_cors_imports(self):
        import flask_cors
        assert flask_cors

    def test_fhir_resources_imports(self):
        from fhir.resources.R4B.patient import Patient
        assert Patient

    def test_psycopg2_imports(self):
        import psycopg2
        assert psycopg2


class TestAppFactory:
    """Verify Flask app factory creates a working application."""

    def test_create_app(self):
        from src.app import create_app
        app = create_app()
        assert app is not None

    def test_create_app_testing_mode(self):
        from src.app import create_app
        app = create_app({"TESTING": True})
        assert app.config["TESTING"] is True

    def test_health_endpoint(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


class TestProjectStructure:
    """Verify required directories and files exist."""

    BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_src_directory(self):
        assert os.path.isdir(os.path.join(self.BASE, "src"))

    def test_models_package(self):
        init = os.path.join(self.BASE, "src", "models", "__init__.py")
        assert os.path.isfile(init)

    def test_routes_package(self):
        init = os.path.join(self.BASE, "src", "routes", "__init__.py")
        assert os.path.isfile(init)

    def test_services_package(self):
        init = os.path.join(self.BASE, "src", "services", "__init__.py")
        assert os.path.isfile(init)

    def test_middleware_package(self):
        init = os.path.join(self.BASE, "src", "middleware", "__init__.py")
        assert os.path.isfile(init)

    def test_fhir_package(self):
        init = os.path.join(self.BASE, "src", "fhir", "__init__.py")
        assert os.path.isfile(init)

    def test_templates_directory(self):
        assert os.path.isdir(os.path.join(self.BASE, "src", "templates"))

    def test_tests_directory(self):
        assert os.path.isdir(os.path.join(self.BASE, "tests"))

    def test_scripts_directory(self):
        assert os.path.isdir(os.path.join(self.BASE, "scripts"))

    def test_env_example_exists(self):
        assert os.path.isfile(os.path.join(self.BASE, ".env.example"))

    def test_requirements_exists(self):
        assert os.path.isfile(os.path.join(self.BASE, "requirements.txt"))

    def test_dockerfile_exists(self):
        assert os.path.isfile(os.path.join(self.BASE, "Dockerfile"))

    def test_docker_compose_exists(self):
        assert os.path.isfile(os.path.join(self.BASE, "docker-compose.yml"))


class TestStartScript:
    """Verify start.sh exists and is executable."""

    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def test_start_sh_exists(self):
        assert os.path.isfile(os.path.join(self.ROOT, "start.sh"))

    def test_start_sh_executable(self):
        path = os.path.join(self.ROOT, "start.sh")
        assert os.access(path, os.X_OK)

    def test_safe_restart_exists(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.isfile(os.path.join(base, "safe_restart.sh"))

    def test_safe_restart_executable(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "safe_restart.sh")
        assert os.access(path, os.X_OK)
