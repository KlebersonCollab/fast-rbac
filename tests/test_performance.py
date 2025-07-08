import asyncio
import concurrent.futures
import time
from unittest.mock import patch

import pytest
from fastapi import status


class TestPerformance:
    """Test system performance and load handling"""

    def test_api_key_authentication_performance(self, client, auth_headers):
        """Test API key authentication performance"""

        # Create API key
        api_key_payload = {
            "name": "Performance Test Key",
            "scopes": ["read"],
            "rate_limit_per_minute": 1000,
        }

        response = client.post("/api-keys/", json=api_key_payload, headers=auth_headers)
        api_key = response.json()["key"]
        api_headers = {"X-API-Key": api_key}

        # Test multiple rapid requests
        start_time = time.time()
        request_count = 50

        for _ in range(request_count):
            response = client.get("/auth/me", headers=api_headers)
            assert response.status_code == status.HTTP_200_OK

        end_time = time.time()
        total_time = end_time - start_time
        requests_per_second = request_count / total_time

        # Should handle at least 10 requests per second
        assert (
            requests_per_second > 10
        ), f"Performance too slow: {requests_per_second} req/s"

        print(f"API Key Authentication Performance: {requests_per_second:.2f} req/s")

    def test_bulk_api_key_creation_performance(self, client, auth_headers):
        """Test performance of creating multiple API keys"""

        start_time = time.time()
        key_count = 20
        created_keys = []

        for i in range(key_count):
            payload = {
                "name": f"Bulk Test Key {i}",
                "scopes": ["read"],
                "rate_limit_per_minute": 100,
            }

            response = client.post("/api-keys/", json=payload, headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK
            created_keys.append(response.json()["api_key"]["id"])

        end_time = time.time()
        total_time = end_time - start_time
        keys_per_second = key_count / total_time

        # Should create at least 5 keys per second
        assert keys_per_second > 5, f"Key creation too slow: {keys_per_second} keys/s"

        print(f"Bulk API Key Creation Performance: {keys_per_second:.2f} keys/s")

        # Clean up
        for key_id in created_keys:
            client.delete(f"/api-keys/{key_id}", headers=auth_headers)

    def test_webhook_creation_performance(self, client, auth_headers):
        """Test performance of creating multiple webhooks"""

        start_time = time.time()
        webhook_count = 15
        created_webhooks = []

        for i in range(webhook_count):
            payload = {
                "name": f"Performance Webhook {i}",
                "url": f"https://test{i}.example.com/webhook",
                "events": ["user.created", "user.updated"],
                "timeout_seconds": 30,
            }

            response = client.post("/webhooks/", json=payload, headers=auth_headers)
            assert response.status_code == status.HTTP_200_OK
            created_webhooks.append(response.json()["id"])

        end_time = time.time()
        total_time = end_time - start_time
        webhooks_per_second = webhook_count / total_time

        # Should create at least 3 webhooks per second
        assert (
            webhooks_per_second > 3
        ), f"Webhook creation too slow: {webhooks_per_second} webhooks/s"

        print(f"Webhook Creation Performance: {webhooks_per_second:.2f} webhooks/s")

        # Clean up
        for webhook_id in created_webhooks:
            client.delete(f"/webhooks/{webhook_id}", headers=auth_headers)

    def test_large_data_retrieval_performance(self, client, auth_headers):
        """Test performance of retrieving large datasets"""

        # Create test data
        api_keys = []
        for i in range(50):
            payload = {
                "name": f"Data Test Key {i}",
                "scopes": ["read"],
                "rate_limit_per_minute": 100,
            }
            response = client.post("/api-keys/", json=payload, headers=auth_headers)
            api_keys.append(response.json()["api_key"]["id"])

        # Test retrieval performance
        start_time = time.time()

        response = client.get("/api-keys/?limit=100", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 50

        end_time = time.time()
        retrieval_time = end_time - start_time

        # Should retrieve data in less than 1 second
        assert retrieval_time < 1.0, f"Data retrieval too slow: {retrieval_time:.3f}s"

        print(
            f"Large Data Retrieval Performance: {retrieval_time:.3f}s for {len(data)} records"
        )

        # Clean up
        for key_id in api_keys:
            client.delete(f"/api-keys/{key_id}", headers=auth_headers)

    def test_concurrent_api_requests_performance(self, client, auth_headers):
        """Test performance under concurrent requests"""

        # Create API key
        api_key_payload = {
            "name": "Concurrent Test Key",
            "scopes": ["read"],
            "rate_limit_per_minute": 2000,
        }

        response = client.post("/api-keys/", json=api_key_payload, headers=auth_headers)
        api_key = response.json()["key"]
        api_headers = {"X-API-Key": api_key}

        def make_request():
            """Make a single API request"""
            response = client.get("/auth/me", headers=api_headers)
            return response.status_code == status.HTTP_200_OK

        # Test concurrent requests
        start_time = time.time()
        thread_count = 10
        requests_per_thread = 5

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=thread_count
        ) as executor:
            futures = []

            for _ in range(thread_count):
                for _ in range(requests_per_thread):
                    future = executor.submit(make_request)
                    futures.append(future)

            # Wait for all requests to complete
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        end_time = time.time()
        total_time = end_time - start_time
        total_requests = thread_count * requests_per_thread
        requests_per_second = total_requests / total_time

        # All requests should succeed
        assert all(results), "Some concurrent requests failed"

        # Should handle concurrent requests efficiently
        assert (
            requests_per_second > 20
        ), f"Concurrent performance too slow: {requests_per_second} req/s"

        print(
            f"Concurrent Requests Performance: {requests_per_second:.2f} req/s with {thread_count} threads"
        )

    def test_database_query_performance(self, client, auth_headers, db_session, sample_user):
        """Test database query performance"""
        from app.schemas.api_key import APIKeyCreate, APIKeyScope
        from app.services.api_key_service import APIKeyService

        service = APIKeyService(db_session)

        # Create test data
        created_keys = []

        start_time = time.time()

        for i in range(30):
            api_key_data = APIKeyCreate(
                name=f"DB Test Key {i}",
                scopes=[APIKeyScope.READ],
                rate_limit_per_minute=100,
            )

            api_key, _ = service.create_api_key(
                api_key_data=api_key_data, current_user=sample_user
            )
            created_keys.append(api_key.id)

        creation_time = time.time() - start_time

        # Test query performance
        start_time = time.time()

        api_keys = service.get_api_keys(current_user=sample_user, limit=100)

        query_time = time.time() - start_time

        # Performance assertions
        assert creation_time < 2.0, f"DB creation too slow: {creation_time:.3f}s"
        assert query_time < 0.1, f"DB query too slow: {query_time:.3f}s"
        assert len(api_keys) >= 30

        print(
            f"Database Performance - Creation: {creation_time:.3f}s, Query: {query_time:.3f}s"
        )

        # Clean up
        for key_id in created_keys:
            service.delete_api_key(key_id, current_user=sample_user)

    def test_memory_usage_under_load(self, client, auth_headers):
        """Test memory usage under sustained load"""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Measure initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create load
        created_resources = []

        for i in range(100):
            # Create API key
            api_key_payload = {
                "name": f"Memory Test Key {i}",
                "scopes": ["read"],
                "rate_limit_per_minute": 100,
            }

            response = client.post(
                "/api-keys/", json=api_key_payload, headers=auth_headers
            )
            if response.status_code == status.HTTP_200_OK:
                created_resources.append(("api_key", response.json()["api_key"]["id"]))

            # Create webhook every 5 iterations
            if i % 5 == 0:
                webhook_payload = {
                    "name": f"Memory Test Webhook {i}",
                    "url": f"https://test{i}.example.com/webhook",
                    "events": ["user.created"],
                }

                webhook_response = client.post(
                    "/webhooks/", json=webhook_payload, headers=auth_headers
                )
                if webhook_response.status_code == status.HTTP_200_OK:
                    created_resources.append(("webhook", webhook_response.json()["id"]))

        # Measure peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        # Clean up
        for resource_type, resource_id in created_resources:
            if resource_type == "api_key":
                client.delete(f"/api-keys/{resource_id}", headers=auth_headers)
            elif resource_type == "webhook":
                client.delete(f"/webhooks/{resource_id}", headers=auth_headers)

        # Measure final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Memory usage should not increase excessively
        assert (
            memory_increase < 100
        ), f"Memory usage increased too much: {memory_increase:.2f}MB"

        print(
            f"Memory Usage - Initial: {initial_memory:.2f}MB, Peak: {peak_memory:.2f}MB, Final: {final_memory:.2f}MB"
        )

    @pytest.mark.asyncio
    async def test_webhook_delivery_performance(self, client, auth_headers):
        """Test webhook delivery performance"""
        from datetime import datetime

        from app.schemas.webhook import WebhookEventData
        from app.services.webhook_service import WebhookService

        # Create webhook
        webhook_payload = {
            "name": "Performance Webhook",
            "url": "https://httpbin.org/status/200",  # Fast test endpoint
            "events": ["user.created"],
            "timeout_seconds": 5,
        }

        response = client.post("/webhooks/", json=webhook_payload, headers=auth_headers)
        webhook_data = response.json()
        webhook_id = webhook_data["id"]

        # Mock webhook delivery to avoid external dependencies in tests
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = type(
                "MockResponse",
                (),
                {
                    "status": 200,
                    "text": lambda: asyncio.create_task(
                        asyncio.coroutine(lambda: '{"success": true}')()
                    ),
                    "headers": {"Content-Type": "application/json"},
                },
            )()

            mock_post.return_value.__aenter__.return_value = mock_response

            # Test multiple webhook deliveries
            start_time = time.time()
            delivery_count = 10

            for i in range(delivery_count):
                test_payload = {
                    "event_type": "user.created",
                    "test_data": {"user_id": i, "test": True},
                }

                test_response = client.post(
                    f"/webhooks/{webhook_id}/test",
                    json=test_payload,
                    headers=auth_headers,
                )
                assert test_response.status_code == status.HTTP_200_OK

            end_time = time.time()
            total_time = end_time - start_time
            deliveries_per_second = delivery_count / total_time

            # Should handle multiple webhook deliveries efficiently
            assert (
                deliveries_per_second > 5
            ), f"Webhook delivery too slow: {deliveries_per_second} deliveries/s"

            print(
                f"Webhook Delivery Performance: {deliveries_per_second:.2f} deliveries/s"
            )

        # Clean up
        client.delete(f"/webhooks/{webhook_id}", headers=auth_headers)

    def test_rate_limiting_performance(self, client, auth_headers):
        """Test rate limiting performance impact"""

        # Create API key with rate limiting
        api_key_payload = {
            "name": "Rate Limit Test Key",
            "scopes": ["read"],
            "rate_limit_per_minute": 30,  # 30 requests per minute = 0.5 per second
        }

        response = client.post("/api-keys/", json=api_key_payload, headers=auth_headers)
        api_key = response.json()["key"]
        api_headers = {"X-API-Key": api_key}

        # Test requests within rate limit
        start_time = time.time()
        success_count = 0

        for i in range(10):
            response = client.get("/auth/me", headers=api_headers)
            if response.status_code == status.HTTP_200_OK:
                success_count += 1

            # Small delay to stay within rate limit
            time.sleep(0.1)

        end_time = time.time()
        total_time = end_time - start_time

        # All requests within limit should succeed
        assert (
            success_count == 10
        ), f"Expected 10 successful requests, got {success_count}"

        # Rate limiting should not add significant overhead
        expected_time = 10 * 0.1  # 10 requests with 0.1s delay each
        overhead = total_time - expected_time
        assert overhead < 0.5, f"Rate limiting overhead too high: {overhead:.3f}s"

        print(
            f"Rate Limiting Performance - Total time: {total_time:.3f}s, Overhead: {overhead:.3f}s"
        )

    def test_pagination_performance(self, client, auth_headers):
        """Test pagination performance with large datasets"""

        # Create test data
        created_keys = []
        for i in range(100):
            payload = {
                "name": f"Pagination Test Key {i}",
                "scopes": ["read"],
                "rate_limit_per_minute": 100,
            }
            response = client.post("/api-keys/", json=payload, headers=auth_headers)
            if response.status_code == status.HTTP_200_OK:
                created_keys.append(response.json()["api_key"]["id"])

        # Test pagination performance
        page_size = 20
        total_pages = 5

        start_time = time.time()

        for page in range(total_pages):
            skip = page * page_size
            response = client.get(
                f"/api-keys/?skip={skip}&limit={page_size}", headers=auth_headers
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) <= page_size

        end_time = time.time()
        total_time = end_time - start_time
        pages_per_second = total_pages / total_time

        # Should handle pagination efficiently
        assert pages_per_second > 10, f"Pagination too slow: {pages_per_second} pages/s"

        print(f"Pagination Performance: {pages_per_second:.2f} pages/s")

        # Clean up
        for key_id in created_keys:
            client.delete(f"/api-keys/{key_id}", headers=auth_headers)
