# Runtime Layer

## Overview

Runtime Layer bertanggung jawab menjalankan provider secara aman,
reliable, dan dapat diperluas.

Layer ini menggunakan pola Reliability Pattern.

---

# Reliability Pattern

Setiap mekanisme reliability wajib mengikuti struktur:

Feature
├── Config
├── Policy
└── Executor

## Config

Menyimpan konfigurasi.

Tidak mengandung logika.

Contoh:

RetryConfig

---

## Policy

Mengambil keputusan.

Tidak menjalankan proses.

Contoh:

RetryPolicy

---

## Executor

Menjalankan mekanisme.

Tidak mengambil keputusan.

Executor selalu menggunakan Policy.

Contoh:

RetryExecutor

---

# Dependency Rule

Executor → Policy → Config

Config tidak bergantung pada komponen lain.

Policy bergantung pada Config.

Executor bergantung pada Policy.

---

# Evolution Rule

Komponen reliability baru wajib mengikuti pola yang sama.

Contoh:

Fallback

Circuit Breaker

Rate Limiter

Timeout

Observability

---

# Architecture Goal

Menjaga:

- High Cohesion
- Low Coupling
- Dependency Injection
- Open Closed Principle
- Evolutionary Refactoring