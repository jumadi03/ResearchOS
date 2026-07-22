# ResearchOS Scientific Governance Framework

## Status

- Identifier: SGF-000
- Document status: project-owner-accepted framework vision
- Formal ratification status: not defined by current repository governance
- Classification: scientific governance framework
- Owner: ResearchOS project
- Authority: project owner
- Recorded: 2026-07-17
- Scope: long-term scientific governance hierarchy and document family
- Child standards: SGF-010 through SGF-100
- Related documents: `Documents/RESEARCHOS_VISION.md`,
  `Documents/RESPONSIBLE_EVOLUTION_VISION.md`,
  `Documents/SCIENTIFIC_INTERFACE_VISION.md`, and
  `Documents/ARCHITECTURE_GOVERNANCE.md`

Dokumen SGF-000 menyimpan kerangka kanonik jangka panjang untuk tata kelola
ilmiah ResearchOS. Ia menetapkan keluarga dokumen, urutan dependensi, dan
posisinya terhadap metodologi, arsitektur, serta implementasi.

SGF-000 belum meratifikasi isi rinci setiap standar turunannya. SGF-010 dan
SGF-050 sampai SGF-100 berstatus **direncanakan**. SGF-020, SGF-030, dan
SGF-040 telah disusun sebagai project-owner-directed operational standards,
tetapi formal ratification tetap belum didefinisikan oleh governance
repository saat ini. Kode dan kontrak kanonik yang sudah ada tetap menjadi
Single Source of Truth untuk perilaku sistem yang telah diimplementasikan.

## Tujuan

ResearchOS memerlukan tata kelola yang mengatur ilmu pengetahuan yang
dijalankan oleh perangkat lunak, bukan hanya tata kelola yang memastikan
perangkat lunaknya berkembang dengan benar.

Posisi konseptual kerangka ini adalah:

```text
Scientific Philosophy
    -> Scientific Governance Framework (SGF)
        -> Scientific Methodology
            -> ResearchOS Architecture
                -> Implementation
```

Architecture Governance, laws, dan specifications tetap mengatur integritas
arsitektur perangkat lunak. SGF berada di atas lapisan tersebut untuk
menetapkan prinsip ilmiah, otoritas manusia, makna objek, lifecycle,
kepercayaan, keputusan, etika, evolusi, dan kualitas yang harus diwujudkan
oleh arsitektur.

Dengan pemisahan ini, ResearchOS dapat digunakan dalam kedokteran, fisika,
ekonomi, ilmu sosial, atau bidang lain dengan metodologi dan implementasi yang
berbeda, tetapi tetap berbagi konstitusi ilmiah yang sama.

## Hierarki dan Urutan Resmi

```text
SGF-000  Scientific Governance Framework
    |
    +-- SGF-010  Scientific Constitution
    |
    +-- SGF-020  Human Authority & Decision Matrix
    |
    +-- SGF-030  Canonical Scientific Ontology
    |
    +-- SGF-040  Research Object Lifecycle Standard
    |
    +-- SGF-050  Scientific Trust & Confidence Framework
    |
    +-- SGF-060  Scientific Decision Record Standard
    |
    +-- SGF-070  Privacy, Ethics & Sensitive Research Policy
    |
    +-- SGF-080  Capability & Product Map
    |
    +-- SGF-090  Scientific Evolution Framework
    |
    `-- SGF-100  Scientific Quality Framework
```

Urutan penyusunan ini bersifat dependency-aware:

1. Konstitusi menetapkan apa yang tidak boleh dilanggar.
2. Human Authority menetapkan siapa yang boleh memutuskan, kapan, dan dengan
   syarat apa.
3. Ontology menetapkan arti setiap objek ilmiah.
4. Lifecycle menetapkan bagaimana objek berubah secara sah.
5. Trust Framework menetapkan cara kualitas evidence, ketidakpastian, dan
   kepercayaan dinilai.
6. Decision Record menjaga memori ilmiah atas keputusan.
7. Privacy and Ethics menetapkan batas penggunaan yang bertanggung jawab.
8. Capability Map menelusurkan prinsip hingga implementasi dan compliance.
9. Scientific Evolution mengatur cara ResearchOS belajar dan mengusulkan
   evolusi dirinya.
10. Scientific Quality menetapkan ukuran mutu sistem dan capability.

Dokumen yang lebih akhir bergantung pada definisi dan batas yang ditetapkan
oleh dokumen sebelumnya. Penyusunannya tidak boleh membalik dependensi itu
atau membuat istilah tandingan yang tidak diperlukan.

## SGF-010 — Scientific Constitution

Status: direncanakan.

Scientific Constitution akan menjadi rujukan tertinggi dalam keluarga SGF.
Ruang lingkup yang direncanakan meliputi:

- purpose;
- scientific authority;
- definition of scientific truth;
- evidence principle;
- human authority;
- AI limitation;
- reproducibility;
- traceability;
- correction principle;
- retraction principle; dan
- governance principle.

Seluruh subsystem pada akhirnya harus dapat menunjukkan kesesuaiannya dengan
konstitusi ini.

## SGF-020 — Human Authority & Decision Matrix

Status: operational standard version 1.0; formal ratification not defined.

Dokumen:
`Documents/SGF_020_HUMAN_AUTHORITY_DECISION_MATRIX.md`.

Standar ini akan menetapkan bukan hanya siapa yang berwenang, tetapi juga:

- siapa;
- kapan;
- mengapa;
- evidence yang diwajibkan;
- review yang diwajibkan;
- separation of duties;
- masa berlaku keputusan;
- mekanisme appeal; dan
- mekanisme rollback.

Contoh alur yang harus dapat dinyatakan secara eksplisit:

```text
Theory Acceptance
    -> Reviewer
        -> Required Evidence
            -> Approval
                -> Publication
