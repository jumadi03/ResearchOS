# Paket Kueri Discovery: Abstraksi ↔ Detail

## Status dan Batas Ilmiah

- Jenis artefak: paket kueri discovery yang dapat dieksekusi
- Construct sasaran: `Abstraksi ↔ Detail`
- Hubungan asal: kandidat pengembangan dari pembahasan
  `Intuisi ↔ Sensing/Sensasi`
- Status ilmiah: hipotesis eksploratif; belum tervalidasi
- Status evidence: belum tersedia
- Status review manusia: belum tersedia
- Pemilik pertanyaan: Jumadi
- Disusun: 2026-07-18

Paket ini mengubah gagasan awal menjadi rencana pencarian yang dapat dijalankan
melalui pipeline discovery kanonik ResearchOS. Paket ini tidak menyatakan bahwa
`Abstraksi ↔ Detail` merupakan construct yang benar, tidak menyamakannya dengan
fungsi psikologis Jung, dan tidak mempromosikan hasil pencarian menjadi
evidence, canonical knowledge, construct, model, atau theory.

## 1. Pertanyaan Utama

> Apakah kecenderungan berorientasi pada representasi abstrak dibandingkan
> rincian konkret merupakan construct psikologis yang dapat dibedakan secara
> konseptual dan empiris dari Intuition ↔ Sensation/Sensing dalam tradisi Jung
> dan MBTI?

Pertanyaan ini sengaja menguji **perbedaan**, bukan mengasumsikan kesamaan.

## 2. Batas Construct

### 2.1 Definisi kerja untuk pencarian

`Abstraksi` sementara berarti kecenderungan memusatkan pemrosesan atau
representasi pada pola, relasi, kategori, prinsip, atau makna yang melampaui
rincian kejadian tertentu.

`Detail` sementara berarti kecenderungan memusatkan pemrosesan atau
representasi pada ciri spesifik, data konkret, unsur lokal, atau rincian
kejadian tertentu.

Definisi tersebut hanya membantu pencarian. Definisi itu belum merupakan
definisi final Model 6S.

### 2.2 Hal yang belum boleh disimpulkan

Pencarian tidak boleh menganggap bahwa:

- abstraksi identik dengan intuition;
- detail identik dengan sensation, sensing, atau pengindraan;
- kedua kutub membentuk satu dimensi bipolar;
- preferensi merupakan trait yang stabil;
- satu kutub lebih baik daripada kutub lain;
- pasangan ini independen dari kemampuan kognitif, pendidikan, budaya,
  pekerjaan, atau konteks tugas; atau
- construct tersebut merupakan salah satu dari enam sumbu yang tervalidasi.

### 2.3 Kriteria pembeda minimum

Construct baru hanya layak dipertimbangkan berbeda dari Intuition ↔
Sensation/Sensing apabila literature candidate nantinya memungkinkan review
terhadap sedikitnya:

1. definisi dan unit analisis yang berbeda;
2. operasionalisasi atau pengukuran yang berbeda;
3. validitas diskriminan;
4. prediksi empiris yang tidak sepenuhnya dijelaskan construct terdahulu; dan
5. competing explanation yang telah diperiksa.

## 3. Kontrak Discovery Bersama

Setiap keluarga kueri dijalankan sebagai `ScientificQuestion`,
`DiscoveryContract`, dan `SearchPlan` terpisah karena
`ScientificQueryPlanner` kanonik saat ini menghasilkan satu keluarga kueri
untuk setiap rencana.

| Field kanonik | Nilai paket |
| --- | --- |
| `project_id` | `researchos-default` |
| `source_categories` | `scholarly_index` |
| `providers` | `openalex`, `crossref`, `semantic_scholar` |
| `languages` | `en`, `id` |
| `document_types` | journal article, review, systematic review, meta-analysis, book chapter |
| `evidence_types` | construct definition, measurement, validity, empirical association, theoretical comparison |
| `maximum_depth` | 1 |
| `limit_per_provider` | 25 |
| `retrieval_budget` | 75 per keluarga |
| `license_policy` | metadata yang diizinkan provider; full text hanya melalui acquisition policy |
| `human_review_policy` | seluruh hasil tetap candidate sampai review manusia yang sah |

### Inclusion rules

- sumber ilmiah membahas definisi, pengukuran, validitas, atau hubungan empiris
  dari sedikitnya satu construct yang dicari;
- sumber menyatakan populasi, konteks, metode, atau basis teoritis yang dapat
  diperiksa;
- sumber menyediakan metadata dan provenance yang cukup untuk resolusi
  identitas;
- karya historis atau teoritis dapat masuk apabila relevansinya terhadap batas
  construct dapat diperiksa; dan
- temuan yang mendukung maupun menentang dipertahankan.

### Exclusion rules

