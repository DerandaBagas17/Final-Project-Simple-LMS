from django.core.management.base import BaseCommand
from courses.models import User

class Command(BaseCommand):
    help = 'Membuat data demo/seed untuk Admin, Instructor, dan Student'

    def handle(self, *args, **kwargs):
        self.stdout.write('Memulai proses seeding data demo...')

        # 1. Buat Admin
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            admin.role = 'admin'
            admin.save()
            self.stdout.write(self.style.SUCCESS('Berhasil membuat akun Admin (admin)'))
        else:
            self.stdout.write(self.style.WARNING('Akun Admin sudah ada.'))

        # 2. Buat Instructor (Dosen)
        if not User.objects.filter(username='dosen').exists():
            dosen = User.objects.create_user(
                username='dosen',
                email='dosen@example.com',
                password='dosen123'
            )
            dosen.role = 'instructor'
            dosen.save()
            self.stdout.write(self.style.SUCCESS('Berhasil membuat akun Instructor (dosen)'))
        else:
            self.stdout.write(self.style.WARNING('Akun Instructor sudah ada.'))

        # 2b. Buat Instructor Kedua (Dosen 1)
        if not User.objects.filter(username='dosen1').exists():
            dosen1 = User.objects.create_user(
                username='dosen1',
                email='dosen1@example.com',
                password='dosen123'
            )
            dosen1.role = 'instructor'
            dosen1.save()
            self.stdout.write(self.style.SUCCESS('Berhasil membuat akun Instructor ke-2 (dosen1)'))
        else:
            self.stdout.write(self.style.WARNING('Akun Instructor ke-2 (dosen1) sudah ada.'))

        # 3. Buat Student
        if not User.objects.filter(username='student').exists():
            student = User.objects.create_user(
                username='student',
                email='student@example.com',
                password='student123'
            )
            student.role = 'student'
            student.save()
            self.stdout.write(self.style.SUCCESS('Berhasil membuat akun Student (student)'))
        else:
            self.stdout.write(self.style.WARNING('Akun Student sudah ada.'))

        self.stdout.write(self.style.SUCCESS('Semua data seed berhasil di-generate!'))
