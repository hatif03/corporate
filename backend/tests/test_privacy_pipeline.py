from shared.privacy_pipeline import redact


def test_redacts_email_and_phone():
    text = "Contact jane.doe@example.com or call 555-123-4567 for details."
    result = redact(text)
    assert result.had_pii is True
    assert "jane.doe@example.com" not in result.redacted_text
    assert "555-123-4567" not in result.redacted_text
    assert result.found == {"EMAIL": 1, "PHONE": 1}


def test_redacts_aws_key():
    text = "leaked key: AKIAABCDEFGHIJKLMNOP in the log"
    result = redact(text)
    assert "AKIAABCDEFGHIJKLMNOP" not in result.redacted_text
    assert result.found.get("AWS_KEY") == 1


def test_clean_text_is_unmodified():
    text = "The build passed and the deploy finished in 90 seconds."
    result = redact(text)
    assert result.had_pii is False
    assert result.redacted_text == text
