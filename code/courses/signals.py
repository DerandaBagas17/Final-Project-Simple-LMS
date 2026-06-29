from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Course, Lesson, Enrollment, Progress

def clear_course_cache():
    cache.delete("course_list_cache")

@receiver([post_save, post_delete], sender=Course)
def invalidate_course_cache(sender, instance, **kwargs):
    clear_course_cache()
    cache.delete(f"course_detail_{instance.id}")

@receiver([post_save, post_delete], sender=Lesson)
def invalidate_course_cache_from_lesson(sender, instance, **kwargs):
    clear_course_cache()
    if instance.course_id:
        cache.delete(f"course_detail_{instance.course_id}")

@receiver([post_save, post_delete], sender=Enrollment)
def invalidate_course_cache_from_enrollment(sender, instance, **kwargs):
    clear_course_cache()
    if instance.course_id:
        cache.delete(f"course_detail_{instance.course_id}")

@receiver([post_save, post_delete], sender=Progress)
def invalidate_course_cache_from_progress(sender, instance, **kwargs):
    clear_course_cache()
    if instance.lesson and instance.lesson.course_id:
        cache.delete(f"course_detail_{instance.lesson.course_id}")
