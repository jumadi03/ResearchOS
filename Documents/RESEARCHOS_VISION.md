# Visi ResearchOS

## Status

- Document status: project-owner-accepted vision
- Formal ratification status: not defined by current repository governance
- Classification: project vision
- Owner: ResearchOS project
- Authority: project owner
- Recorded: 2026-07-17
- Scope: long-term identity, direction, and success criteria
- Related documents: `README.md`,
  `Documents/AUTONOMOUS_INTELLIGENCE_ROADMAP.md`,
  `Documents/SCIENTIFIC_INTERFACE_VISION.md`,
  `Documents/SCIENTIFIC_KNOWLEDGE_ROADMAP.md`,
  `Documents/INTERNET_DISCOVERY_ROADMAP.md`,
  `Documents/SCIENTIFIC_DATA_STORAGE.md`, and
  `Documents/ARCHITECTURE_GOVERNANCE.md`

Dokumen ini menyimpan visi jangka panjang ResearchOS. Ia bukan roadmap
implementasi, spesifikasi komponen, klaim bahwa seluruh kemampuan sudah
tersedia, atau pengganti kontrak dan kode kanonik. Roadmap dan sprint
menentukan urutan realisasi; visi ini menentukan arah dan identitas yang tidak
boleh hilang ketika implementasi berkembang.

Visi interaksi dan evolusi workspace dicatat secara khusus dalam
`Documents/SCIENTIFIC_INTERFACE_VISION.md`. Antarmuka ResearchOS diarahkan
menjadi object-centric scientific workspace, bukan kumpulan halaman atau
chatbot yang terpisah dari objek, provenance, lifecycle, dan human authority.

## Identitas

ResearchOS bukan sekadar platform AI untuk penelitian. Visi jangka panjangnya
adalah menjadi **Scientific Knowledge Operating System**: infrastruktur
komputasi untuk seluruh siklus penelitian ilmiah.

ResearchOS menerjemahkan metodologi ilmiah menjadi sistem komputasi. Posisi
konseptualnya adalah:

```text
Human Scientist
    -> Scientific Workspace
        -> ResearchOS Kernel and Scientific Subsystems
            -> AI, Storage, Compute, and Network
```

Peneliti berada di atas sebagai pemegang otoritas ilmiah. AI dan infrastruktur
berada di bawah sebagai instrumen. ResearchOS berada di tengah untuk mengubah
tujuan, metode, keputusan, dan hasil penelitian menjadi objek serta workflow
yang eksplisit, dapat diperiksa, dan dapat direproduksi.

## Scientific Workspace

Ketika membuka ResearchOS, peneliti tidak seharusnya hanya melihat chatbot.
Peneliti melihat ruang kerja ilmiah:

```text
Research Question
    -> Discovery
    -> Evidence
    -> Knowledge
    -> Theory
    -> Validation
    -> Publication
```

Setiap tahap direpresentasikan sebagai objek nyata dengan:

- identity;
- provenance;
- lifecycle;
- history;
- review;
- relationships;
- applicable AI capabilities; dan
- human decision authority.

Interaksi utama bukan hanya “cari paper tentang X”, melainkan “saya sedang
membangun pengetahuan atau teori tentang X”. ResearchOS kemudian membantu
memperlihatkan evidence, contradiction, missing evidence, suggested
observation, uncertainty, dan kebutuhan replikasi tanpa menyatakan sendiri
bahwa suatu teori benar.

## Knowledge Atlas

Visi pengalaman pengetahuan ResearchOS bukan folder atau kumpulan file,
melainkan **Knowledge Atlas** yang dapat dijelajahi lintas tingkat:

```text
Scientific Field
    -> Domain
        -> Construct
            -> Theory
                -> Source Document
                    -> Evidence
                        -> Observation or Exact Source Passage
```

Pengguna dapat memperkecil tampilan untuk melihat hubungan lintas bidang atau
memperbesar hingga satu paper, satu evidence, dan satu kalimat sumber.
Perpindahan tingkat tidak boleh menghilangkan provenance atau mengubah
assertion menjadi fakta tanpa review.

## Theory Builder

Theory Builder tidak menetapkan kebenaran. Ia memperlihatkan keadaan teori
berdasarkan evidence yang dapat ditelusuri, misalnya:

- jumlah evidence yang mendukung;
- jumlah evidence yang bertentangan;
- confidence beserta metode penghitungannya;
- missing observations;
- replication needs;
- unresolved conflicts;
- quality and bias assessments; dan
- status human review.

Theory construction wajib evidence-first. Provisional, pending, rejected,
missing-review, atau incompletely provenanced evidence tidak boleh menjadi
dasar canonical knowledge atau theory.

