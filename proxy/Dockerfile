FROM python:3.10-slim
WORKDIR /app
RUN pip install flask pandas requests gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
