from django.core.cache import cache
from ninja import NinjaAPI, Schema
from django.shortcuts import get_object_or_404
from courses.models import Course, Category, User, Lesson, Progress, Enrollment
from courses.schemas import CourseSchema, CourseIn,CoursePatchIn, Register, UserOut, CategorySchema, LessonSchema, CategoryIn, LessonIn, LessonReorderIn, EnrollmentSchema, LessonStateIn
from ninja.errors import HttpError
from datetime import datetime
from ninja_simple_jwt.auth.views.api import web_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from django.conf import settings
from courses.tasks import export_course_report
from courses.tasks import send_enrollment_email
from courses.tasks import generate_certificate
apiv1 = NinjaAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="API untuk Simple Learning Management System. "
                "Dokumentasi ini di-generate otomatis oleh Django Ninja.",
    docs_url="/docs/",          # Default: /docs
    openapi_url="/openapi.json" # Default: /openapi.json
)

apiAuth = HttpJwtAuth()

def rate_limit_check(request):
    ip = request.META.get('REMOTE_ADDR')
    cache_key = f"rate_limit_{ip}"
    requests_count = cache.get(cache_key, 0)
    
    if requests_count >= 60:
        raise HttpError(429, "Too Many Requests (Limit 60 per menit)")
        
    cache.set(cache_key, requests_count + 1, 60)

# 1. AUTHENTICATION ENDPOINTS
from ninja_simple_jwt.auth.views.api import get_access_token_for_user, get_refresh_token_for_user, get_access_token_from_refresh_token

class LoginIn(Schema):
    email: str
    password: str

@apiv1.post('auth/login', tags=["Authentication"])
def login(request, payload: LoginIn):
    # Coba cari berdasarkan email dulu, jika gagal, cari berdasarkan username
    user = User.objects.filter(email=payload.email).first() or User.objects.filter(username=payload.email).first()
    if user and user.check_password(payload.password):
        return {
            "access": get_access_token_for_user(user),
            "refresh": get_refresh_token_for_user(user)
        }
    raise HttpError(401, "Invalid credentials")

class TokenRefreshIn(Schema):
    refresh: str

@apiv1.post('auth/refresh', tags=["Authentication"])
def refresh_token(request, payload: TokenRefreshIn):
    try:
        new_access = get_access_token_from_refresh_token(payload.refresh)
        return {"access": new_access}
    except Exception:
        raise HttpError(401, "Invalid or expired refresh token")

@apiv1.post('auth/register', response=UserOut, tags=["Authentication"])
def register(request, data: Register):
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan")
        
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah digunakan")
        
    newUser = User.objects.create_user(
        username=data.username,
        password=data.password,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name
    )
    return newUser

#2. CATEGORIES ENDPOINTS

@apiv1.get('categories/', response=list[CategorySchema], tags=["Categories"])
def list_categories(request):
    # Mengambil semua kategori (bisa tambahkan cache jika perlu)
    return Category.objects.all()
@apiv1.post('categories/', response=CategorySchema, auth=apiAuth, tags=["Categories"])
def create_category(request, payload: CategoryIn):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'admin':
        raise HttpError(403, "Hanya Admin yang boleh membuat kategori.")
    
    parent = None
    if payload.parent_id:
        parent = get_object_or_404(Category, id=payload.parent_id)
    category = Category.objects.create(name=payload.name, parent=parent)
    return category

@apiv1.get('categories/{category_id}', response=CategorySchema, tags=["Categories"])
def get_category(request, category_id: int):
    category = get_object_or_404(Category, id=category_id)
    return category

@apiv1.put('categories/{category_id}', response=CategorySchema, auth=apiAuth, tags=["Categories"])
def update_category(request, category_id: int, payload: CategoryIn):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'admin':
        raise HttpError(403, "Hanya Admin yang boleh mengedit kategori.")
    
    category = get_object_or_404(Category, id=category_id)
    parent = None
    if payload.parent_id:
        parent = get_object_or_404(Category, id=payload.parent_id)
        
    category.name = payload.name
    category.parent = parent
    category.save()
    return category