## Publication

ResearchOS diarahkan untuk menghasilkan paket publikasi dari objek penelitian
yang sudah melalui review, antara lain:

- journal paper;
- conference paper;
- technical report;
- dataset;
- supplementary material;
- evidence brief; dan
- knowledge package.

Otomasi publikasi tidak menghapus review manusia. Setiap keluaran harus
mempertahankan input identity, provenance, version, validation state, content
hash, dan hubungan ke evidence yang mendasarinya.

## Domain and AI Agnosticism

ResearchOS diarahkan untuk bekerja lintas disiplin tanpa mengubah prinsip inti
Kernel. Kedokteran, fisika, ilmu sosial, atau domain lain dapat memiliki
scientific objects, methods, dan policies yang berbeda, tetapi tetap memakai
kontrak umum seperti:

- Project;
- Workspace;
- Workflow;
- Task;
- Context;
- Artifact;
- Scientific Object;
- Evidence;
- Theory; dan
- Provenance.

AI juga harus dapat diganti tanpa mengubah scientific authority. AI membantu
discovery, extraction, analysis, explanation, dan drafting, tetapi tidak
meratifikasi evidence, menetapkan kebenaran, atau melewati governance.

Kemandirian jangka panjang ResearchOS tidak bergantung pada pembangunan model
bahasa sendiri. Model bahasa diposisikan sebagai Language Layer yang dapat
diganti, sedangkan discovery, evidence, provenance, knowledge, deterministic
reasoning, validation, measurement, workflow, dan governance berkembang
sebagai kemampuan asli ResearchOS. Tahapan evolusi ini dicatat dalam
`Documents/AUTONOMOUS_INTELLIGENCE_ROADMAP.md`.

## Architecture as an Inspectable System

ResearchOS juga memandang arsitektur perangkat lunak sebagai objek yang dapat
ditelusuri:

```text
Architecture
    -> Capability
    -> Engine
    -> Law
    -> Compliance
```

Arsitektur harus dapat divisualisasikan, diuji, diberi provenance, dan diaudit.
Prinsip ini mendukung evolusi ResearchOS tanpa kehilangan batas subsystem,
service, capability, dan trust.

## Institutional Direction

Dalam jangka panjang, ResearchOS dapat mendukung struktur institusi:

```text
University
    -> Faculty
    -> Research Group
    -> Project
    -> Knowledge
```

Skala institusional tidak boleh mengurangi pemisahan project, akses berbasis
peran, provenance, review, atau human authority.

## A Computational Language for Scientific Research

Visi terdalam ResearchOS adalah membangun bahasa komputasi untuk penelitian
ilmiah. Vocabulary seperti Scientific Object, Workflow, Context, Artifact,
Evidence, Theory, Provenance, Architecture Law, dan Canonical Domain Model
memungkinkan proses ilmiah direpresentasikan secara konsisten lintas disiplin.

ResearchOS seharusnya membantu pengguna membedakan:

- observation;
- phenomenon;
- research question;
- scientific construct;
- hypothesis;
- theory;
- evidence;
- interpretation; dan
- inference.

Sistem tidak langsung menjawab pertanyaan besar sebagai kebenaran final.
Sistem membantu pengguna membangun penelitian sedikit demi sedikit sampai
kesimpulan dapat dipertanggungjawabkan.

## Permanent Principles

Lima prinsip berikut adalah identitas yang harus dipertahankan pada setiap
roadmap dan sprint:

1. **Reproducibility** — proses dan hasil dapat diulang dari input, versi,
   konfigurasi, serta metode yang tercatat.
2. **Traceability** — setiap kesimpulan dapat ditelusuri kembali melalui
   reasoning, evidence, source representation, dan exact source location.
3. **Governance** — lifecycle, authority, review, policy, dan perubahan
   bersifat eksplisit serta dapat diaudit.
4. **Human authority** — keputusan ilmiah terakhir tetap berada pada manusia.
5. **Evidence-first** — teori lahir dari evidence yang diterima, bukan evidence
   dipilih untuk membenarkan teori.

## Success Criterion

ResearchOS berhasil bukan ketika AI-nya terlihat paling pintar, melainkan
ketika pengguna mempercayai hasilnya karena setiap langkah yang membentuk
kesimpulan dapat ditelusuri, diperiksa, diulang, dan diwariskan.

Identitas ResearchOS tidak ditentukan oleh penggunaan AI. Identitasnya
ditentukan oleh kemampuannya membuat proses lahirnya pengetahuan ilmiah
menjadi eksplisit, dapat diaudit, reproducible, governed, dan tetap berada di
bawah otoritas manusia.
