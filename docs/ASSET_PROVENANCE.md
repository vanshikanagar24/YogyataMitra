# Asset Provenance & Attribution Register

This document provides a formal, verifiable record of origin, creation metadata, legal rights, cryptographic checksums, and runtime fallback behavior for all static media assets distributed with the **YogyataMitra** platform repository.

---

## 1. Summary Asset Register

| Asset Path | Format | Size (Bytes) | SHA-256 Checksum | Origin / Source | Legal Rights Basis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `frontend/public/images/parliament_hero.jpg` | JPEG | 930,522 | `9ec95cb8cdd3ae9126c8d075f967eaad0bdcd9d7055c3fa7d41f22e214544eca` | Synthetic AI Generation (DeepMind Imagen via Antigravity) | Synthetic AI output subject to service terms; no CC0 dedication asserted; open academic/civic demonstration |
| `frontend/public/images/logo.png` | PNG | 176,789 | `5bb85cde33814e00c42e07769b2bbd0aba3c58f39f09422e188186df286f7bf7` | Original YogyataMitra project asset created for this repository | MIT License (Repository Root) |

---

## 2. Asset Specification: `parliament_hero.jpg`

### 2.1 File Characteristics
- **Relative Repository Path**: `frontend/public/images/parliament_hero.jpg`
- **File Format**: JPEG (`image/jpeg`)
- **Dimensions**: `1920 × 1080` pixels
- **Aspect Ratio**: 16:9
- **Color Profile**: sRGB
- **File Size**: 930,522 bytes (~908.7 KB)
- **SHA-256 Hash**:
  ```text
  9ec95cb8cdd3ae9126c8d075f967eaad0bdcd9d7055c3fa7d41f22e214544eca
  ```

### 2.2 Synthetic Origin & Generation Metadata
- **Engine / Pipeline**: Google DeepMind Imagen generation pipeline through the Antigravity platform (`generate_image`).
- **Generation Timestamp**: `2026-09-18T13:35:00+05:30` (Artifact: `parliament_hero_1789718716022.jpg`).
- **Original Generation Prompt**:
  > *"Photorealistic wide shot of Sansad Bhavan, the Indian Parliament building in New Delhi, with the Indian national tricolor flag flying on the central dome, lush manicured green lawns, trees and gardens in the foreground, bright clear daylight sky with subtle clouds, stately institutional architecture, majestic, dignified public service feel."*
- **Subject & Nature**: Synthetic artistic depiction of Sansad Bhavan (Parliament of India). It is **not** an official Government of India photograph.

### 2.3 Legal Status, Rights & Distribution Basis
This hero image was generated using Google DeepMind Imagen through the Antigravity platform on 2026-09-18. It is a synthetic artistic depiction of Sansad Bhavan and is not an official Government of India photograph.

No CC0 dedication is asserted for this asset. The project records the generation provenance and relies on the applicable service terms concerning generated user content. The asset is included for this open-source academic/civic demonstration, subject to applicable third-party rights and service terms.

- **A. Generation Provenance**: Generated synthetically via text-to-image AI prompt on 2026-09-18 as part of the YogyataMitra demonstration interface.
- **B. Ownership & Service Terms**: Generated pursuant to the Google Terms of Service and Google Generative AI Additional Terms of Service (specifically regarding generated user content).
- **C. Copyright Uncertainty**: The legal status and copyrightability of purely machine-generated synthetic imagery remain subject to evolving domestic and international legal frameworks. The project does not assert affirmative copyright ownership over the generated output, nor does it make definitive legal claims regarding public domain status.
- **D. Distribution Purpose**: The asset is distributed within this repository strictly for open-source academic, educational, and civic demonstration purposes, subject to applicable third-party rights and service terms.
- **E. Absence of an Asserted CC0 Dedication**: No CC0 dedication is asserted for this asset. The project records the generation provenance and relies on the applicable service terms concerning generated user content.

### 2.4 Resiliency & Fallback Guarantee
- **Zero Layout Shift (CLS)**: The hero container in `frontend/src/app/page.tsx` specifies fixed minimum height (`min-h-[480px] sm:min-h-[520px]`) and a solid background color class `bg-primary-dark` (`#0c2340`).
- **Gradient Overlay**: The image is rendered under a high-contrast dark navy linear gradient (`from-navy-900/95 via-navy-900/85 to-navy-900/40`).
- **Graceful Failure**: If the network connection drops, the asset is removed, or the static file server encounters an error:
  1. The layout collapses zero pixels.
  2. The background renders solid navy blue.
  3. All foreground typography, search inputs, CTAs, and badges maintain full contrast compliance (`> 7.5:1`, exceeding WCAG 2.2 AAA text contrast requirements).
- **Accessibility**: Provided with descriptive `alt="Sansad Bhavan - Parliament of India in New Delhi"` in compliance with accessible HTML standards.

---

## 3. Asset Specification: `logo.png`

### 3.1 File Characteristics
- **Relative Repository Path**: `frontend/public/images/logo.png`
- **File Format**: PNG (`image/png` with 8-bit alpha transparency)
- **File Size**: 176,789 bytes (~172.6 KB)
- **SHA-256 Hash**:
  ```text
  5bb85cde33814e00c42e07769b2bbd0aba3c58f39f09422e188186df286f7bf7
  ```

### 3.2 Origin & Rights Basis
`logo.png` is an original YogyataMitra project asset created for this repository and is distributed under the project's MIT License.

---

## 4. Verification Command

To independently verify the SHA-256 checksums of the static assets on Windows PowerShell:

```powershell
Get-FileHash D:\YogyataMitra\frontend\public\images\* -Algorithm SHA256 | Format-Table -AutoSize
```

Or on Linux / macOS:

```bash
sha256sum frontend/public/images/*
```
