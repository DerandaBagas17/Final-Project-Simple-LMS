from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestCoursesTests(BaseAPITestCase):
    def test_api_list_courses(self):
        """Test 2: Memastikan API Dasar GET List Course Berjalan (Membuktikan Cache/Rate Limit aman)"""
        response = self.client.get('/api/v1/courses/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_rbac_student_cannot_create_course(self):
        """Test 3: RBAC/Permission - Student dilarang membuat course"""
        token = self.get_token('student@test.com', 'password123')
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        payload = {
            "title": "Hacked Course",
            "description": "Student trying to create",
            "category_id": self.category.id,
            "instructor_id": self.student.id
        }
        
        response = self.client.post('/api/v1/courses/', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 403) # 403 Forbidden

    def test_rbac_instructor_can_create_course(self):
        """Test 4: RBAC/Permission - Instructor dizinkan membuat course"""
        token = self.get_token('instructor@test.com', 'password123')
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        payload = {
            "title": "Advanced Python",
            "description": "Created by instructor",
            "category_id": self.category.id,
            "instructor_id": self.instructor.id
        }
        
        response = self.client.post('/api/v1/courses/', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('title'), 'Advanced Python')

    def test_cache_invalidation_strategy(self):
        """Test 6: Fitur Tambahan - Cache Invalidation Strategy via Signals"""
        from django.core.cache import cache
        
        # 1. Panggil API agar daftar kursus di-cache di Redis
        response1 = self.client.get('/api/v1/courses/')
        self.assertEqual(response1.status_code, 200)
        
        # Pastikan cache-nya sudah terbentuk
        cached_data = cache.get('course_list_cache')
        self.assertIsNotNone(cached_data)
        
        # 2. Modifikasi data course untuk memicu signals.py menghapus cache
        self.course.title = "Python 101 - Update Terbaru"
        self.course.save()
        
        # 3. Pastikan cache sudah terhapus otomatis (invalidated)
        cached_data_after = cache.get('course_list_cache')
        self.assertIsNone(cached_data_after)

    def test_course_endpoints_extended(self):
        """Test 8: Menguji endpoint courses extended (GET id, PUT, PATCH, DELETE)"""
        token = self.get_token('instructor@test.com', 'password123')
        
        # Get single course
        resp = self.client.get(f'/api/v1/courses/{self.course.id}')
        self.assertEqual(resp.status_code, 200)
        
        # Update course (PUT)
        payload = {"title": "Updated Python", "description": "Desc", "category_id": self.category.id, "instructor_id": self.instructor.id}
        resp = self.client.put(f'/api/v1/courses/{self.course.id}', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 200)
        
        # Delete course
        resp = self.client.delete(f'/api/v1/courses/{self.course.id}', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 200)

    def test_search_and_update_lesson(self):
        """Test 14: Menguji pencarian dan update lesson untuk final coverage"""
        token = self.get_token('instructor@test.com', 'password123')
        
        # Test Search Courses
        resp = self.client.get('/api/v1/courses/?search=Python')
        self.assertEqual(resp.status_code, 200)
        
        resp = self.client.get(f'/api/v1/courses/?category_id={self.category.id}')
        self.assertEqual(resp.status_code, 200)
        
        # Test Update Lesson
        # 1. Create lesson first
        payload = {"title": "L1", "content": "C1", "order": 1}
        resp = self.client.post(f'/api/v1/course/{self.course.id}/lessons', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        lesson_id = resp.json().get('id')
        
        # 2. Update it
        payload_upd = {"title": "L1 Updated", "content": "C1", "order": 1}
        resp = self.client.put(f'/api/v1/course/{self.course.id}/lessons/{lesson_id}', json.dumps(payload_upd), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 200)
        
        # 3. Mark lesson completed error (not enrolled/auth error)
        resp = self.client.post(f'/api/v1/lessons/{lesson_id}/progress/') # No auth
        self.assertEqual(resp.status_code, 401)

