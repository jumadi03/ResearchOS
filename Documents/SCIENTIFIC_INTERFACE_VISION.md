# Scientific Interface Vision

## Status

- Document status: project-owner-accepted interface vision
- Formal ratification status: not defined by current repository governance
- Classification: long-term product and interaction direction
- Owner: ResearchOS project
- Authority: project owner
- Recorded: 2026-07-17
- Scope: scientific workspaces, object-centered interaction, contextual
  intelligence, collaboration, and ResearchOS desktop evolution
- Related documents: `Documents/RESEARCHOS_VISION.md`,
  `Documents/AUTONOMOUS_INTELLIGENCE_ROADMAP.md`,
  `Documents/SCIENTIFIC_KNOWLEDGE_ROADMAP.md`,
  `Documents/SCIENTIFIC_DATA_STORAGE.md`, and
  `Documents/VALIDATION_GUIDE.md`

Dokumen ini menyimpan pedoman jangka panjang untuk antarmuka ResearchOS. Ia
bukan klaim bahwa seluruh workspace telah tersedia, bukan spesifikasi desain
visual final, dan bukan izin untuk membangun capability tanpa dependency
verification serta architecture positioning. Existing canonical code tetap
menjadi Single Source of Truth untuk keadaan implementasi aktual.

## Product Identity

ResearchOS bukan sekadar web application. ResearchOS diarahkan menjadi
**Scientific Operating System**.

Antarmukanya harus membantu peneliti bekerja dengan pertanyaan, sumber,
evidence, construct, theory, validation, workflow, dan publication sebagai
objek ilmiah yang nyata. Browser adalah salah satu media penyajian; ia tidak
menentukan model interaksi atau identitas produk.

## Primary Design Decision

ResearchOS tidak dibangun sebagai kumpulan halaman yang bertambah setiap kali
fitur baru dibuat. Antarmuka dibangun sebagai kumpulan workspace yang berpusat
pada objek ilmiah.

Pengguna berpindah di antara:

- `ScientificQuestion`;
- source document dan literature record;
- evidence;
- construct;
- relationship;
- theory;
- validation;
- artifact;
- workflow; dan
- project context.

Setiap objek membuka workspace yang sesuai. Context panel, provenance,
lifecycle, relationships, permissions, available actions, AI assistance, dan
activity history mengikuti objek aktif tersebut.

Prinsip ini disebut **object-centric scientific workspace**.

## Interface Evolution

### Era 1 — Research Workspace

Era ini membangun fondasi untuk menggantikan folder penelitian yang terpisah.
Workspace awal mencakup:

- Home;
- Projects;
- Documents;
- Literature;
- Evidence; dan
- Tasks.

Struktur kerja tetap berada di dalam project:

```text
Research
    -> Project
        -> Literature
        -> Notes
        -> Evidence
        -> Publication
```

Tujuannya bukan sekadar pengelolaan file. Setiap dokumen dan hasil kerja mulai
memiliki identity, provenance, lifecycle, dan hubungan ke project.

### Era 2 — Scientific Knowledge

Antarmuka berkembang dari file-centric menjadi knowledge-centric:

```text
Paper
    -> Claim
        -> Evidence
            -> Construct
                -> Theory
```

Setiap objek dapat dibuka dan diperiksa. Theory workspace, misalnya,
memperlihatkan evidence, methods, conflicts, references, confidence,
uncertainty, review state, dan provenance tanpa menyatakan theory sebagai
kebenaran final.

### Era 3 — Scientific Intelligence

AI dan native reasoning bekerja terhadap objek aktif, bukan menjadi chatbot
yang terpisah dari penelitian.

Ketika theory aktif, action yang relevan dapat meliputi:

- validate;
- compare;
- measure;
- detect weakness;
- find conflict;
- find missing evidence; dan
- propose hypothesis.

Ketika evidence atau paper aktif, action berubah menjadi:

- summarize;
- inspect source context;
- extract variables dan methods;
- compare evidence;
- find related evidence; dan
- propose constructs.

Semua action tunduk pada role, lifecycle, provenance, canonical admission
gates, dan human authority. AI action adalah capability yang mengikuti
context; ia bukan otoritas ilmiah.

### Era 4 — Collaborative Research

ResearchOS mendukung penelitian multi-peneliti tanpa kehilangan jejak:

```text
Scientific Object
    -> created by Researcher A
    -> validated by Researcher B
    -> reviewed by Researcher C
```

Kolaborasi harus mempertahankan:

- actor identity;
- attributed decisions;
- append-only review history;
- role separation;
- task and workflow ownership;
- rationale;
- version and content hash; dan
- conflict visibility.

### Era 5 — Scientific Operating System