- halaman populer, kuis kepribadian, pemasaran, dan tipologi tanpa metode atau
  sumber ilmiah;
- penggunaan kata `abstract`, `detail`, `intuition`, atau `sensing` yang tidak
  merujuk pada construct psikologis atau proses kognitif yang relevan;
- klaim yang hanya mengulang label MBTI tanpa definisi, pengukuran, atau
  provenance;
- duplikat yang telah disatukan oleh identity resolution;
- dokumen yang tidak memungkinkan pemeriksaan hubungan klaim dengan sumber;
  dan
- `Seed Theory` mengenai kehidupan, AI, atau consciousness yang tidak membahas
  construct sasaran.

### Stopping conditions

- anggaran 75 candidate per keluarga tercapai;
- seluruh provider telah selesai atau mencatat kegagalan eksplisit;
- tidak ada candidate baru setelah deduplikasi pada satu perluasan kueri yang
  disetujui;
- batas waktu atau rate limit provider mengharuskan run dihentikan; atau
- manusia menghentikan pencarian dengan alasan tercatat.

## 4. Keluarga Kueri

Istilah di bawah adalah input `QueryConcept`. Planner kanonik akan membuat
ekspresi `AND` antar-concept dan `OR` antara preferred term dengan synonym
dalam concept yang sama.

### QF-1 — Asal dan batas Jung/MBTI

**Tujuan:** menemukan definisi sumber dan penelitian yang memungkinkan
perbandingan historis-konseptual.

QF-1 dijalankan sebagai dua run pembanding. Run pertama mencari construct
sumber Jung/MBTI. Run kedua mencari construct Abstraksi–Detail. Hubungan
keduanya dinilai pada screening manusia; hubungan tersebut tidak dipaksakan
dengan `AND` dalam satu query.

#### QF-1A — Construct sumber Jung/MBTI

| Concept lokal | Preferred term | Synonyms |
| --- | --- | --- |
| perception-pair | Jungian intuition sensation | Jung psychological types intuition sensation; MBTI intuition sensing; sensing intuition scale; intuitive sensing preference |

Draft query QF-1A:

```text
("Jungian intuition sensation" OR "psychological types intuition sensation"
 OR "MBTI intuition sensing" OR "sensing intuition scale"
 OR "intuitive sensing preference")
```

#### QF-1B — Kandidat construct Abstraksi–Detail

| Concept lokal | Preferred term | Synonyms |
| --- | --- | --- |
| representation-level | abstract concrete processing | abstraction detail orientation; abstract concrete cognition; global local cognitive style; abstract concrete representation; level of abstraction |

Draft query QF-1B:

```text
("abstract concrete processing" OR "abstraction detail orientation"
 OR "abstract concrete cognition" OR "global local cognitive style"
 OR "abstract concrete representation" OR "level of abstraction")
```

### QF-2 — Dukungan empiris

**Tujuan:** mencari apakah kecenderungan abstrak-detail memiliki
operasionalisasi, stabilitas, dan prediksi empiris yang dapat diuji.

| Concept lokal | Preferred term | Synonyms |
| --- | --- | --- |
| abstraction-detail | abstract concrete processing | abstraction detail orientation; level of abstraction; global local cognitive style; abstract concrete representation |
| empirical-measurement | psychological measurement | individual differences measure; scale validation; behavioral task; psychometric assessment |

Draft query:

```text
("abstract concrete processing" OR "abstraction detail orientation"
 OR "level of abstraction" OR "global local cognitive style"
 OR "abstract concrete representation")
AND
("psychological measurement" OR "individual differences measure"
 OR "scale validation" OR "behavioral task" OR "psychometric assessment")
```

### QF-3 — Sanggahan dan validitas diskriminan

**Tujuan:** mencari overlap, kegagalan replikasi, kelemahan pengukuran, atau
penjelasan bahwa construct tidak berbeda.

| Concept lokal | Preferred term | Synonyms |
| --- | --- | --- |
| abstraction-detail-validity | abstract concrete construct validity | abstraction detail discriminant validity; global local validity; abstract concrete psychometric validity |
| critical-test | construct overlap | redundant construct; measurement confound; discriminant validity failure; replication failure |

Draft query:

```text
("abstract concrete construct validity"
 OR "abstraction detail discriminant validity" OR "global local validity"
 OR "abstract concrete psychometric validity")
AND
("construct overlap" OR "redundant construct" OR "measurement confound"
 OR "discriminant validity failure" OR "replication failure")
```

### QF-4 — Teori dan construct pesaing

**Tujuan:** menguji apakah fenomena sudah dijelaskan lebih baik oleh construct
yang ada.

| Concept lokal | Preferred term | Synonyms |
| --- | --- | --- |
| target-process | abstract concrete cognition | abstraction detail processing; global local processing; level of construal |
| competing-construct | cognitive style | field dependence independence; analytic holistic cognition; need for cognition; openness to experience; construal level theory |

