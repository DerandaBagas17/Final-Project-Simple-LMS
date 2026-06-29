from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestModelsTests(BaseAPITestCase):
    def test_model_creation(self):
        """Test 1: Memastikan Data Model dan Relasi Terbuat dengan Benar"""
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(self.course.title, 'Python 101')
        self.assertEqual(self.course.instructor.role, 'instructor')
        self.assertEqual(self.course.category.name, 'Programming')

    def test_deep_edge_cases_and_models(self):
        """Test 12: Menguji Models string representation dan endpoint 404/403 tambahan"""
        # Test models __str__
        self.assertEqual(str(self.category), self.category.name)
        self.assertEqual(str(self.course), self.course.title)
        
        token_student = self.get_token('student@test.com', 'password123')
        token_instructor = self.get_token('instructor@test.com', 'password123')
        
        # Course not found
        resp = self.client.get('/api/v1/courses/99999')
        self.assertEqual(resp.status_code, 404)
        
        # PATCH course
        payload = {"title": "Patched Title"}
        resp = self.client.patch(f'/api/v1/courses/{self.course.id}', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 200)
        
        # Instructor try to reorder lessons (fake payload)
        payload = [{"lesson_id": 1, "order": 2}]
        resp = self.client.put(f'/api/v1/course/{self.course.id}/lessons/reorder', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        # Since lesson doesn't exist, might be 400, 404, or 422
        self.assertTrue(resp.status_code in [200, 400, 404, 422])

