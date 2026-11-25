"""
tests.unit.test_payloads - curator.payloads.sent_fields

The search save routes pass source and search_url on only when the request
carries them: the proc treats a present key as "set (blank clears)" and an
absent key as "keep", so adding a key the client never sent would blank it.
"""

from curator.payloads import sent_fields

KEYS = ("source", "search_url")


class TestSentFields:
    def test_only_keys_present_in_the_body_are_returned(self):
        body = {"search_terms": "Boyle", "source": "Ancestry"}

        assert sent_fields(body, KEYS) == {"source": "Ancestry"}

    def test_absent_keys_are_not_added(self):
        assert sent_fields({"search_terms": "Boyle"}, KEYS) == {}

    def test_blank_string_becomes_none_so_the_proc_clears_it(self):
        assert sent_fields({"search_url": ""}, KEYS) == {"search_url": None}

    def test_whitespace_only_becomes_none(self):
        assert sent_fields({"source": "   "}, KEYS) == {"source": None}

    def test_explicit_none_stays_none(self):
        assert sent_fields({"source": None}, KEYS) == {"source": None}

    def test_surrounding_whitespace_is_trimmed(self):
        body = {"search_url": "  https://example.test/a  "}

        assert sent_fields(body, KEYS) == {"search_url": "https://example.test/a"}

    def test_both_keys_when_both_sent(self):
        body = {"source": "Ancestry", "search_url": "https://example.test/a"}

        assert sent_fields(body, KEYS) == body

    def test_key_order_follows_the_keys_argument(self):
        body = {"search_url": "u", "source": "s"}

        assert list(sent_fields(body, KEYS)) == ["source", "search_url"]

    def test_empty_body_gives_nothing(self):
        assert sent_fields({}, KEYS) == {}
