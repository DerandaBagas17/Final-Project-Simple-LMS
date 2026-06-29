import json

fixtures = []

# 3 Categories
categories = [
    {"pk": 100, "name": "Web Development"},
    {"pk": 101, "name": "Data Science"},
    {"pk": 102, "name": "Cyber Security"},
]

for cat in categories:
    fixtures.append({
        "model": "courses.category",
        "pk": cat["pk"],
        "fields": {
            "name": cat["name"],
            "parent": None
        }
    })

# 3 Courses (1 per category)
courses = [
    {"pk": 100, "title": "Fullstack Django & React", "cat": 100},
    {"pk": 101, "title": "Machine Learning 101", "cat": 101},
    {"pk": 102, "title": "Ethical Hacking Basics", "cat": 102},
]

for c in courses:
    fixtures.append({
        "model": "courses.course",
        "pk": c["pk"],
        "fields": {
            "title": c["title"],
            "description": f"Pelajari seluk beluk {c['title']} secara mendalam.",
            "category": c["cat"],
            "instructor": 2, # ID 2 adalah dosen
            "created_at": "2026-06-29T10:00:00Z"
        }
    })

# 14 Lessons per course
lesson_pk = 1000
for c in courses:
    for i in range(1, 15): # 1 sampai 14
        fixtures.append({
            "model": "courses.lesson",
            "pk": lesson_pk,
            "fields": {
                "course": c["pk"],
                "title": f"Bab {i}: Pengenalan {c['title']}",
                "content": f"Ini adalah materi lengkap untuk Bab {i} dari kursus {c['title']}. Selamat belajar!",
                "order": i
            }
        })
        lesson_pk += 1

with open("e:/belajar docker/Final-Project-Simple-LMS/simple-lms/code/courses/fixtures/large_data.json", "w") as f:
    json.dump(fixtures, f, indent=2)

print("Berhasil men-generate large_data.json dengan 14 lesson per course!")
