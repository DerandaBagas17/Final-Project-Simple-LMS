from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestAnalyticsTests(BaseAPITestCase):
    def test_analytics_endpoints(self):
        """Test 11: Menguji endpoint Analytics"""
        # Endpoint ini bersifat publik (untuk demo), jadi kita bisa langsung GET
        resp = self.client.get('/api/v1/analytics/report/')
        self.assertEqual(resp.status_code, 200)
        
        # Trigger export celery
        resp = self.client.post('/api/v1/analytics/export/')
        self.assertEqual(resp.status_code, 200)

