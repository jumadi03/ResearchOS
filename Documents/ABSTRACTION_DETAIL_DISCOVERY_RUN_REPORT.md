# Laporan Run Discovery Abstraksi ↔ Detail

## Status

- Jenis artefak: laporan observasi pelaksanaan discovery
- Tanggal pelaksanaan: 2026-07-18
- Status hasil: candidate discovery; belum menjadi evidence
- Status screening manusia: belum dilakukan
- Status extraction: belum dilakukan
- Status review ilmiah: belum dilakukan
- Paket asal:
  `Documents/ABSTRACTION_DETAIL_DISCOVERY_QUERY_PACK.md`

Laporan ini mencatat apa yang benar-benar terjadi ketika paket kueri
dijalankan melalui pipeline discovery kanonik ResearchOS. Jumlah hasil,
peringkat provider, judul, DOI, atau kemunculan pada beberapa provider tidak
menyatakan dukungan ilmiah terhadap Model 6S.

## 1. Run Diagnostik Awal

Run awal memaksakan dua concept—Jung/MBTI dan Abstraksi–Detail—dalam satu query
`AND`.

- Run ID: `discovery-bc789d3d7fca44589788f7f915cb91ce`
- Snapshot hash:
  `b0b3d87e91e05daa2b15326d6f6cefb54f25bce50395dfbea9a2a54bb36cdb6d`
- Record unik: 25
- OpenAlex: 0 dari total provider 0
- Crossref: 25 dari total provider 1.319
- Semantic Scholar: gagal dengan HTTP 429; retryable

### Observasi

Query tersebut terlalu ketat bagi OpenAlex, tetapi hasil Crossref tetap
mengandung banyak penggunaan `intuition` yang tidak membahas batas construct
yang dicari. Run ini dipertahankan sebagai diagnostic provenance dan tidak
digunakan sebagai baseline kualitas.

Beberapa judul tampak berpotensi relevan berdasarkan judul saja, antara lain:

- `Psychological types`;
- `Sensation Seeking and the Sensing-Intuition Scale of the Myers-Briggs Type
  Indicator`;
- `The Jungian Psychological Functions Sensing and Intuition and the
  Preference for Art`; dan
- `PART ONE ABSTRACT THINKING VERSUS CONCRETE SENSATION...`.

Daftar tersebut **bukan keputusan screening**. Abstract atau teks sumber belum
diperiksa.

## 2. Run Pembanding QF-1A — Jung/MBTI

- Run ID: `discovery-1f3a792e173743f2b09c00fd963d2a92`
- Snapshot hash:
  `724dc03a70f4ae8b3b5f0047431a60d225f9c22bd72c64d5816995a4e478ed2f`
- Record unik setelah deduplikasi: 49
- OpenAlex: 25 dari total provider 50
- Crossref: 25 dari total provider 673.310
- Semantic Scholar: gagal dengan HTTP 429; retryable

Judul yang tampak layak masuk antrean screening berdasarkan judul saja:

- `Contexts of the birth of intuition in Jung’s psychology`;
- `Does the Myers-Briggs Type Indicator Measure Anything Beyond the NEO Five
  Factor Inventory?`;
- `Evaluating the MBTI Form M in a South African context`;
- `Correlations among the Group Embedded Figures Test, the Myers-Briggs Type
  Indicator and Demographic Characteristics: A Business School Study`; dan
- `An experimental study of individual differences in intuition: preference
  and process`.

Sebagian hasil lain memakai `intuition` sebagai pengambilan keputusan umum,
pendidikan, kreativitas, atau topik lain. Relevansinya belum ditetapkan.

## 3. Run Pembanding QF-1B — Abstraksi–Detail

- Run ID: `discovery-ace181b4cf274d40a78f4eb2915afce3`
- Snapshot hash:
  `3ce4036b09f83cb69b7ca9b496f921570603feca082a737a23018ad6d36c9177`
- Record unik: 50
- OpenAlex: 25 dari total provider 111.239
- Crossref: 25 dari total provider 1.622.710
- Semantic Scholar: gagal dengan HTTP 429; retryable

Judul yang tampak layak masuk antrean screening berdasarkan judul saja:

- `Basic objects in natural categories`;
- `Concept learning at different levels of abstraction by pigeons, monkeys,
  and people`;
- `Conditional reasoning, representation, and level of abstraction`; dan
- `Cognition and Categorization`.

Banyak hasil Crossref berasal dari seni, bahasa, komputasi, dan penggunaan
`abstract` atau `concrete` yang tidak berkaitan langsung dengan individual
differences dalam pemrosesan psikologis. Query ini masih terlalu luas.

## 4. Kesimpulan Operasional

1. Pipeline ResearchOS benar-benar menghubungi provider dan menyimpan snapshot
   immutable.
2. Pemisahan QF-1A dan QF-1B lebih berguna daripada query gabungan awal.
3. Pencarian berbasis istilah saja belum cukup untuk menetapkan construct.
4. Crossref menghasilkan ruang kandidat sangat besar dan noise tinggi.
5. OpenAlex memberi kandidat yang lebih terbatas pada QF-1A, tetapi QF-1B
   masih sangat luas.
6. Semantic Scholar belum berhasil karena rate limit 429. Kegagalan tetap
   tercatat dan tidak diperlakukan sebagai hasil kosong.
7. Belum ada evidence ilmiah yang diterima.

## 5. Langkah Berikutnya

Langkah berikutnya bukan theory construction. Langkah yang sah adalah:

1. lakukan screening judul dan abstract terhadap kandidat QF-1A;
2. lakukan screening judul dan abstract terhadap kandidat QF-1B;
3. tandai penggunaan istilah yang tidak relevan dengan alasan eksplisit;
4. pilih candidate untuk controlled acquisition;
5. ulang Semantic Scholar setelah rate limit memungkinkan, sebagai run baru;
6. perbaiki QF-1B dengan istilah pengukuran dan individual differences setelah
   hasil screening awal tersedia; dan
7. pertahankan semua hasil sebagai candidate sampai extraction dan human
   review yang sah selesai.
