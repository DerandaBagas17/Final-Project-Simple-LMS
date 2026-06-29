from django.contrib import admin
from .models import User, Category, Course, Lesson, Enrollment, Progress

# Register User dengan list display sederhana
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
    search_fields = ('username', 'email')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    list_filter = ('parent',)
    search_fields = ('name',)

# --- KONFIGURASI INLINE UNTUK LESSON ---
# Ini memungkinkan kita menambah Lesson langsung di dalam form Course
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1 # Jumlah baris kosong default yang ditampilkan
    ordering = ('order',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'instructor', 'created_at')
    list_filter = ('category', 'instructor')
    search_fields = ('title', 'description')
    # Memasukkan Lesson sebagai form sebaris (inline)
    inlines = [LessonInline]

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title',)
    ordering = ('course', 'order')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'get_progress', 'enrolled_at')
    list_filter = ('course',)
    search_fields = ('student__username', 'course__title')

    def get_progress(self, obj):
        return f"{obj.progress_percentage}%"
    get_progress.short_description = 'Progress'

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'lesson__course')
    search_fields = ('student__username', 'lesson__title')