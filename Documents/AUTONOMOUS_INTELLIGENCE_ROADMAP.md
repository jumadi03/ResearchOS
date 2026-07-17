# Autonomous Intelligence Roadmap

## Status

- Document status: project-owner-accepted strategic direction
- Formal ratification status: not defined by current repository governance
- Classification: long-term architectural vision and sequencing guide
- Owner: ResearchOS project
- Authority: project owner
- Recorded: 2026-07-17
- Scope: provider independence, native scientific intelligence, and local-first evolution
- Related documents: `Documents/RESEARCHOS_VISION.md`,
  `Documents/SCIENTIFIC_KNOWLEDGE_ROADMAP.md`,
  `Documents/INTERNET_DISCOVERY_ROADMAP.md`, and
  `Documents/ARCHITECTURE_GOVERNANCE.md`

Dokumen ini menyimpan pedoman jangka panjang bagi evolusi kecerdasan
ResearchOS. Dokumen ini bukan klaim bahwa seluruh kemampuan telah tersedia,
bukan spesifikasi sprint aktif, dan bukan izin untuk melewati kontrak,
provenance, review, atau otoritas manusia. Existing canonical code tetap
menjadi Single Source of Truth untuk keadaan implementasi aktual.

## Strategic Position

Kemandirian ResearchOS tidak berarti membangun model bahasa umum baru.
Kemandirian berarti proses ilmiah inti tetap utuh, dapat dijalankan, dan dapat
diaudit ketika vendor, model, atau layanan AI diganti atau tidak tersedia.

Model bahasa adalah capability untuk tugas bahasa. Ia bukan pusat otoritas
ilmiah dan bukan sumber kebenaran sistem. Kekuatan asli ResearchOS berada
pada:

- scientific workflow;
- canonical knowledge;
- evidence dan provenance;
- scientific objects dan lifecycle;
- deterministic reasoning;
- validation dan measurement; serta
- governance dan human authority.

## Levels of Independence

### Level 0 — API Dependent

ResearchOS bertindak sebagai orchestrator bagi penyedia eksternal seperti
OpenAI, Gemini, Claude, Ollama, atau penyedia lain. Keberlangsungan capability
AI masih bergantung pada API yang digunakan.

### Level 1 — Multi-Provider

AI Router memisahkan workflow ResearchOS dari penyedia. Model dapat diganti
tanpa mengubah kontrak workflow atau otoritas ilmiah. Level ini mengikuti
prinsip AI replaceability dan AI agnosticism.

### Level 2 — Local AI First

Local LLM, embedding, OCR, dan speech menjadi pilihan utama. Cloud AI menjadi
fallback yang eksplisit. Pergantian local dan cloud tidak boleh mengubah
identity, provenance, review state, atau hasil deterministic gates.

### Level 3 — ResearchOS Native Intelligence

Discovery, screening, normalization, deduplication, lifecycle, provenance,
workflow, dan knowledge graph dijalankan sebagai kemampuan asli ResearchOS.
Pekerjaan deterministik tidak boleh dibuat bergantung pada LLM tanpa kebutuhan
arsitektural yang terbukti.

### Level 4 — Scientific Reasoning Engine

ResearchOS membangun reasoning ilmiah melalui algoritma yang dapat diperiksa,
misalnya:

- graph reasoning;
- Bayesian reasoning;
- rule engine;
- constraint solver; dan
- scientific inference.

Alur konseptualnya adalah:

```text
Evidence
    -> Relationship
        -> Conflict
            -> Inference
                -> Hypothesis
```

Setiap inference harus menyimpan metode, input identity, provenance, versi,
ketidakpastian, dan batas validitasnya. Reasoning tidak boleh mengubah
hypothesis menjadi kebenaran atau menggantikan review manusia.

### Level 5 — Fully Autonomous Scientific Platform

ResearchOS mengoordinasikan language, reasoning, knowledge, evidence,
validation, measurement, dan publication engines sebagai satu scientific
platform. Otonomi berarti workflow dapat berjalan dengan intervensi minimal,
bukan hilangnya governance atau human scientific authority.

## Target Intelligence Stack

```text
ResearchOS
    -> Language Layer
    -> Scientific Reasoning Layer
    -> Knowledge Layer
    -> Evidence Layer
    -> Storage
```

Language Layer dapat memakai model bahasa lokal atau eksternal yang dapat
diganti. Scientific Reasoning, Knowledge, Evidence, dan Storage harus
mempertahankan kontrak kanonik serta tidak menjadikan keluaran LLM sebagai
fakta tanpa verifikasi.

