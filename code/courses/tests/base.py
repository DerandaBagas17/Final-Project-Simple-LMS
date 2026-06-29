from django.test import TestCase, Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json

class BaseAPITestCase(TestCase):
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
