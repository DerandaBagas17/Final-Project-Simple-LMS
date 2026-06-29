from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestCeleryTests(BaseAPITestCase):
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

    def test_celery_tasks(self):
        """Test 13: Menguji Celery tasks secara langsung (Synchronous)"""
        from courses.tasks import send_enrollment_email, export_course_report, generate_certificate, update_course_statistics
        
        # Panggil fungsi Celery layaknya fungsi biasa untuk coverage
        res_email = send_enrollment_email('student@test.com', 'Python')
        self.assertEqual(res_email, "Email sent successfully to student@test.com for course 'Python'")
        
        res_report = export_course_report()
        self.assertEqual(res_report, "CSV report exported successfully")
        
        res_cert = generate_certificate(1, 2)
        self.assertEqual(res_cert, "Certificate generated for user 1, course 2")
        
        res_stat = update_course_statistics()
        self.assertEqual(res_stat, "Course statistics updated successfully")

