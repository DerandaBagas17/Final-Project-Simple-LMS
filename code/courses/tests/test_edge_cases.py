from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestEdgeCasesTests(BaseAPITestCase):
    def test_edge_cases_and_errors(self):
        """Test 10: Menguji Edge Cases dan Error Handling"""
        token_student = self.get_token('student@test.com', 'password123')
        
        # 1. Login Failed
        resp = self.client.post('/api/v1/auth/login', json.dumps({'email': 'wrong@test.com', 'password': '123'}), content_type='application/json')
        self.assertEqual(resp.status_code, 401)
        
        # 2. Register duplicate email
        payload = {"username": "new_student", "email": "student@test.com", "password": "123", "first_name": "A", "last_name": "B"}
        resp = self.client.post('/api/v1/auth/register', json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        
        # 3. Unauthorized access to update course
        payload = {"title": "Hack", "description": "Desc", "category_id": self.category.id, "instructor_id": self.instructor.id}
        resp = self.client.put(f'/api/v1/courses/{self.course.id}', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 403)
        
        # 4. Request certificate when progress not 100%
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        resp = self.client.post(f'/api/v1/enrollments/{enrollment.id}/certificate', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 400)

    def test_apiv1_ultimate_coverage(self):
        """Test 15: Menguji sisa endpoint apiv1 (refresh token, get enrollment, set lesson state, certificate, delete course)"""
        token_student = self.get_token('student@test.com', 'password123')
        token_instructor = self.get_token('instructor@test.com', 'password123')
        
        # 1. Auth Refresh
        login_resp = self.client.post('/api/v1/auth/login', json.dumps({'email': 'student@test.com', 'password': 'password123'}), content_type='application/json')
        refresh_token = login_resp.json().get('refresh')[0] if isinstance(login_resp.json().get('refresh'), list) else login_resp.json().get('refresh')
        
        refresh_resp = self.client.post('/api/v1/auth/refresh', json.dumps({'refresh': refresh_token}), content_type='application/json')
        self.assertEqual(refresh_resp.status_code, 200)
        self.assertIn('access', refresh_resp.json())
        
        # 2. Setup Enrollment & Lesson for Student
        lesson = Lesson.objects.create(course=self.course, title="L Final", content="C", order=99)
        enrollment, _ = Enrollment.objects.get_or_create(student=self.student, course=self.course)
        
        # 3. Get Enrollment Detail
        resp = self.client.get(f'/api/v1/enrollments/{enrollment.id}', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # 4. Set Lesson State (Completed)
        payload = {"is_completed": True}
        resp = self.client.post(f'/api/v1/enrollments/{enrollment.id}/lessons/{lesson.id}/state', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # Set Lesson State (Uncompleted) to hit branches
        payload = {"is_completed": False}
        resp = self.client.post(f'/api/v1/enrollments/{enrollment.id}/lessons/{lesson.id}/state', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
        
        # Set Lesson State (Completed) AGAIN for certificate
        payload = {"is_completed": True}
        resp = self.client.post(f'/api/v1/enrollments/{enrollment.id}/lessons/{lesson.id}/state', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        self.assertEqual(resp.status_code, 200)
    
        # 5. Hit 100% and get Certificate
        # (Progress is already created and set to 100% by the API above)
        resp = self.client.post(f'/api/v1/enrollments/{enrollment.id}/certificate', HTTP_AUTHORIZATION=f'Bearer {token_student}')
        # Should be 200 since progress is 100%
        self.assertEqual(resp.status_code, 200)
        
        # 6. Delete Lesson
        resp = self.client.delete(f'/api/v1/course/{self.course.id}/lessons/{lesson.id}', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 200)
        
        # 7. Reorder Lesson
        lesson2 = Lesson.objects.create(course=self.course, title="L2", content="C", order=5)
        payload = {"order": 2}
        resp = self.client.put(f'/api/v1/course/{self.course.id}/lessons/{lesson2.id}/reorder', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 200)
        
        # 8. Create Category
        payload = {"name": "Test Cat"}
        token_admin_test = self.get_token('admin@test.com', 'password123')
        resp = self.client.post('/api/v1/categories/', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_admin_test}')
        self.assertEqual(resp.status_code, 200)
        
        # Create Category as non-admin (error)
        resp = self.client.post('/api/v1/categories/', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 403)
        
        # 9. Register (Happy Path)
        payload = {"username": "newuser", "password": "123", "email": "new@test.com", "first_name": "A", "last_name": "B"}
        resp = self.client.post('/api/v1/auth/register', json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        
        # 10. Delete Course
        resp = self.client.delete(f'/api/v1/courses/{self.course.id}', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 200)
        
        # 11. Duplicate username register
        payload["email"] = "other@test.com"
        resp = self.client.post('/api/v1/auth/register', json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        
        # 12. Invalid refresh token
        resp = self.client.post('/api/v1/auth/refresh', json.dumps({"refresh": "invalid"}), content_type='application/json')
        self.assertEqual(resp.status_code, 401)
        
        # 13. Reorder duplicate order
        # create new course for isolation since we deleted self.course
        c2 = Course.objects.create(title="C2", description="D", category=self.category, instructor=self.instructor)
        l_a = Lesson.objects.create(course=c2, title="LA", content="C", order=1)
        l_b = Lesson.objects.create(course=c2, title="LB", content="C", order=2)
        resp = self.client.put(f'/api/v1/course/{c2.id}/lessons/{l_b.id}/reorder', json.dumps({"order": 1}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 400)
        
        # 14. Update Category & Delete Category
        token_admin_test = self.get_token('admin@test.com', 'password123')
        payload_cat = {"name": "SubCat", "parent_id": self.category.id}
        resp = self.client.post('/api/v1/categories/', json.dumps(payload_cat), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_admin_test}')
        self.assertEqual(resp.status_code, 200)
        subcat_id = resp.json()['id']
        
        # Update category
        resp = self.client.put(f'/api/v1/categories/{subcat_id}', json.dumps({"name": "NewSub", "parent_id": self.category.id}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_admin_test}')
        self.assertEqual(resp.status_code, 200)
        
        # Update category error (non admin)
        resp = self.client.put(f'/api/v1/categories/{subcat_id}', json.dumps({"name": "NewSub"}), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 403)
        
        # Delete category error (non admin)
        resp = self.client.delete(f'/api/v1/categories/{subcat_id}', HTTP_AUTHORIZATION=f'Bearer {token_instructor}')
        self.assertEqual(resp.status_code, 403)
        
        # Delete category (admin)
        resp = self.client.delete(f'/api/v1/categories/{subcat_id}', HTTP_AUTHORIZATION=f'Bearer {token_admin_test}')
        self.assertEqual(resp.status_code, 200)

