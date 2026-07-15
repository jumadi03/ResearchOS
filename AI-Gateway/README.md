# ResearchOS AI Gateway

## Version

0.3

## Description

ResearchOS AI Gateway adalah pintu masuk seluruh layanan AI
pada ResearchOS.

Repository ini juga memuat fondasi domain ResearchOS untuk architecture
governance, discovery, modeling, dan runtime. Architecture governance bersifat
deterministik; keluaran AI hanya bersifat advisory dan tidak dapat menetapkan
status compliance.

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
    architecture/  # discovery dan governance arsitektur
    discovery/     # scientific object dan evidence discovery
    infrastructure/
    kernel/        # kontrak lintas domain
    modeling/      # scientific modeling
    router/
    runtime/
    services/
    models/
    settings.py
```

## Architecture governance

Istilah `ArchitectureLaw` di codebase berarti aturan internal arsitektur
software, bukan hukum negara atau regulasi. Hasil validator fondasi ditandai
`NOT_IMPLEMENTED` dan tidak boleh dianggap compliant hanya karena tidak
memiliki violation.

Spesifikasi terminologi, trust boundary, status, dan reproducibility gate ada
di [`Documents/ARCHITECTURE_GOVERNANCE.md`](../Documents/ARCHITECTURE_GOVERNANCE.md).

Architecture Graph MVP tersedia melalui `ArchitectureGraphBuilder`. Builder
memindai source Python dan menghasilkan snapshot JSON deterministik berisi
project, module, class, dependency, source revision, serta SHA-256 content hash.

Architecture Law Engine mendukung law bundle berversi, content hash, scope
node/path, severity, masa berlaku, JSON integrity verification, dan resolution
trace yang menjelaskan mengapa setiap law diterapkan atau dikecualikan.

Compliance Engine dapat mengeksekusi forbidden-import rules dan package public
namespace rules terhadap Architecture Graph. Setiap finding menyimpan law,
fact, node, source path, import line, remediation, dan graph hash sebagai bukti.

Review Engine menyediakan session yang terikat graph hash, keputusan per
finding, waiver dengan expiry, append-only audit trail, finalization fail-safe,
stale-review detection, JSON deterministik, dan SHA-256 review hash.

ARC Generator menerapkan approval dan integrity gates lalu menghasilkan paket
berisi graph, law bundle, compliance report, review, Markdown, manifest, serta
checksums. Paket diverifikasi sebelum ditulis dan tidak menimpa ARC lama secara
diam-diam.

ARC Publisher merender Markdown kanonis menjadi HTML responsif dan PDF A4
berhalaman. Publisher menghitung ulang checksum, menerbitkan manifest/ARC ID
baru, dan mempertahankan paket sumber tanpa perubahan.

Architecture API menyediakan workflow bertahap pada prefix `/architecture`.
Project root dan output root dikendalikan server melalui
`ARCHITECTURE_PROJECT_ROOT` dan `ARCHITECTURE_OUTPUT_ROOT`; klien tidak dapat
memilih path filesystem. Snapshot setiap tahap dan paket ARC disimpan di output
root yang terkonfigurasi.

Run index direhidrasi otomatis dari snapshot terverifikasi saat service mulai.
Seluruh endpoint architecture memerlukan Bearer token yang dipetakan ke actor
oleh konfigurasi JSON `ARCHITECTURE_API_PRINCIPALS`. Konfigurasi kosong menolak
semua akses, dan identity review selalu berasal dari principal terautentikasi.
Principal memiliki role least-privilege: `scanner`, `law_admin`, `reviewer`,
`approver`, `publisher`, dan `auditor`. ARC manifest mencatat principal
publisher pada field `generated_by`.

Persistence menggunakan atomic file replacement, `fsync`, dan lock file lintas
proses. ARC diterbitkan melalui staging-directory commit dan released ARC
directory bersifat immutable. Startup recovery membersihkan interrupted
internal staging serta dapat menemukan ARC valid walaupun location pointer
belum sempat ditulis.

Schema registry menegakkan format versi `major.minor`, menolak versi future
atau unknown, dan menyediakan migrasi eksplisit untuk Compliance/Review `0.9`
serta ARC Manifest `1.0`. Migrasi tidak pernah mengubah released ARC in-place;
hasil upgrade memperoleh hash dan identity baru.

Operational observability tersedia pada `GET /health`, `GET /ready`, dan
`GET /metrics`. Endpoint metrics memakai format Prometheus dan hanya dapat
diakses principal dengan role `auditor`. Setiap request menerima atau membuat
`X-Correlation-ID`, yang juga dicatat pada structured JSON logs dan audit event.
Audit keamanan serta publikasi ARC disimpan append-only di
`<ARCHITECTURE_OUTPUT_ROOT>/audit/security-publication.jsonl`.

GitHub Actions menjalankan architecture quality gates pada pull request dan
push ke `main`: regression dengan minimum 90% application coverage, kontrak
schema/ARC/persistence, pemeriksaan konsistensi dependency, kompilasi source,
dan audit vulnerability. Branch protection sebaiknya mewajibkan ketiga check
`Regression and coverage`, `Schema, ARC, and persistence gates`, serta
`Dependency security` sebelum merge.
