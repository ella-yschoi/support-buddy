"""Tests for i18n module — language detection and translation."""

from src.core.i18n import Language, detect_language, t


class TestDetectLanguage:
    def test_english_text_returns_en(self) -> None:
        assert detect_language("Files are not syncing") == Language.EN

    def test_korean_text_returns_ko(self) -> None:
        assert detect_language("파일이 동기화가 안 됩니다") == Language.KO

    def test_mixed_text_with_hangul_returns_ko(self) -> None:
        assert detect_language("sync 오류가 발생했습니다") == Language.KO

    def test_empty_text_returns_en(self) -> None:
        assert detect_language("") == Language.EN

    def test_whitespace_only_returns_en(self) -> None:
        assert detect_language("   ") == Language.EN

    def test_error_codes_only_returns_en(self) -> None:
        assert detect_language("SYNC-001 AUTH-002") == Language.EN

    def test_korean_jamo_returns_ko(self) -> None:
        assert detect_language("ㅎㅎ") == Language.KO


class TestTranslate:
    def test_returns_english_string(self) -> None:
        result = t("checklist_title", Language.EN)
        assert result == "Checklist:"

    def test_returns_korean_string(self) -> None:
        result = t("checklist_title", Language.KO)
        assert result == "체크리스트:"

    def test_missing_key_returns_key_itself(self) -> None:
        result = t("nonexistent_key", Language.EN)
        assert result == "nonexistent_key"

    def test_missing_lang_falls_back_to_english(self) -> None:
        result = t("checklist_title")
        assert result == "Checklist:"