Seluruh capability tampil sebagai satu research desktop, bukan kumpulan
produk yang terpisah:

```text
ResearchOS Desktop
    -> Explorer
    -> Project Workspace
    -> Discovery
    -> Knowledge Atlas
    -> Theory Builder
    -> Evidence Explorer
    -> Literature Browser
    -> Validation
    -> Publication Studio
    -> Architecture Studio
    -> AI Studio
    -> Dataset Manager
    -> Workflow Designer
    -> Administration
```

Desktop ini tetap dapat diimplementasikan melalui browser, desktop shell, atau
media lain. Kontrak objek dan workflow tidak boleh bergantung pada media
presentasinya.

## Canonical Workspace Anatomy

Layout jangka panjang terdiri dari area yang hidup dan mengikuti context:

```text
+---------------------------------------------------------------+
| Project and global navigation                                 |
+----------------+---------------------------+------------------+
| Navigation     | Main Canvas               | Context Panel    |
|                |                           |                  |
| Workspace      | Active scientific object  | Identity         |
| Discovery      | graph, document, canvas,  | Provenance       |
| Knowledge      | notebook, or workflow     | Lifecycle        |
| Validation     |                           | Relationships    |
| Publication    |                           | Permissions      |
| Architecture   |                           |                  |
+----------------+---------------------------+------------------+
| Contextual AI and native scientific actions                   |
+---------------------------------------------------------------+
| Activity and reproducible timeline                            |
+---------------------------------------------------------------+
```

Panel tidak boleh menampilkan informasi yang dibuat-buat ketika canonical data
tidak tersedia. Missing, loading, unavailable, stale, rejected, and
permission-denied states harus tampil eksplisit.

## Knowledge Atlas

Knowledge Atlas adalah salah satu identitas utama ResearchOS: peta ilmu yang
dapat dijelajahi lintas skala.

```text
Scientific Field
    -> Domain
        -> Construct
            -> Theory
                -> Paper
                    -> Claim
                        -> Evidence
                            -> Exact Source Passage
```

Pengguna dapat melakukan zoom out untuk melihat struktur bidang ilmu dan zoom
in sampai paragraf sumber. Perubahan tingkat visual tidak boleh menghapus
provenance, review status, uncertainty, atau perbedaan antara observation,
source-author interpretation, dan ResearchOS inference.

## Research Canvas

Research Canvas adalah ruang komposisi object-centric, bukan papan gambar
tanpa kontrak. Node dapat mewakili:

- question;
- evidence;
- construct;
- relationship;
- theory;
- measurement; dan
- publication.

Drag, drop, connect, disconnect, dan validate harus diterjemahkan menjadi
command domain yang terotorisasi dan dapat diaudit. Perubahan visual tidak
boleh langsung memutasi canonical knowledge tanpa validation dan persistence
gate.

## Reproducible Timeline

Timeline menyajikan sejarah penelitian yang dapat diputar ulang:

```text
Question created
    -> literature discovered
    -> evidence reviewed
    -> knowledge intake completed
    -> theory changed
    -> validation recorded
    -> publication created
```

Timeline berasal dari event dan provenance kanonik. Ia bukan sekadar activity
log kosmetik. Replay harus membedakan historical state dari current state dan
tidak boleh menjalankan ulang side effect tanpa command eksplisit.

## Architecture Studio

Architecture Studio menyajikan arsitektur sebagai sistem yang dapat diperiksa:

```text
Capability
    -> Engine
        -> Subsystem
            -> Dependency
                -> Law
                    -> Compliance
```

Visualisasi harus berasal dari Architecture Graph, law resolution, compliance
results, review decisions, dan ARC provenance yang kanonik. UI tidak boleh
mengubah status compliance atau waiver hanya melalui perubahan visual lokal.

## Contextual Intelligence

AI panel mengikuti objek aktif. Capability yang ditawarkan harus:

- relevan terhadap tipe objek dan lifecycle;
- dibatasi oleh role dan policy;
- menyebutkan input yang digunakan;
- memisahkan source content dari generated content;
- menyimpan provider, model, configuration, dan output provenance bila
  material;
- memperlihatkan uncertainty dan failure;
- tidak meratifikasi evidence atau theory; dan
- tidak melewati canonical service boundary.

Native reasoning dan deterministic validators harus tampil setara sebagai
scientific actions, bukan disembunyikan di bawah label AI.

## Bilingual Scientific Interface

Bahasa Indonesia adalah bahasa antarmuka default bagi project owner saat ini.
Antarmuka harus mendukung tampilan bilingual:

- Bahasa Indonesia untuk navigation, command, status, explanation, form,
  validation message, dan accessibility label;
