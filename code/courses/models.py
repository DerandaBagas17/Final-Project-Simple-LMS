from django.db import models
from django.contrib.auth.models import AbstractUser


# --- 0. CUSTOM MANAGERS (Ini yang sebelumnya terlewat) ---
class CourseManager(models.Manager):
    def for_listing(self):
        # select_related mencegah N+1 saat meload category & instructor
        return self.select_related("category", "instructor")


class EnrollmentManager(models.Manager):
    def for_student_dashboard(self):
        return self.select_related("course")


# 1. User Model (dengan role)
class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("instructor", "Instructor"),
        ("student", "Student"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")

    def __str__(self):
        return f"{self.username} ({self.role})"


# 2. Category Model (self-referencing untuk hierarchy)
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
    )

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name


# 3. Course Model
class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="courses"
    )
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "instructor"},
        related_name="courses_taught",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ---> KITA PASANG MANAGER-NYA DI SINI <---
    objects = CourseManager()

    def __str__(self):
        return self.title


# 4. Lesson Model (dengan ordering)
class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(help_text="Urutan lesson dalam sebuah course")

    class Meta:
        ordering = ["order"]
        unique_together = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} - Lesson {self.order}: {self.title}"


# 5. Enrollment Model (dengan unique constraint)
class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"},
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    # ---> KITA PASANG MANAGER-NYA DI SINI <---
    objects = EnrollmentManager()

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

    @property
    def progress_percentage(self):
        total_lessons = self.course.lessons.count()
        if total_lessons == 0:
            return 0
        # Hitung berapa materi di kursus ini yang sudah diselesaikan oleh student
        completed = self.student.progress.filter(lesson__course=self.course, is_completed=True).count()
        return round((completed / total_lessons) * 100)



# 6. Progress Model (tracking lesson completion)
class Progress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress")
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="progress"
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["student", "lesson"]
        verbose_name_plural = (
            "Progress"  # (Bonus: memperbaiki tulisan Progresss di admin)
        )

    def __str__(self):
        status = "Completed" if self.is_completed else "Pending"
        return f"{self.student.username} - {self.lesson.title} ({status})"
