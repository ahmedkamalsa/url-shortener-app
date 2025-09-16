# Dockerfile (النسخة النهائية والمضمونة)

# المرحلة الأولى: البناء (Builder) - لا تغيير هنا
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
# ننشئ البيئة الافتراضية هنا ونثبت المكتبات بداخلها
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# المرحلة الثانية: التشغيل (Runner)
FROM python:3.11-slim
WORKDIR /app

# ننسخ البيئة الافتراضية الجاهزة بالكامل من مرحلة البناء
COPY --from=builder /opt/venv /opt/venv

# ننسخ كل كود التطبيق الخاص بنا
COPY . .

# === الحل الحاسم ===
# الآن، بدلاً من تخمين المسار، نستخدم المسار الكامل والصريح للبيئة الافتراضية
# لتشغيل uvicorn. هذا يضمن أننا نستخدم النسخة الصحيحة المثبتة.
ENV PATH="/opt/venv/bin:$PATH"

# نضيف مستخدمًا غير مسؤول (هذه الخطوة اختيارية الآن ولكنها ممارسة جيدة)
RUN useradd --create-home appuser
USER appuser

# نحدد الأمر الذي سيتم تشغيله
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
