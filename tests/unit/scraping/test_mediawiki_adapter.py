"""Unit tests for MediaWiki adapter helpers."""

from courseflow.infrastructure.scrapers.mediawiki import MediaWikiAdapter


class TestMediaWikiRedirectParsing:
    """Test redirect parsing for MediaWiki source content."""

    def test_extract_redirect_target(self) -> None:
        adapter = object.__new__(MediaWikiAdapter)
        target = adapter._extract_redirect_target(  # noqa: SLF001
            {"source": "#REDIRECT [[Biological carbon fixation]]"}
        )
        assert target == "Biological_carbon_fixation"

    def test_extract_redirect_target_with_anchor_and_alias(self) -> None:
        adapter = object.__new__(MediaWikiAdapter)
        target = adapter._extract_redirect_target(  # noqa: SLF001
            {"source": "#redirect [[Biological carbon fixation#Section|alias]]"}
        )
        assert target == "Biological_carbon_fixation"

    def test_extract_redirect_target_non_redirect(self) -> None:
        adapter = object.__new__(MediaWikiAdapter)
        target = adapter._extract_redirect_target(  # noqa: SLF001
            {"source": "Regular article content"}
        )
        assert target is None
