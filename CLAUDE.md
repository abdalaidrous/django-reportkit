# django-reportkit — دليل المشروع لـ Claude

حزمة Django فوق pyreportkit (المجلد المجاور `../reportkit`). الحزمة مسؤولة عن الاستعلام والفلاتر والإجماليات (aggregate على كل البيانات المفلترة) والعرض والتصدير؛ أما التخطيط والتنسيق فمن pyreportkit عبر `ReportBuilder` و`TableBuilder`. لا تضف منطق عرض هنا، ولا منطق Django في pyreportkit.

## البنية

```text
src/django_reportkit/
├── conf.py                 # settings.REPORTKIT فوق DEFAULTS (يُقرأ عند كل وصول)
├── reports/                # params.py (ReportParams قابلة للتخزين مع الـ Job)، columns.py، rows.py (QuerysetRows كسولة)، base.py (Report)، model.py (ModelReport)
├── exports/                # formats.py (ExportFormat)، policy.py (مباشر/خلفية/رفض)، runner.py (تصدير إلى ملف مؤقت)
├── jobs/                   # models.py (ReportJob)، service.py، backends/ (sync, thread, celery)، storage.py، cleanup.py، tasks.py (Celery)
├── errors/                 # exceptions.py، messages.py (رسائل ودّية)، handlers.py (تسجيل + صفحة خطأ)
├── views/                  # preview.py، export.py، jobs.py، urls.py (report_urlpatterns)
├── urls.py                 # روابط الـ Jobs (app_name = django_reportkit)
└── templates/django_reportkit/
```

## قواعد

- التقرير يُبنى من `ReportParams` (قيم الفلاتر والمستخدم واللغة) لا من `HttpRequest`، حتى يعمل نفسه في الطلب وفي الخلفية.
- الصفوف عبر `values().iterator()`؛ لا تحوّلها إلى قائمة. المعاينة وحدها تستخدم Paginator.
- الأخطاء: سجّل التفاصيل (`errors.handlers.log_error`) وأظهر `friendly_message` فقط.
- كل الكتابة إلى ملفات مؤقتة أو storage، لا إلى الذاكرة.

## التحقق

لا يوجد Django في `.venv` الخاص بـ pyreportkit؛ تُشغَّل الاختبارات في صورة Docker الخاصة بـ pyreportkit مع ربط المجلدين:

```powershell
docker build -t reportkit-pdf D:/projects/console/reportkit
docker run --rm -v "D:/projects/console/reportkit:/app" -v "D:/projects/console/django-reportkit:/dj" -w /dj reportkit-pdf sh -c "pip install -q 'Django>=4.2' pytest-django && pip install -q --no-deps -e /dj && python -m pytest -q"
```

بعد تعديل `ReportJob` شغّل `makemigrations django_reportkit` بالإعدادات `tests.settings`.