Draft query:

```text
("abstract concrete cognition" OR "abstraction detail processing"
 OR "global local processing" OR "level of construal")
AND
("cognitive style" OR "field dependence independence"
 OR "analytic holistic cognition" OR "need for cognition"
 OR "openness to experience" OR "construal level theory")
```

## 5. Urutan Eksekusi

1. Jalankan QF-1A dan QF-1B sebagai run pembanding untuk menetapkan batas
   historis dan terminologis.
2. Jalankan QF-4 untuk mencegah penemuan ulang construct yang telah ada.
3. Jalankan QF-2 untuk mengumpulkan candidate dukungan empiris.
4. Jalankan QF-3 walaupun QF-2 memberi hasil yang tampak mendukung.
5. Simpan setiap `DiscoveryRun` sebagai snapshot immutable.
6. Lakukan metadata collection dan identity resolution.
7. Screening manusia menilai relevansi; hasil pencarian tidak sama dengan
   evidence.
8. Candidate terpilih baru dapat melalui acquisition, extraction, dan human
   review normal.

Urutan tersebut tidak memberi prioritas epistemik kepada hasil yang mendukung.
QF-4 dan QF-3 merupakan bagian wajib, bukan pencarian opsional.

## 6. Deduplikasi dan Hubungan Antar-run

- deduplikasi di dalam run memakai mekanisme kanonik ResearchOS;
- duplikat lintas keluarga harus ditandai sebagai satu karya yang ditemukan
  melalui beberapa tujuan kueri;
- provenance setiap kemunculan—provider, query family, source query, rank,
  page, request URL, dan response hash—tidak boleh dihapus;
- DOI digunakan bila tersedia, tetapi ketiadaan DOI tidak otomatis berarti
  karya berbeda; dan
- perbedaan metadata tidak boleh diselesaikan dengan menimpa raw observation.

## 7. Resume dan Reproducibility

Snapshot discovery dan raw provider pages sudah immutable dan
content-addressed. Namun engine kanonik saat ini membuat `run_id` baru dan
tidak melanjutkan cursor dari run parsial. Karena itu:

- jangan menyatakan run terputus sebagai “resumed” secara teknis;
- jalankan ulang keluarga yang sama sebagai run baru;
- pertahankan question, contract, plan, concepts, source definitions, dan
  batas tahun yang sama;
- catat run sebelumnya sebagai predecessor pada catatan pelaksanaan;
- bandingkan serta deduplikasi hasil berdasarkan provenance; dan
- perubahan istilah, provider, anggaran, atau batas tahun harus menjadi versi
  paket/rencana baru, bukan kelanjutan diam-diam.

Dengan aturan ini pekerjaan dapat diteruskan lintas sesi tanpa mengklaim
dukungan cursor-resume yang belum tersedia.

## 8. Matriks Screening Manusia

Setiap candidate minimal diberi keputusan dan alasan terhadap:

| Pertanyaan screening | Nilai yang diizinkan |
| --- | --- |
| Relevan terhadap construct sasaran? | ya / tidak / tidak pasti |
| Membahas Jung/MBTI atau construct lain? | Jung/MBTI / construct lain / keduanya / tidak ada |
| Jenis kontribusi? | definisi / pengukuran / validitas / hasil empiris / kritik / teori |
| Arah terhadap hipotesis? | mendukung / menentang / campuran / tidak menentukan |
| Unit analisis jelas? | ya / tidak |
| Metode dapat diperiksa? | ya / tidak / tidak berlaku |
| Risiko salah padan istilah? | rendah / sedang / tinggi |
| Layak ke acquisition? | ya / tidak / perlu review lanjutan |

Label arah tidak boleh ditetapkan hanya dari judul atau abstract yang
terpotong.

## 9. Keputusan yang Dilarang pada Tahap Discovery

Paket atau hasil run tidak boleh digunakan untuk:

- menetapkan nama final sumbu;
- menyatakan jumlah sumbu adalah enam;
- menerima atau menolak hipotesis Model 6S;
- membuat canonical construct;
- membuat edge pada canonical knowledge graph;
- membangun theory;
- menganggap citation sebagai dukungan; atau
- menganggap jumlah hasil sebagai kekuatan evidence.

## 10. Definition of Done Paket

Paket dianggap siap dijalankan apabila:

- pertanyaan dan batas construct eksplisit;
- empat keluarga kueri tersedia;
- dukungan, sanggahan, validitas, dan competing explanation tercakup;
- ketiga provider berasal dari Canonical Source Registry;
- inclusion, exclusion, anggaran, stopping condition, dan human-review policy
  eksplisit;
- keterbatasan resume dinyatakan;
- hasil tetap candidate-only; dan
- tidak ada klaim evidence atau theory baru yang dibuat.
