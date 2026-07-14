# ResearchOS AI Gateway

## Version

0.3

## Description

ResearchOS AI Gateway adalah pintu masuk seluruh layanan AI
pada ResearchOS.

Saat ini mendukung:

- FastAPI
- Ollama
- Qwen3

## Menjalankan

Aktifkan Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Jalankan

```powershell
uvicorn app.main:app --reload
```

Swagger

```
http://127.0.0.1:8000/docs
```

---

## Struktur

```
app/
    router/
    services/
    models/
    settings.py
```