@apiv1.delete('categories/{category_id}', auth=apiAuth, tags=["Categories"])
def delete_category(request, category_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'admin':
        raise HttpError(403, "Hanya Admin yang boleh menghapus kategori.")
        
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return {"success": True, "message": f"Kategori '{category.name}' berhasil dihapus."}

#3. COURSES ENDPOINTS

@apiv1.get('courses/', response=list[CourseSchema], tags=["Courses"])
def list_courses(request):
    rate_limit_check(request)
    courses = cache.get("course_list_cache")
    if not courses:
        courses = list(Course.objects.for_listing())
        cache.set("course_list_cache", courses, 900)
    return courses
@apiv1.get('courses/{course_id}', response=CourseSchema, tags=["Courses"])
def get_course(request, course_id: int):
    rate_limit_check(request)
    cache_key = f"course_detail_{course_id}"
    course = cache.get(cache_key)
    if not course:
        course = get_object_or_404(Course, id=course_id)
        cache.set(cache_key, course, 900)
    return course
@apiv1.post('courses/', response=CourseSchema, auth=apiAuth, tags=["Courses"])
def create_course(request, payload: CourseIn):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role not in ['instructor', 'admin']:
        raise HttpError(403, "Hanya Instructor atau Admin yang boleh membuat kursus.")
    category = get_object_or_404(Category, id=payload.category_id)
    course = Course.objects.create(
        title=payload.title,
        description=payload.description,
        category=category,
        instructor=real_user
    )
    return course

@apiv1.put('courses/{course_id}', response=CourseSchema, auth=apiAuth, tags=["Courses"])
def update_course(request, course_id: int, payload: CourseIn):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak. Anda bukan pemilik kursus ini.")
    category = get_object_or_404(Category, id=payload.category_id)
    course.title = payload.title
    course.description = payload.description
    course.category = category
    course.save()
    return course

@apiv1.patch('courses/{course_id}', response=CourseSchema, auth=apiAuth, tags=["Courses"])
def patch_course(request, course_id: int, payload: CoursePatchIn):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak. Anda bukan pemilik kursus ini.")
    if payload.title is not None:
        course.title = payload.title
    if payload.description is not None:
        course.description = payload.description
    if payload.category_id is not None:
        category = get_object_or_404(Category, id=payload.category_id)
        course.category = category
        
    course.save()
    return course
    
@apiv1.delete('courses/{course_id}', auth=apiAuth, tags=["Courses"])
def delete_course(request, course_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak. Anda bukan pemilik kursus ini.")
    
    course.delete()
    return {"success": True, "message": f"Course '{course.title}' berhasil dihapus."}

# 4. LESSONS ENDPOINTS

@apiv1.get('course/{course_id}/lessons', response=list[LessonSchema], tags=["Lessons"])
def list_lessons(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    return course.lessons.all().order_by('order')

@apiv1.post('course/{course_id}/lessons', response=LessonSchema, auth=apiAuth, tags=["Lessons"])
def create_lesson(request, course_id: int, payload: LessonIn):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak. Anda bukan pemilik kursus ini.")
    if Lesson.objects.filter(course=course, order=payload.order).exists():
        raise HttpError(400, "Nomor urut (order) ini sudah digunakan di kursus ini.")
    lesson = Lesson.objects.create(
        course=course,
        title=payload.title,
        content=payload.content,
        order=payload.order
    )
    return lesson

@apiv1.get('course/{course_id}/lessons/{lesson_id}', response=LessonSchema, tags=["Lessons"])
def get_lesson(request, course_id: int, lesson_id: int):
    lesson = get_object_or_404(Lesson, id=lesson_id, course_id=course_id)
    return lesson

@apiv1.put('course/{course_id}/lessons/{lesson_id}', response=LessonSchema, auth=apiAuth, tags=["Lessons"])
def update_lesson(request, course_id: int, lesson_id: int, payload: LessonIn):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak.")
    lesson = get_object_or_404(Lesson, id=lesson_id, course_id=course_id)
    if payload.order != lesson.order and Lesson.objects.filter(course=course, order=payload.order).exists():
        raise HttpError(400, "Nomor urut (order) ini sudah digunakan.")
    
    lesson.title = payload.title
    lesson.content = payload.content
    lesson.order = payload.order
    lesson.save()
    return lesson

@apiv1.delete('course/{course_id}/lessons/{lesson_id}', auth=apiAuth, tags=["Lessons"])
def delete_lesson(request, course_id: int, lesson_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak.")
    lesson = get_object_or_404(Lesson, id=lesson_id, course_id=course_id)
    lesson.delete()
    return {"success": True, "message": f"Materi '{lesson.title}' berhasil dihapus."}

@apiv1.put('course/{course_id}/lessons/{lesson_id}/reorder', response=LessonSchema, auth=apiAuth, tags=["Lessons"])
def reorder_lesson(request, course_id: int, lesson_id: int, payload: LessonReorderIn):
    real_user = get_object_or_404(User, id=request.user.id)
    course = get_object_or_404(Course, id=course_id)
    if course.instructor != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak.")
    lesson = get_object_or_404(Lesson, id=lesson_id, course_id=course_id)
    
    if payload.order != lesson.order and Lesson.objects.filter(course=course, order=payload.order).exists():
        raise HttpError(400, "Nomor urut (order) ini sudah digunakan.")
        
    lesson.order = payload.order
    lesson.save()
    return lesson

# 5. ENROLLMENTS & CERTIFICATES ENDPOINTS

@apiv1.post('enrollments/enroll/{course_id}', auth=apiAuth, tags=["Enrollments"])
def enroll_course(request, course_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'student':
        raise HttpError(403, "Hanya Student yang dapat mendaftar kursus.")
    course = get_object_or_404(Course, id=course_id)
    
    enrollment, created = Enrollment.objects.get_or_create(student=real_user, course=course)
    if created:
        send_enrollment_email.delay(real_user.email, course.title)
        return {"message": f"Berhasil mendaftar! Email konfirmasi untuk '{course.title}' sedang dikirim di background."}
    else:
        return {"message": f"Anda sudah terdaftar di kursus '{course.title}'."}

@apiv1.get('enrollments/my-courses', response=list[EnrollmentSchema], auth=apiAuth, tags=["Enrollments"])
def my_courses(request):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'student':
        raise HttpError(403, "Hanya Student yang memiliki daftar kursus.")
    return Enrollment.objects.filter(student=real_user)

@apiv1.get('enrollments/{enrollment_id}', response=EnrollmentSchema, auth=apiAuth, tags=["Enrollments"])
def get_enrollment(request, enrollment_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if enrollment.student != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak.")
    return enrollment

@apiv1.post('enrollments/{enrollment_id}/lessons/{lesson_id}/state', auth=apiAuth, tags=["Enrollments"])
def set_lesson_state(request, enrollment_id: int, lesson_id: int, payload: LessonStateIn):
    real_user = get_object_or_404(User, id=request.user.id)
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    if enrollment.student != real_user:
        raise HttpError(403, "Akses ditolak.")
    lesson = get_object_or_404(Lesson, id=lesson_id, course=enrollment.course)
    
    progress, created = Progress.objects.get_or_create(
        student=real_user,
        lesson=lesson,
        defaults={'is_completed': payload.is_completed, 'completed_at': datetime.now() if payload.is_completed else None}
    )
    if not created:
        progress.is_completed = payload.is_completed
        progress.completed_at = datetime.now() if payload.is_completed else None
        progress.save()
    
    status = "selesai" if payload.is_completed else "belum selesai"
    return {"success": True, "message": f"Materi '{lesson.title}' berhasil ditandai {status}."}

@apiv1.post('enrollments/{enrollment_id}/certificate', auth=apiAuth, tags=["Enrollments"])
def trigger_certificate(request, enrollment_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Validasi: Hanya siswa pemilik pendaftaran atau admin yang boleh
    if enrollment.student != real_user and real_user.role != 'admin':
        raise HttpError(403, "Akses ditolak. Anda tidak berhak meminta sertifikat ini.")
        
    # Validasi: Syarat mutlak 100%
    if enrollment.progress_percentage < 100:
        raise HttpError(400, f"Progres Anda masih {enrollment.progress_percentage}%. Sertifikat hanya bisa diklaim jika seluruh materi sudah diselesaikan (100%).")

    # Memicu proses pembuatan PDF di background dengan ID siswa yang benar
    generate_certificate.delay(enrollment.student.id, enrollment.course.id)
    
    return {
        "success": True,
        "message": f"Luar biasa! Progres Anda 100%. PDF Sertifikat kursus '{enrollment.course.title}' sedang diproses dan akan segera dikirimkan."
    }

# 6 PROGRESS ENDPOINTS (Student Activity)

@apiv1.post('lessons/{lesson_id}/progress/', auth=apiAuth, tags=["Progress"])
def mark_lesson_completed(request, lesson_id: int):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'student':
        raise HttpError(403, "Hanya Student yang dapat menandai progress materi.")
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Memastikan siswa sudah enroll di course ini sebelum bisa mengerjakan materi
    is_enrolled = lesson.course.enrollments.filter(student=real_user).exists()
    if not is_enrolled:
        raise HttpError(403, "Anda harus mendaftar (enroll) kursus ini terlebih dahulu.")
    # Update atau Create Progress siswa untuk materi ini
    progress, created = Progress.objects.get_or_create(
        student=real_user,
        lesson=lesson,
        defaults={'is_completed': True, 'completed_at': datetime.now()}
    )
    if not created and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = datetime.now()
        progress.save()
        
    enrollment = lesson.course.enrollments.get(student=real_user)
    return {
        "success": True, 
        "message": f"Materi '{lesson.title}' berhasil ditandai selesai.",
        "course_progress": f"{enrollment.progress_percentage}%"
    }

@apiv1.get('progress/', auth=apiAuth, tags=["Progress"])
def get_my_progress(request):
    real_user = get_object_or_404(User, id=request.user.id)
    if real_user.role != 'student':
        raise HttpError(403, "Hanya Student yang memiliki data progress.")
    
    # Menampilkan daftar materi apa saja yang sudah/belum diselesaikan siswa
    progress_list = Progress.objects.filter(student=real_user).select_related('lesson', 'lesson__course')
    
    data = []
    for p in progress_list:
        data.append({
            "course_title": p.lesson.course.title,
            "lesson_title": p.lesson.title,
            "is_completed": p.is_completed,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None
        })
    return data


# 7. ANALYTICS ENDPOINTS

@apiv1.get('analytics/report/', tags=["Analytics"])
def get_activity_report(request):
    pipeline = [
        {"$group": {"_id": "$path", "total_visits": {"$sum": 1}}},
        {"$sort": {"total_visits": -1}}
    ]
    report = list(settings.MONGO_DB['activity_logs'].aggregate(pipeline))
    return {"report": report}
@apiv1.post('analytics/export/', tags=["Analytics"])
def trigger_export(request):
    export_course_report.delay()
    return {"message": "Proses export CSV sedang berjalan di background. Tidak perlu menunggu!"}