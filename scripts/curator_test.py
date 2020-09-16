from curator import env_validation, log, es_connect
import pytest

class TestLog:
    def test_log_fail(self):
        log("fake level", "Dummy log message") == None

    def test_log_pass(self, capsys):
        log("info", "Dummy log message") == {"level": "info", "message": "Dummy log message"}
        captured = capsys.readouterr()  # Capture output
        assert captured.out == '{"level": "info", "message": "Dummy log message"}\n'

class TestEnvValidation:
    def test_env_validation_fail(self):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
                env_validation(2, "", "elasticsearch:9200")
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    def test_env_validation_pass(self):
        assert env_validation(2, "infra-,app-,audit-", "elasticsearch:9200") == None
