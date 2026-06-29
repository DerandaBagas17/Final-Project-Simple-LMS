from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestLessonsAndProgressTests(BaseAPITestCase):
    def test_lesson_and_progress_endpoints(self):
        """Test 9: Menguji endpoint Lessons dan Progress"""
        token_instructor = self.get_token('instructor@test.com', 'password123')
        token_student = self.get_token('student@test.com', 'password123')
        
        # Create Lesson
        payload = {"title": "L1", "content": "C1", "order": 1}
        resp = self.client.post(f'/api/v1/course/{self.course.id}/lessons', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 200)
        lesson_id = resp.json().get('id')
        
        # Get Lesson list
        resp = self.client.get(f'/api/v1/course/{self.course.id}/lessons')
        self.assertEqual(resp.status_code, 200)
        
        # Enroll course as student
        resp = self.client.post(f'/api/v1/enrollments/enroll/{self.course.id}', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # Get my courses
        resp = self.client.get('/api/v1/enrollments/my-courses', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # Mark lesson completed
        resp = self.client.post(f'/api/v1/lessons/{lesson_id}/progress/', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # Get my progress
        resp = self.client.get('/api/v1/progress/', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # Delete Lesson
        resp = self.client.delete(f'/api/v1/course/{self.course.id}/lessons/{lesson_id}', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 200)

