from typing import Literal

from pydantic import SecretStr

from backend.data.model import APIKeyCredentials, CredentialsField, CredentialsMetaInput
from backend.integrations.providers import ProviderName

AnyBrowseCredentials = APIKeyCredentials
AnyBrowseCredentialsInput = CredentialsMetaInput[
    Literal[ProviderName.ANYBROWSE],
    Literal["api_key"],
]


def AnyBrowseCredentialsField() -> AnyBrowseCredentialsInput:
    """
    Creates an AnyBrowse credentials input on a block.

    AnyBrowse offers a free tier (10 scrapes/day, no API key required)
    and a paid tier ($5 for 3,000 scrapes). This field is optional to support
    the free tier while enabling paid tier for higher usage.
    """
    return CredentialsField(
        description="AnyBrowse API key (optional). "
        "Free tier: 10 scrapes/day without key. "
        "Paid tier: $5 for 3,000 scrapes (never expire).",
    )


TEST_CREDENTIALS = APIKeyCredentials(
    id="anybrowse-test-creds-001",
    provider="anybrowse",
    api_key=SecretStr("mock-anybrowse-api-key"),
    title="Mock AnyBrowse API key",
    expires_at=None,
)
TEST_CREDENTIALS_INPUT = {
    "provider": TEST_CREDENTIALS.provider,
    "id": TEST_CREDENTIALS.id,
    "type": TEST_CREDENTIALS.type,
    "title": TEST_CREDENTIALS.title,
}
