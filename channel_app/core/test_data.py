import unittest

from channel_app.core.data import (
    ErrorReportDto, OperationalEventDto, mask_sensitive_data)


class MaskSensitiveDataTestCase(unittest.TestCase):
    def test_masks_query_string_credentials(self):
        raw = "GET - https://m.example/orders?api_key=SECRET123&page=1&token=abc"
        masked = mask_sensitive_data(raw)
        self.assertNotIn("SECRET123", masked)
        self.assertNotIn("abc", masked)
        self.assertIn("page=1", masked)

    def test_masks_json_fields(self):
        raw = '{"email": "john@example.com", "phone": "+90 532 111 22 33", ' \
              '"password": "pw", "city": "Istanbul"}'
        masked = mask_sensitive_data(raw)
        self.assertNotIn("john@example.com", masked)
        self.assertNotIn("532 111 22 33", masked)
        self.assertNotIn('"pw"', masked)
        self.assertIn("Istanbul", masked)

    def test_masks_free_text_email_and_phone(self):
        masked = mask_sensitive_data("contact john@example.com 05321112233")
        self.assertNotIn("john@example.com", masked)
        self.assertNotIn("05321112233", masked)

    def test_empty_value_is_returned_as_is(self):
        self.assertEqual(mask_sensitive_data(""), "")
        self.assertIsNone(mask_sensitive_data(None))


class OperationalEventRawDataTestCase(unittest.TestCase):
    def _report(self, is_ok):
        return ErrorReportDto(
            is_ok=is_ok,
            error_code="code",
            error_description="desc",
            action_content_type="order",
            action_object_id=1,
            modified_date="2026-01-01",
            raw_request="GET - https://m.example/o?api_key=KEY - "
                        '{"email": "a@b.co"}',
            raw_response='{"phone": "05321112233"}',
        )

    def test_successful_report_has_no_raw_data(self):
        event = OperationalEventDto.from_error_report(self._report(True))
        self.assertEqual(event.level, "info")
        self.assertIsNone(event.raw_data)

    def test_failed_report_has_masked_raw_data(self):
        event = OperationalEventDto.from_error_report(self._report(False))
        self.assertEqual(event.level, "error")
        dumped = str(event.raw_data)
        for secret in ("KEY", "a@b.co", "05321112233"):
            self.assertNotIn(secret, dumped)


if __name__ == "__main__":
    unittest.main()