Dalam pembagian berbasis engine, arah jangka panjangnya adalah:

```text
ResearchOS
    -> Language Engine
    -> Reasoning Engine
    -> Knowledge Engine
    -> Validation Engine
    -> Measurement Engine
    -> Publication Engine
```

AI terutama melayani Language Engine. Engine lain boleh menggunakan AI sebagai
alat bantu, tetapi keputusan kanonik dan release gates harus berasal dari
kontrak serta metode yang dapat diperiksa.

## Autonomous Intelligence Sequence

Urutan strategis yang diusulkan adalah:

1. **AI-001 — Local Embedding**
2. **AI-002 — Local Reranker**
3. **AI-003 — Scientific Parser**
4. **AI-004 — Knowledge Reasoner**
5. **AI-005 — Hypothesis Engine**
6. **AI-006 — Scientific Planner**
7. **AI-007 — Local Language Model Integration**
8. **AI-008 — ResearchOS Native Intelligence**

Urutan ini sengaja menempatkan local language model setelah fondasi struktur
pengetahuan dan reasoning. Item-item tersebut belum menjadi sprint resmi
sampai melalui dependency verification, architecture positioning, contract
review, invariant dan safety review, test plan, serta Definition of Done.

## Language Tasks

Tugas yang secara alami tetap membutuhkan language capability meliputi:

- natural-language summary;
- translation;
- explanation dan conversation;
- paraphrase; dan
- article drafting.

Keluaran tugas tersebut harus dibedakan dari source content dan canonical
scientific assertions. Terjemahan tidak menggantikan teks sumber; ringkasan
tidak menggantikan evidence; drafting tidak menggantikan publication review.

## Native Scientific Tasks

Kemampuan berikut harus sebisa mungkin berdiri sebagai kontrak dan algoritma
ResearchOS sendiri:

- discovery dan source enumeration;
- metadata normalization dan deduplication;
- evidence lifecycle dan provenance;
- knowledge graph construction;
- support dan conflict analysis;
- confidence computation dengan metode eksplisit;
- replication dan evidence-gap detection;
- theory construction dari accepted evidence;
- validation, measurement, dan governance.

Knowledge graph berskala besar harus dapat menjawab pertanyaan struktural
seperti paper yang bertentangan, theory yang kekurangan evidence, atau
observation yang belum direplikasi tanpa mewajibkan panggilan LLM.

## Permanent Invariants

Setiap pekerjaan yang mengikuti roadmap ini wajib mempertahankan:

1. **Provider replaceability** — mengganti model atau vendor tidak mengubah
   scientific contract.
2. **Local-first portability** — sistem dapat berevolusi menuju operasi lokal
   tanpa merusak workflow.
3. **Deterministic authority** — status, hash, lifecycle, admission, dan
   release gate ditentukan oleh kode serta data kanonik.
4. **Evidence-first reasoning** — inference dan theory hanya memakai evidence
   yang memenuhi review dan provenance requirements.
5. **Explicit uncertainty** — confidence, assumptions, conflicts, dan batas
   inference tidak boleh disembunyikan.
6. **Human scientific authority** — otomatisasi tidak meratifikasi evidence
   atau menetapkan kebenaran.
7. **Traceability and reproducibility** — setiap hasil dapat ditelusuri dan
   diulang dari input, metode, versi, serta konfigurasi.
8. **No silent AI bypass** — service langsung maupun integrasi AI tidak boleh
   melewati canonical gates.

## Working Rule

Roadmap ini memberi arah, bukan menggantikan urutan roadmap aktif. Implementasi
baru hanya dimulai setelah posisinya terhadap existing canonical code
diverifikasi dan disetujui. Satu sprint tetap menghasilkan satu deliverable
yang dapat diuji, dengan architecture compliance dan regression validation.

## Long-Term Success Criterion

ResearchOS mencapai kemandirian yang bernilai ketika discovery, evidence
management, provenance, workflow, knowledge graph, reasoning, validation, dan
governance tetap berfungsi tanpa ketergantungan pada satu vendor, satu model,
atau bahkan keberadaan LLM untuk mayoritas proses ilmiah.

Model bahasa boleh terus berkembang dan diganti. Identitas ResearchOS tetap
berasal dari kemampuannya membangun pengetahuan ilmiah secara terstruktur,
evidence-first, dapat diaudit, reproducible, dan berada di bawah otoritas
manusia.