```

## SGF-030 — Canonical Scientific Ontology

Status: operational standard version 1.0; formal ratification not defined.

Dokumen:
`Documents/SGF_030_CANONICAL_SCIENTIFIC_ONTOLOGY.md`.

Ontology akan menyatukan makna objek ilmiah agar AI, backend, antarmuka,
Knowledge Graph, dan subsystem lain tidak memakai definisi yang berbeda.
Objek yang perlu dicakup antara lain:

- Observation;
- Fact;
- Claim;
- Evidence;
- Interpretation;
- Inference;
- Hypothesis;
- Construct;
- Relationship;
- Model;
- Theory; dan
- Publication.

Terminologi existing canonical code harus diverifikasi sebelum definisi atau
nama baru diperkenalkan.

## SGF-040 — Research Object Lifecycle Standard

Status: operational standard version 1.0; formal ratification not defined.

Dokumen:
`Documents/SGF_040_RESEARCH_OBJECT_LIFECYCLE_STANDARD.md`.

Evidence, Theory, Publication, dan objek penelitian lain dapat memiliki
lifecycle yang berbeda, tetapi harus memakai bahasa lifecycle, transition,
authority, provenance, correction, dan invalidation yang konsisten. Standar
ini akan menjadi rujukan bersama untuk perubahan status objek ilmiah.

## SGF-050 — Scientific Trust & Confidence Framework

Status: direncanakan.

Framework ini tidak boleh mereduksi kebenaran ilmiah menjadi satu angka
confidence. Penilaian yang direncanakan mencakup:

- evidence quality;
- authority;
- bias;
- replication;
- consistency;
- contradiction;
- coverage; dan
- uncertainty.

Confidence hanya boleh menjadi salah satu hasil yang transparan dari dimensi
tersebut, bukan sinonim untuk kebenaran.

## SGF-060 — Scientific Decision Record Standard

Status: direncanakan.

Scientific Decision Record akan menjaga **scientific memory**, bukan sekadar
mencatat keputusan akhir. Struktur yang direncanakan meliputi:

- context;
- evidence;
- alternatives;
- decision;
- rationale;
- consequences;
- risk;
- rollback;
- superseded state; dan
- review.

Standar ini diarahkan menjadi salah satu fondasi Scientific Evolution
Framework dan Evolution Engine.

## SGF-070 — Privacy, Ethics & Sensitive Research Policy

Status: direncanakan.

Policy ini akan menetapkan batas dan kewajiban ketika ResearchOS digunakan
untuk penelitian sensitif, termasuk dalam konteks rumah sakit, universitas,
pemerintah, dan industri. Implementasi sektoral tidak boleh mengurangi
otoritas manusia, perlindungan subjek, traceability, atau accountability.

## SGF-080 — Capability & Product Map

Status: direncanakan.

Peta ini akan menyediakan traceability menyeluruh:

```text
Vision
    -> Scientific Principle
        -> Governance
            -> Subsystem
                -> Engine
                    -> Capability
                        -> Scientific Object
                            -> Workflow
                                -> API
                                    -> Workspace
                                        -> Test
                                            -> Compliance
                                                -> Implementation
```

Peta tidak boleh mengklaim capability sebagai tersedia tanpa hubungan yang
dapat diverifikasi ke implementasi dan pengujiannya.

## SGF-090 — Scientific Evolution Framework

Status: direncanakan.

Framework ini akan menjadi fondasi governance bagi Evolution Engine:

```text
Observation
    -> Learning
        -> Proposal
            -> Simulation
                -> Verification
                    -> Approval
                        -> Evolution
```

ResearchOS diarahkan untuk belajar tentang dirinya dengan metode ilmiah.
Learning dan proposal tidak memberikan kewenangan bagi AI untuk mengubah
canonical knowledge, governance, architecture, atau implementation tanpa
verifikasi dan persetujuan manusia yang sah.

## SGF-100 — Scientific Quality Framework

Status: direncanakan.

Scientific Quality berbeda dari Scientific Trust. Trust terutama menilai
evidence dan dasar kepercayaan ilmiah; Quality menilai mutu sistem dan
capability. Dimensi yang direncanakan meliputi:

- coverage;
- completeness;
- consistency;
- reproducibility;
- traceability;
- maintainability;
- auditability; dan
- explainability.

Setiap capability pada akhirnya harus memiliki ukuran kualitas yang eksplisit
dan dapat diuji.

## Aturan Pengembangan SGF

Untuk setiap standar turunan:

1. lakukan dependency verification terhadap kode, kontrak, lifecycle, enum,
   service boundary, dan dokumen kanonik yang sudah ada;
2. tetapkan architecture position dan hubungannya dengan standar SGF lain;
3. bedakan existing contract, extension, dan perubahan yang tidak kompatibel;
4. nyatakan domain invariant dan hal yang tidak boleh dilanggar;
5. periksa bypass, stale state, provenance, authority, dan rollback;
6. siapkan unit, integration, architecture, dan compliance test plan;
7. tetapkan Definition of Done sebelum implementasi;
8. jangan mengubah kode sebelum verification dan positioning selesai
   dilaporkan serta disetujui; dan
9. jangan menyatakan standar diratifikasi atau capability tersedia tanpa
   bukti dan otoritas yang sah.

## Hasil yang Dituju

SGF memungkinkan ResearchOS berkembang sebagai **Scientific Research
Operating System**, bukan hanya sistem yang membantu penelitian. Semua domain
dapat mengembangkan metodologi masing-masing sambil mempertahankan prinsip
ilmiah, otoritas manusia, provenance, lifecycle, accountability, dan kualitas
yang sama.
