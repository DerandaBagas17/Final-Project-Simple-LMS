from django.test import Client
from courses.models import User, Category, Course, Lesson, Enrollment, Progress
import json
from unittest.mock import patch
from datetime import datetime
from courses.tests.base import BaseAPITestCase

class TestCategoriesTests(BaseAPITestCase):
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

