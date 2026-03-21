"""Comprehensive tests for AnyBrowse block."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from backend.blocks.anybrowse import AnyBrowseScrapeBlock
from backend.blocks.anybrowse._auth import (
    TEST_CREDENTIALS,
    TEST_CREDENTIALS_INPUT,
    AnyBrowseCredentials,
)
from backend.data.execution import ExecutionContext
from backend.util.request import Response


def make_test_context(
    graph_exec_id: str = "test-exec-id",
    user_id: str = "test-user-id",
) -> ExecutionContext:
    """Helper to create test ExecutionContext."""
    return ExecutionContext(
        user_id=user_id,
        graph_exec_id=graph_exec_id,
    )


class TestAnyBrowseBlock:
    """Test suite for AnyBrowseScrapeBlock."""

    @pytest.fixture
    def block(self):
        """Create an AnyBrowse block instance."""
        return AnyBrowseScrapeBlock()

    @pytest.fixture
    def mock_success_response(self):
        """Mock a successful HTTP response from AnyBrowse API."""
        response = MagicMock(spec=Response)
        response.status = 200
        response.json.return_value = {
            "markdown": "# Example Domain\n\nThis domain is for use in illustrative examples."
        }
        return response

    @pytest.fixture
    def mock_error_response(self):
        """Mock an error HTTP response from AnyBrowse API."""
        response = MagicMock(spec=Response)
        response.status = 429
        response.json.return_value = {"error": "Rate limit exceeded"}
        return response

    @pytest.fixture
    def credentials_with_key(self):
        """Create AnyBrowse credentials with API key."""
        return AnyBrowseCredentials(
            id="test-anybrowse-creds",
            provider="anybrowse",
            api_key=SecretStr("test-api-key"),
            title="Test AnyBrowse API Key",
            expires_at=None,
        )

    def test_block_instantiation(self, block):
        """Test that block is properly instantiated with correct attributes."""
        assert block.name == "AnyBrowseScrapeBlock"
        assert block.id == "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e"
        assert block.description.startswith("Scrape web pages bypassing Cloudflare")
        assert "SEARCH" in str(block.categories)

    def test_input_schema_fields(self, block):
        """Test that all required input schema fields are present."""
        fields = block.input_schema.model_fields
        assert "url" in fields
        assert "credentials" in fields

    def test_output_schema_fields(self, block):
        """Test that all required output schema fields are present."""
        fields = block.output_schema.model_fields
        assert "markdown" in fields
        assert "error" in fields

    def test_test_credentials_valid(self):
        """Test that test credentials are properly defined."""
        assert TEST_CREDENTIALS.provider == "anybrowse"
        assert TEST_CREDENTIALS.api_key.get_secret_value() == "mock-anybrowse-api-key"
        assert TEST_CREDENTIALS_INPUT["provider"] == "anybrowse"

    @pytest.mark.asyncio
    @patch("backend.blocks.anybrowse.scrape.Requests")
    async def test_scrape_success_with_api_key(
        self,
        mock_requests_class,
        block,
        mock_success_response,
        credentials_with_key,
    ):
        """Test successful scrape with API key."""
        # Setup mocks
        mock_requests = AsyncMock()
        mock_requests.post.return_value = mock_success_response
        mock_requests_class.return_value = mock_requests

        # Prepare input data
        input_data = AnyBrowseScrapeBlock.Input(
            url="https://example.com",
            credentials={
                "provider": "anybrowse",
                "id": "test-creds",
                "type": "api_key",
                "title": "Test Key",
            },
        )

        # Execute block
        result = []
        async for output_name, output_data in block.run(
            input_data,
            credentials=credentials_with_key,
            execution_context=make_test_context(),
        ):
            result.append((output_name, output_data))

        # Verify request was made correctly
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args.kwargs["url"] == "https://anybrowse.dev/scrape"
        assert call_args.kwargs["json"] == {"url": "https://example.com"}
        assert call_args.kwargs["headers"]["x-api-key"] == "test-api-key"

        # Verify response handling
        assert len(result) == 1
        assert result[0][0] == "markdown"
        assert "Example Domain" in result[0][1]

    @pytest.mark.asyncio
    @patch("backend.blocks.anybrowse.scrape.Requests")
    async def test_scrape_success_without_api_key(
        self,
        mock_requests_class,
        block,
        mock_success_response,
    ):
        """Test successful scrape without API key (free tier)."""
        # Setup mocks
        mock_requests = AsyncMock()
        mock_requests.post.return_value = mock_success_response
        mock_requests_class.return_value = mock_requests

        # Prepare input data without credentials
        input_data = AnyBrowseScrapeBlock.Input(
            url="https://example.org",
            credentials={
                "provider": "anybrowse",
                "id": "",
                "type": "api_key",
                "title": "",
            },
        )

        # Execute block with no credentials
        result = []
        async for output_name, output_data in block.run(
            input_data,
            credentials=None,
            execution_context=make_test_context(),
        ):
            result.append((output_name, output_data))

        # Verify request was made without API key header
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args.kwargs["url"] == "https://anybrowse.dev/scrape"
        assert call_args.kwargs["json"] == {"url": "https://example.org"}
        # No x-api-key header when credentials are not provided
        assert "x-api-key" not in call_args.kwargs["headers"]

        # Verify response handling
        assert len(result) == 1
        assert result[0][0] == "markdown"

    @pytest.mark.asyncio
    @patch("backend.blocks.anybrowse.scrape.Requests")
    async def test_scrape_handles_exception(
        self,
        mock_requests_class,
        block,
        credentials_with_key,
    ):
        """Test that block properly handles exceptions."""
        # Setup mocks to raise exception
        mock_requests = AsyncMock()
        mock_requests.post.side_effect = Exception("Connection timeout")
        mock_requests_class.return_value = mock_requests

        # Prepare input data
        input_data = AnyBrowseScrapeBlock.Input(
            url="https://example.com",
            credentials={
                "provider": "anybrowse",
                "id": "test-creds",
                "type": "api_key",
                "title": "Test Key",
            },
        )

        # Execute block
        result = []
        async for output_name, output_data in block.run(
            input_data,
            credentials=credentials_with_key,
            execution_context=make_test_context(),
        ):
            result.append((output_name, output_data))

        # Verify error handling
        assert len(result) == 1
        assert result[0][0] == "error"
        assert "Failed to scrape" in result[0][1]
        assert "Connection timeout" in result[0][1]

    @pytest.mark.asyncio
    @patch("backend.blocks.anybrowse.scrape.Requests")
    async def test_scrape_empty_markdown(
        self,
        mock_requests_class,
        block,
        credentials_with_key,
    ):
        """Test handling of empty markdown response."""
        # Setup mocks to return empty markdown
        mock_response = MagicMock(spec=Response)
        mock_response.status = 200
        mock_response.json.return_value = {"markdown": ""}

        mock_requests = AsyncMock()
        mock_requests.post.return_value = mock_response
        mock_requests_class.return_value = mock_requests

        # Prepare input data
        input_data = AnyBrowseScrapeBlock.Input(
            url="https://example.com",
            credentials={
                "provider": "anybrowse",
                "id": "test-creds",
                "type": "api_key",
                "title": "Test Key",
            },
        )

        # Execute block
        result = []
        async for output_name, output_data in block.run(
            input_data,
            credentials=credentials_with_key,
            execution_context=make_test_context(),
        ):
            result.append((output_name, output_data))

        # Verify empty markdown is yielded (not an error)
        assert len(result) == 1
        assert result[0][0] == "markdown"
        assert result[0][1] == ""

    @pytest.mark.asyncio
    @patch("backend.blocks.anybrowse.scrape.Requests")
    async def test_scrape_with_various_urls(
        self,
        mock_requests_class,
        block,
        mock_success_response,
        credentials_with_key,
    ):
        """Test scraping various URLs including Cloudflare-protected sites."""
        test_urls = [
            "https://www.nytimes.com/2024/01/15/business/example-article",
            "https://www.linkedin.com/in/johndoe",
            "https://www.amazon.com/dp/product123",
            "https://www.gov.uk/guidance/example",
        ]

        mock_requests = AsyncMock()
        mock_requests.post.return_value = mock_success_response
        mock_requests_class.return_value = mock_requests

        for url in test_urls:
            mock_requests.reset_mock()

            input_data = AnyBrowseScrapeBlock.Input(
                url=url,
                credentials={
                    "provider": "anybrowse",
                    "id": "test-creds",
                    "type": "api_key",
                    "title": "Test Key",
                },
            )

            result = []
            async for output_name, output_data in block.run(
                input_data,
                credentials=credentials_with_key,
                execution_context=make_test_context(),
            ):
                result.append((output_name, output_data))

            # Verify each URL was scraped
            mock_requests.post.assert_called_once()
            call_args = mock_requests.post.call_args
            assert call_args.kwargs["json"] == {"url": url}
            assert len(result) == 1
            assert result[0][0] == "markdown"

    def test_block_id_is_valid_uuid(self, block):
        """Test that block ID is a valid UUID format."""
        import uuid

        # Should not raise ValueError if valid UUID
        uuid.UUID(block.id)
