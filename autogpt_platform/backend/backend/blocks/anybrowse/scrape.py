from typing import Any

from backend.blocks._base import (
    Block,
    BlockCategory,
    BlockOutput,
    BlockSchemaInput,
    BlockSchemaOutput,
)
from backend.blocks.anybrowse._auth import (
    TEST_CREDENTIALS_INPUT,
    AnyBrowseCredentials,
    AnyBrowseCredentialsField,
    AnyBrowseCredentialsInput,
)
from backend.blocks.helpers.http import GetRequest
from backend.data.model import SchemaField
from backend.util.request import Requests


class AnyBrowseScrapeBlock(Block, GetRequest):
    """
    Scrape web pages bypassing Cloudflare and other protection systems.

    AnyBrowse uses real residential Chrome browsers to extract clean LLM-ready
    markdown from any URL, including Cloudflare-protected sites that typically
    block automated scraping tools.

    Free tier: 10 scrapes/day without API key.
    Paid tier: $5 for 3,000 scrapes (never expire) at https://anybrowse.dev
    """

    class Input(BlockSchemaInput):
        credentials: AnyBrowseCredentialsInput = AnyBrowseCredentialsField()
        url: str = SchemaField(description="The URL to scrape and extract content from")

    class Output(BlockSchemaOutput):
        markdown: str = SchemaField(
            description="Clean markdown content extracted from the URL"
        )
        error: str = SchemaField(
            description="Error message if the scrape failed",
            default="",
        )

    def __init__(self):
        super().__init__(
            id="b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
            description="Scrape web pages bypassing Cloudflare protection. "
            "Returns clean LLM-ready markdown content.",
            categories={BlockCategory.SEARCH},
            input_schema=self.Input,
            output_schema=self.Output,
            test_input={
                "url": "https://example.com",
                "credentials": TEST_CREDENTIALS_INPUT,
            },
            test_output=(
                "markdown",
                "# Example Domain\n\nThis domain is for use in...",
            ),
            test_mock={
                "post_request": lambda *args, **kwargs: {
                    "markdown": "# Example Domain\n\nThis domain is for use in..."
                }
            },
        )

    async def run(
        self,
        input_data: Input,
        *,
        credentials: AnyBrowseCredentials | None = None,
        **kwargs,
    ) -> BlockOutput:
        url = input_data.url
        headers = {"Content-Type": "application/json"}

        # Add API key to headers if provided (for paid tier)
        api_key: str | None = None
        if credentials and credentials.api_key:
            api_key = credentials.api_key.get_secret_value()
            headers["x-api-key"] = api_key

        try:
            result = await self.post_request(
                "https://anybrowse.dev/scrape",
                json={"url": url},
                headers=headers,
            )
            yield "markdown", result.get("markdown", "")
        except Exception as e:
            yield "error", f"Failed to scrape {url}: {str(e)}"

    async def post_request(
        self, url: str, json: dict[str, Any], headers: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a POST request to the AnyBrowse API."""
        response = await Requests().post(url, json=json, headers=headers)
        return response.json()
