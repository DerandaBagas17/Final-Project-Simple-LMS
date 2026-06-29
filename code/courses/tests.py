from django.test import TestCase, Client
from courses.models import User, Category, Course, Lesson, Enrollment
import json
from unittest.mock import patch

class LMSApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Buat user admin
        self.admin = User.objects.create_superuser(
            username='admin_test', email='admin@test.com', password='password123', role='admin'
        )
        
        # Buat user instructor
        self.instructor = User.objects.create_user(
            username='instructor_test', email='instructor@test.com', password='password123', role='instructor'
        )
        
        # Buat user student
        self.student = User.objects.create_user(
            username='student_test', email='student@test.com', password='password123', role='student'
        )
        
        # Buat kategori
        self.category = Category.objects.create(name='Programming')
        
        # Buat course
        self.course = Course.objects.create(
            title='Python 101', description='Learn Python', category=self.category, instructor=self.instructor
        )

    def get_token(self, email, password):
        # API Auth Login menggunakan endpoint /api/v1/auth/login
        response = self.client.post('/api/v1/auth/login', json.dumps({'email': email, 'password': password}), content_type='application/json')
        return response.json().get('access')[0]

    def test_model_creation(self):
        """Test 1: Memastikan Data Model dan Relasi Terbuat dengan Benar"""
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(self.course.title, 'Python 101')
        self.assertEqual(self.course.instructor.role, 'instructor')
        self.assertEqual(self.course.category.name, 'Programming')

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

    @patch('courses.tasks.generate_certificate.delay')
    def test_generate_certificate_asinkron(self, mock_generate_cert):
        """Test 5: Fitur Tambahan - Generate Certificate Asinkron (PDF) via Celery"""
        token = self.get_token('student@test.com', 'password123')
        
        # Buat lesson agar course ada isinya
        from courses.models import Lesson, Enrollment, Progress
        lesson = Lesson.objects.create(course=self.course, title="Intro to Python", content="Print Hello World", order=1)
        
        # Student mendaftar
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        
        # Student menyelesaikan materi (Progress 100%)
        Progress.objects.create(student=self.student, lesson=lesson, is_completed=True)
        
        # Panggil endpoint generate certificate
        response = self.client.post(f'/api/v1/enrollments/{enrollment.id}/certificate', HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Verifikasi respons berhasil
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success'))
        
        # Verifikasi Celery Task (generate_certificate) benar-benar terpanggil di background
        mock_generate_cert.assert_called_once_with(self.student.id, self.course.id)

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

    def test_category_endpoints(self):
        """Test 7: Menguji endpoint kategori (CRUD)"""
        token = self.get_token('admin@test.com', 'password123')
        
        # Create Category
        payload = {"name": "New Category", "parent_id": None}
        resp = self.client.post('/api/v1/categories/', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 200)
        cat_id = resp.json().get('id')
        
        # Get List Category
        resp = self.client.get('/api/v1/categories/')
        self.assertEqual(resp.status_code, 200)
        
        # Get Single Category
        resp = self.client.get(f'/api/v1/categories/{cat_id}')
        self.assertEqual(resp.status_code, 200)
        
        # Update Category
        payload = {"name": "Updated Category", "parent_id": None}
        resp = self.client.put(f'/api/v1/categories/{cat_id}', json.dumps(payload), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 200)
        
        # Delete Category
        resp = self.client.delete(f'/api/v1/categories/{cat_id}', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(resp.status_code, 200)

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
        
    def test_analytics_endpoints(self):
        """Test 11: Menguji endpoint Analytics"""
        # Endpoint ini bersifat publik (untuk demo), jadi kita bisa langsung GET
        resp = self.client.get('/api/v1/analytics/report/')
        self.assertEqual(resp.status_code, 200)
        
        # Trigger export celery
        resp = self.client.post('/api/v1/analytics/export/')
        self.assertEqual(resp.status_code, 200)
