# CSV Data Schema Analysis & Cleaning Strategy

## Summary of Structures

### FILE STRUCTURE PATTERNS

#### **PATTERN 1: Multi-Level Headers (2-3 levels)**
These files have hierarchical headers with dimension categories spanning multiple columns.

**Kesehatan_angka_harapan_hidup.csv** ✓ COMPLEX
- Row 0: Title "Angka Harapan Hidup (AHH)..."
- Row 1: **Dimensions**: Laki-laki (cols 1-5) | Perempuan (cols 6-10)
- Row 2: Years 2020-2024 repeated for each dimension
- **Structure**: 37 provinces × 2 dimensions × 5 years = 370 rows (after unpivot)
- **Action**: 
  1. Pull first 5 columns (province + Laki-laki data)
  2. Pull second 5 columns (province + Perempuan data)
  3. Unpivot years separately
  4. Add dimensi='Laki-laki' and 'Perempuan'
  5. Combine both DataFrames

**Pendidikan_APM_provinsi.csv** ✓ MOST COMPLEX
- Row 0: Title "Angka Partisipasi Murni (APM)..."
- Row 1: **Sub-categories**: SD/sederajat (cols 1-5) | SMP/sederajat (cols 6-10) | SM/sederajat (cols 11-15)
- Row 2: Years 2020-2024 repeated for each sub-category
- **Structure**: 37 provinces × 3 education levels × 5 years = 555 rows (after unpivot)
- **Action**:
  1. Extract 3 separate blocks of 5 columns each
  2. For each block: unpivot years, add dimensi (APM-SD, APM-SMP, APM-SM)
  3. Combine all 3 DataFrames

#### **PATTERN 2: Simple Year Columns (standard)**
These files have a single indicator with years as columns.

**Ekonomi_upah_rata-rata.csv**
- Row 0: Title
- Row 1: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Kesehatan_unmet_layanan_kesehatan.csv**
- Row 0: Title
- Row 1: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Ketenagakerjaan_formal.csv**
- Row 0: Title
- Row 1: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Ketenagakerjaan_informal.csv**
- Row 0: Title
- Row 1: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Pendidikan_APK_PT_provinsi.csv**
- Row 0: Title
- Row 1: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Pendidikan_Rata-rata_lama_sekolah.csv**
- Row 0: Title
- Row 1: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Teknologi_memiliki_telepon_seluler.csv**
- Row 0: Title
- Row 1: "Perkotaan+Perdesaan" (category, but no sub-split needed - combined data)
- Row 2: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

**Teknologi_mengakses_internet.csv**
- Row 0: Title
- Row 1: "Perkotaan+Perdesaan" (category, but no sub-split needed - combined data)
- Row 2: Years 2020-2024 (5 columns)
- Years: 2020-2024
- **Action**: Simple unpivot

#### **PATTERN 3: Unusual Format**

**Ekonomi_persentase_penduduk_miskin.csv** ⚠️ SPECIAL
- Row 0: Title "Persentase Penduduk Miskin (P0)..."
- Row 1: "Jumlah" (category label)
- Row 2: Years **2021-2025** (NOTE: DIFFERENT YEAR RANGE! Starts 2021, ends 2025)
- Row 3: "Semester 1 (Maret)" (sub-metadata, should be skipped)
- **Action**:
  1. Read header specially to detect year range
  2. Skip row 3 (semester metadata)
  3. Unpivot with years 2021-2025

---

## Cleaning Implementation Strategy

### Step 1: Table-Specific Cleaners
Create individual cleaner functions in `etl/table_cleaners.py`:
- `clean_apm()` - Splits 3 education levels
- `clean_ahh()` - Splits 2 genders
- `clean_poverty()` - Handles special year range (2021-2025)
- `clean_simple()` - Generic handler for 8 standard tables

### Step 2: Parser Flow
1. **Extract**: Read raw CSV (header=None, skiprows=0)
2. **Detect Format**: Analyze row 1 to determine which cleaner to use
3. **Clean**: Apply table-specific logic to normalize
4. **Standardize**: Convert to long format (provinsi, tahun, indikator, dimensi, nilai)

### Step 3: Output Format (for all tables)
```
provinsi | tahun | kategori | indikator | dimensi | nilai | satuan | is_national_aggregate | sumber | data_kualitas_flag | catatan | created_at
---------|-------|----------|-----------|---------|-------|--------|----------------------|--------|-------------------|---------|----------
ACEH     | 2020  | Kesehatan| AHH       | Laki-laki | 70.72 | Tahun  | False                | BPS    | NULL              | NULL    | 2024-01-01 ...
```

### Step 4: Validation Rules (per table)
- **APM**: 37 provinces × 3 levels × 5 years = 555 rows expected
- **AHH**: 37 provinces × 2 genders × 5 years = 370 rows expected
- **Poverty**: 37 provinces × 1 × 5 years (2021-2025) = 185 rows expected
- **Simple tables**: 37-40 provinces × 1 × 5 years = 185-200 rows expected

---

## Implementation Files

**File**: `etl/table_cleaners.py`
- Contains table-specific cleaner functions
- Each function handles the unique structure of its CSV
- All return standardized long-format DataFrames

**Updates to**: `etl/extractor.py`
- Replace generic `extract_all_csvs()` with version that calls table-specific cleaners
- Each CSV file gets its own parsing strategy

**Updates to**: `etl/transformer.py`
- May simplify validation if table-specific cleaners handle structure normalization
- Focus on data quality checks rather than structural parsing

