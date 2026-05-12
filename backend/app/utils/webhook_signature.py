"""
Webhook signature verification for SNS and SES events.

Validates:
- SNS message signatures
- Timestamp authenticity
- Message integrity
"""

import base64
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WebhookSignatureError(Exception):
    """Raised when webhook signature verification fails."""

    pass


class SNSSignatureVerifier:
    """
    Verifies AWS SNS message signatures.

    AWS SNS signs messages using RSA-SHA256 with a certificate URL.
    Certificate is fetched from AWS and validated.
    """

    # AWS SNS certificate URL format
    SNS_CERT_DOMAIN = "sns.amazonaws.com"

    # Cache for certificates (in production, use proper caching)
    _cert_cache: dict[str, tuple[str, float]] = {}
    _cache_ttl_seconds = 3600  # 1 hour

    @classmethod
    async def verify_signature(cls, message_data: dict[str, Any]) -> bool:
        """
        Verify SNS message signature.

        Args:
            message_data: The SNS message dictionary from webhook

        Returns:
            True if signature is valid, raises WebhookSignatureError otherwise

        Raises:
            WebhookSignatureError: If signature verification fails
        """
        # Extract required fields
        signature = message_data.get("Signature")
        cert_url = message_data.get("SigningCertUrl")
        message = message_data.get("Message")
        timestamp = message_data.get("Timestamp")
        message_type = message_data.get("Type")

        # Validate required fields exist
        if not all([signature, cert_url, message, timestamp, message_type]):
            raise WebhookSignatureError("Missing required SNS message fields")

        # Validate certificate URL is from AWS SNS
        if not cls._is_valid_cert_url(cert_url):
            raise WebhookSignatureError(f"Invalid certificate URL: {cert_url}")

        # Validate timestamp is recent (within 15 minutes)
        if not cls._is_recent_timestamp(timestamp):
            raise WebhookSignatureError("Message timestamp is too old or invalid")

        # Fetch and validate certificate
        try:
            certificate = await cls._get_certificate(cert_url)
        except Exception as e:
            raise WebhookSignatureError(f"Failed to fetch certificate: {e}")

        # Build signing string (canonical format)
        signing_string = cls._build_signing_string(
            message, timestamp, message_type, message_data
        )

        # Verify signature
        try:
            if not cls._verify_rsa_signature(certificate, signing_string, signature):
                raise WebhookSignatureError("Signature verification failed")
        except Exception as e:
            raise WebhookSignatureError(f"Signature verification error: {e}")

        logger.info(
            "SNS webhook signature verified successfully",
            extra={
                "message_type": message_type,
                "cert_url": cert_url[:50] + "..." if len(cert_url) > 50 else cert_url,
            },
        )

        return True

    @classmethod
    def _is_valid_cert_url(cls, cert_url: str) -> bool:
        """Verify certificate URL is from AWS SNS."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(cert_url)
            # Certificate must be HTTPS from AWS SNS domain
            return (
                parsed.scheme == "https"
                and cls.SNS_CERT_DOMAIN in parsed.netloc
                and parsed.path.endswith(".pem")
            )
        except Exception:
            return False

    @classmethod
    def _is_recent_timestamp(cls, timestamp_str: str) -> bool:
        """Verify message timestamp is recent (within 15 minutes)."""
        try:
            # AWS timestamps are ISO 8601 format
            message_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            # Message must not be older than 15 minutes
            time_diff = abs((now - message_time).total_seconds())
            return time_diff < 900  # 15 minutes

        except Exception as e:
            logger.warning(f"Failed to parse SNS timestamp: {e}")
            return False

    @classmethod
    async def _get_certificate(cls, cert_url: str) -> str:
        """Fetch and cache SNS certificate."""
        # Check cache
        if cert_url in cls._cert_cache:
            cert, cached_time = cls._cert_cache[cert_url]
            if (datetime.now().timestamp() - cached_time) < cls._cache_ttl_seconds:
                return cert

        # Fetch certificate from AWS
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(cert_url)
                response.raise_for_status()
                certificate = response.text

                # Cache the certificate
                cls._cert_cache[cert_url] = (certificate, datetime.now().timestamp())

                return certificate
        except Exception as e:
            logger.error(f"Failed to fetch SNS certificate: {e}")
            raise

    @classmethod
    def _build_signing_string(
        cls,
        message: str,
        timestamp: str,
        message_type: str,
        message_data: dict[str, Any],
    ) -> str:
        """Build the string to verify signature against."""
        # For SubscriptionConfirmation and Notification, the signing string format differs
        parts = []

        # Add in specific order as per AWS documentation
        if message_type in ["SubscriptionConfirmation", "Notification"]:
            parts.append("Message")
            parts.append(message)
            parts.append("MessageId")
            parts.append(message_data.get("MessageId", ""))
            parts.append("Timestamp")
            parts.append(timestamp)
            parts.append("Type")
            parts.append(message_type)

        return "\n".join(parts)

    @classmethod
    def _verify_rsa_signature(cls, certificate: str, data: str, signature: str) -> bool:
        """Verify RSA-SHA256 signature."""
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding

            # Load certificate
            cert_obj = x509.load_pem_x509_certificate(
                certificate.encode(), backend=default_backend()
            )

            # Get public key from certificate
            public_key = cert_obj.public_key()

            # Decode base64 signature
            decoded_signature = base64.b64decode(signature)

            # Verify signature
            public_key.verify(
                decoded_signature,
                data.encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )

            return True

        except Exception as e:
            logger.error(f"RSA signature verification failed: {e}")
            return False


class HMACSignatureVerifier:
    """
    Verifies HMAC-based signatures for webhooks.

    Can be used for custom webhook implementations or API gateway signatures.
    """

    @staticmethod
    def verify_signature(
        message: str, signature: str, secret: str, algorithm: str = "sha256"
    ) -> bool:
        """
        Verify HMAC signature.

        Args:
            message: The message to verify
            signature: The provided signature (base64 encoded)
            secret: The shared secret
            algorithm: Hash algorithm (default: sha256)

        Returns:
            True if signature is valid
        """
        try:
            # Decode provided signature
            provided_signature = base64.b64decode(signature)

            # Compute expected signature
            hasher = getattr(hashlib, algorithm)
            expected_signature = hmac.new(
                secret.encode(), message.encode(), hasher
            ).digest()

            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(provided_signature, expected_signature)

        except Exception as e:
            logger.error(f"HMAC signature verification failed: {e}")
            return False

    @staticmethod
    def compute_signature(
        message: str, secret: str, algorithm: str = "sha256"
    ) -> str:
        """
        Compute HMAC signature for testing.

        Args:
            message: The message to sign
            secret: The shared secret
            algorithm: Hash algorithm (default: sha256)

        Returns:
            Base64 encoded signature
        """
        hasher = getattr(hashlib, algorithm)
        signature = hmac.new(secret.encode(), message.encode(), hasher).digest()
        return base64.b64encode(signature).decode()