- bahasa sumber untuk scientific source content;
- terjemahan Bahasa Indonesia sebagai representasi tambahan yang terikat pada
  source hash;
- pilihan untuk melihat bahasa sumber dan terjemahan secara berdampingan; dan
- penanda yang jelas untuk source text, translation, summary, interpretation,
  dan inference.

Terjemahan tidak menggantikan teks sumber. Judul, kutipan, evidence, identifier,
hash, dan provenance dari sumber harus tetap tersedia secara persis.

## Interaction Invariants

Setiap implementasi antarmuka wajib mempertahankan:

1. **Object-centricity** — interaction berangkat dari scientific object dan
   context, bukan penambahan halaman tanpa model domain.
2. **Canonical truth** — UI membaca status dari canonical service; local state
   bukan scientific authority.
3. **Provenance visibility** — pengguna dapat menelusuri asal, actor, review,
   version, dan source location.
4. **Lifecycle visibility** — provisional, pending, accepted, rejected,
   validated, ratified, published, stale, dan unavailable tidak disamarkan.
5. **Human authority** — action berisiko memerlukan role, rationale, dan review
   yang sesuai.
6. **No silent mutation** — drag-drop, AI action, bulk action, dan automation
   tidak boleh melewati command serta persistence boundary.
7. **Contextual capability** — action yang ditawarkan mengikuti object type,
   current state, permissions, dan available evidence.
8. **Scientific separation** — source, observation, interpretation,
   inference, translation, dan generated content tetap dapat dibedakan.
9. **Accessibility** — keyboard, focus, contrast, semantic labels, reduced
   motion, dan assistive technology menjadi bagian Definition of Done.
10. **Responsive workspace** — informasi kritis tetap dapat digunakan pada
    ukuran layar berbeda tanpa menghilangkan provenance atau review state.
11. **Explicit system state** — loading, empty, error, offline, retry,
    conflict, stale, and permission states ditampilkan secara jujur.
12. **Scalable consistency** — capability baru memperluas object actions dan
    workspace contracts tanpa memecah pola interaksi.

## Delivery Sequence

Urutan produk jangka panjang diringkas sebagai berikut:

| Stage | Focus | Primary products |
| --- | --- | --- |
| UI Foundation | Workspace shell dan project navigation | Project Workspace, Document Explorer |
| Scientific Workspace | Scientific objects | Literature Explorer, Evidence Workspace, Scientific Notebook |
| Knowledge Workspace | Knowledge representation | Knowledge Atlas, Theory Builder, Research Canvas |
| Intelligence Workspace | Object-context intelligence | Contextual AI Panel, Hypothesis Assistant, Validation Assistant |
| Collaboration Workspace | Multi-researcher governance | Review Workspace, Provenance Timeline, Workflow and Task Board |
| Scientific OS | Integrated capabilities | Research Desktop, Architecture Studio, Publication Studio |

UI Foundation adalah baseline teknis bagi lima era evolusi, bukan era produk
yang terpisah. Setiap stage baru tetap harus mempertahankan kemampuan dan
invariant stage sebelumnya.

## Working Rule for Interface Tasks

Sebelum mengubah UI, pekerjaan wajib:

1. memverifikasi scientific object, constructor, enum, lifecycle, API,
   permissions, provenance, dan service boundary yang benar-benar tersedia;
2. menetapkan posisi workspace, subsystem, engine, dan capability;
3. membedakan canonical data, derived read model, translation, dan local UI
   state;
4. mendefinisikan interaction invariant dan jalur failure;
5. meninjau bilingual content, accessibility, responsive behavior, loading,
   empty, stale, conflict, and permission states;
6. merencanakan unit, integration, browser, accessibility, architecture, dan
   regression tests; serta
7. menetapkan Definition of Done sebelum implementasi.

Visual baru tidak boleh dibuat hanya berdasarkan mock data bila canonical API
sebenarnya tersedia. Jika capability backend belum ada, UI harus menyatakan
ketiadaan tersebut dan tidak mensimulasikan keberhasilan ilmiah.

## Long-Term Success Criterion

Antarmuka ResearchOS berhasil ketika peneliti merasa bekerja di dalam ruang
ilmiah yang utuh: memilih objek, memahami context, melihat evidence dan
provenance, menjalankan action yang sesuai, meninjau perubahan, berkolaborasi,
dan menghasilkan publication tanpa kehilangan jejak bagaimana pengetahuan
terbentuk.

Identitas UI bukan ditentukan oleh jumlah halaman atau banyaknya panel AI.
Identitasnya ditentukan oleh konsistensi object-centric workspace, kejujuran
scientific state, keterlacakan, bilingual accessibility, dan kemampuan tumbuh
bersama model ilmiah ResearchOS.
