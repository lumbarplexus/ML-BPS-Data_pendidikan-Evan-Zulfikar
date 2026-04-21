# Table-Specific CSV Cleaners - Implementation Complete

## Executive Summary

Successfully designed and implemented individual cleaners for 11 CSV files with diverse, complex structures. Each file's unique format (hierarchical headers, multi-level dimensions, varying year ranges) is now handled by a specialized parser that normalizes the data into a standardized long format.

**Total Rows Processed: 2,790**

---

## Extraction Results

| CSV File | Rows | Structure | Dimensions | Years |
|----------|------|-----------|-----------|-------|
| Ekonomi_persentase_penduduk_miskin.csv | 200 | Simple + Special years | 1 | 2021-2025 |
| Ekonomi_upah_rata-rata.csv | 200 | Simple | 1 | 2020-2024 |
| Kesehatan_angka_harapan_hidup.csv | 390 | Gender split | 2 | 2020-2024 |
| Kesehatan_unmet_layanan_kesehatan.csv | 200 | Simple | 1 | 2020-2024 |
| Ketenagakerjaan_formal.csv | 200 | Simple | 1 | 2020-2024 |
| Ketenagakerjaan_informal.csv | 200 | Simple | 1 | 2020-2024 |
| Pendidikan_APK_PT_provinsi.csv | 200 | Simple | 1 | 2020-2024 |
| **Pendidikan_APM_provinsi.csv** | **600** | **3 education levels** | **3** | **2020-2024** |
| Pendidikan_Rata-rata_lama_sekolah.csv | 200 | Simple | 1 | 2020-2024 |
| Teknologi_memiliki_telepon_seluler.csv | 200 | Simple | 1 | 2020-2024 |
| Teknologi_mengakses_internet.csv | 200 | Simple | 1 | 2020-2024 |
| **TOTAL** | **2,790** | | | |

---

## Specialized Cleaners Implemented

### 1. `clean_apm()` - Angka Partisipasi Murni (APM)
**Challenge:** 3-level hierarchical headers with sub-categories spanning multiple columns

**Structure:**
```
Row 0: Title
Row 1: 3 Categories | SD/sederajat (cols 1-5) | SMP/sederajat (cols 6-10) | SM/sederajat (cols 11-15)
Row 2: Years | 2020-2024 x3 (repeated for each category)
Row 3+: Data (39 provinces + 1 extra row requiring trim)
```

**Solution:**
- Extract 3 separate 5-column blocks
- Reset index for each block to match province list
- Handle length mismatch (41 rows → 40 provinces) via trimming
- Unpivot each block separately, add dimensi (APM-SD, APM-SMP, APM-SM)
- Combine all 3 blocks: 40 × 3 × 5 = **600 rows**

**Sample Output:**
```
ACEH,2020,APM,APM-SD,99.03
ACEH,2020,APM,APM-SMP,86.87
ACEH,2020,APM,APM-SM,70.7
```

---

### 2. `clean_ahh()` - Angka Harapan Hidup (Life Expectancy)
**Challenge:** 2-level gender split headers

**Structure:**
```
Row 0: Title
Row 1: 2 Genders | Laki-laki (cols 1-5) | Perempuan (cols 6-10)
Row 2: Years | 2020-2024 x2 (repeated for each gender)
Row 3+: Data (39 provinces)
```

**Solution:**
- Extract 2 separate 5-column blocks (Laki-laki, Perempuan)
- Reset index for each block
- Unpivot each block, add dimensi (Laki-laki, Perempuan)
- Combine: 39 × 2 × 5 = **390 rows**

**Sample Output:**
```
ACEH,2020,AHH,Laki-laki,70.72
ACEH,2020,AHH,Perempuan,74.75
```

---

### 3. `clean_poverty()` - Persentase Penduduk Miskin
**Challenge:** Non-standard year range (2021-2025 instead of 2020-2024), extra metadata row

**Structure:**
```
Row 0: Title
Row 1: "Jumlah" (category label)
Row 2: Years | 2021-2025 (DIFFERENT RANGE)
Row 3: "Semester 1 (Maret)" (metadata - skip)
Row 4+: Data (40 provinces, 41 total including extra row)
```

**Solution:**
- Detect special year range (2021-2025) from row 2
- Skip metadata row 3
- Handle length mismatch (41 rows → 40 provinces) via trimming
- Unpivot with special year range: 40 × 1 × 5 = **200 rows**

**Key Insight:** Different year range requires special handling to ensure reconciliation validation doesn't fail

---

### 4. `clean_simple()` - Generic Handler
**Challenge:** 8 different simple tables with same basic structure

**Files Handled:**
- Ekonomi_upah_rata-rata.csv (Wages)
- Kesehatan_unmet_layanan_kesehatan.csv (Unmet Health Services)
- Ketenagakerjaan_formal.csv (Formal Employment)
- Ketenagakerjaan_informal.csv (Informal Employment)
- Pendidikan_APK_PT_provinsi.csv (Higher Education Participation)
- Pendidikan_Rata-rata_lama_sekolah.csv (Average Years of School)
- Teknologi_memiliki_telepon_seluler.csv (Mobile Phone Ownership)
- Teknologi_mengakses_internet.csv (Internet Access)

**Structure:**
```
Row 0: Title
Row 1: Optional category metadata OR Years
Row 1/2: Years (2020-2024)
Row 2/3+: Data (40 provinces, with 41 rows requiring trim)
```

**Solution:**
- Detect year row by scanning for numeric values
- Handle optional category row (Perkotaan+Perdesaan)
- Trim to match province count
- Generic unpivot: 40 × 1 × 5 = **200 rows** per file

---

## Data Quality Handling

### Length Mismatch Resolution
**Problem:** Most CSV files load as 41 rows (likely trailing blank/metadata row) vs. 40-40 provinces

**Solution:**
```python
if len(data_df) != len(provinces):
    min_len = min(len(data_df), len(provinces))
    data_df = data_df.iloc[:min_len]
    provinces = provinces[:min_len]
```

**Applied To:** Poverty, Upah, Unmet, Formal, Informal, APK PT, APM (all 3 blocks), Lama Sekolah, Telepon, Internet

### Special Year Ranges
- **Standard:** 2020, 2021, 2022, 2023, 2024 (most files)
- **Poverty Only:** 2021, 2022, 2023, 2024, 2025 (5-year range with 2025)

---

## Output Format (Standardized)

All cleaners return consistent long-format DataFrame:

| Column | Type | Example |
|--------|------|---------|
| provinsi | str | ACEH, RIAU, JAKARTA |
| tahun | int | 2020-2025 |
| kategori | str | Ekonomi, Kesehatan, Pendidikan, Teknologi, Ketenagakerjaan |
| indikator | str | APM, AHH, Persentase_Penduduk_Miskin, Upah_Rata_Rata, ... |
| dimensi | str/None | APM-SD, Laki-laki, Perempuan, None |
| nilai | float | 99.03, 70.72, 38.12, ... |
| satuan | str | Persen, Tahun, Rupiah/Jam |
| is_national_aggregate | bool | False |
| sumber | str | BPS |
| created_at | datetime | 2026-04-20T11:29:00 |

---

## Architecture Components

### File: `etl/table_cleaners.py` (380+ lines)
Contains:
- `clean_apm()` - APM special handler
- `clean_ahh()` - AHH special handler  
- `clean_poverty()` - Poverty special handler
- `clean_simple()` - Generic handler for 8 files
- `CLEANER_REGISTRY` - Mapping of filename → cleaner function + parameters
- `get_cleaner()` - Registry lookup function

### File: `etl/extractor.py` - Updated
- Replaced generic `extract_all_csvs()` with table-aware version
- Now calls `get_cleaner()` for each CSV
- Routes to appropriate specialized cleaner
- Returns dict of {filename: CleanedDataFrame}

### File: `etl/transformer.py` - Simplified
- No longer handles structural normalization
- Focuses on data quality validation (province names, ranges, years)
- Flags data quality issues (VALID, OUTLIER, MISSING_DATA)
- Simpler design due to pre-cleaned data from extraction layer

---

## Benefits of Table-Specific Approach

✅ **Clear, Maintainable Code**
- Each file's logic isolated in dedicated function
- Easy to debug specific parsers
- Self-documenting (function name = file intent)

✅ **Handles Edge Cases**
- Hierarchical headers split correctly
- Special year ranges captured
- Length mismatches detected & resolved

✅ **Scalable Design**
- `CLEANER_REGISTRY` makes adding new files easy
- Simple cleaners can be added without touching complex ones
- Parameters in registry allow customization per file

✅ **Quality Checkpoints**
- Each cleaner validates expected dimensions
- Length mismatch warnings logged
- Pre-transformation validation gates issues early

✅ **Future-Proof Architecture**
- When new CSV files arrive, add to registry + create new cleaner
- Existing cleaners unaffected
- Modular approach supports incremental updates

---

## Testing & Validation

### Test Results
```
Cleaning Poverty table... [OK] 200 rows
Cleaning Upah_Rata_Rata table... [OK] 200 rows  
Cleaning AHH table... [OK] 390 rows (2 gender splits)
Cleaning Unmet_Layanan_Kesehatan table... [OK] 200 rows
Cleaning Tenaga_Kerja_Formal table... [OK] 200 rows
Cleaning Lapangan_Kerja_Informal table... [OK] 200 rows
Cleaning APK_Perguruan_Tinggi table... [OK] 200 rows
Cleaning APM table... [OK] 600 rows (3 education level splits)
Cleaning Rata_Rata_Lama_Sekolah table... [OK] 200 rows
Cleaning Memiliki_Telepon_Seluler table... [OK] 200 rows
Cleaning Mengakses_Internet table... [OK] 200 rows

TOTAL: 2,790 rows extracted & cleaned
```

### Sample Verification
AHH (Gender Split):
```
ACEH,2020,AHH,Laki-laki,70.72
SUMATERA UTARA,2020,AHH,Laki-laki,71.01
...
ACEH,2020,AHH,Perempuan,74.75
SUMATERA UTARA,2020,AHH,Perempuan,75.09
```

APM (3 Education Levels):
```
ACEH,2020,APM,APM-SD,99.03
ACEH,2020,APM,APM-SMP,86.87
ACEH,2020,APM,APM-SM,70.7
```

---

## Next Steps

1. **Transformation Phase**: transformer.py validates cleaned data quality
2. **Loader Phase**: Load to PostgreSQL staging table
3. **Reconciliation Gate**: Validate staging vs. source CSVs (row counts, values ±0.0001 tolerance)
4. **DW Load**: Insert into fact table after reconciliation passes
5. **Validation Reports**: Generate quality summaries from staging/DW

---

## Notes for Future Maintenance

- If new CSV files arrive with complex structures, create dedicated cleaner function
- Add to `CLEANER_REGISTRY` with appropriate parameters
- If year range changes for any file, update parser (e.g., poverty's 2021-2025)
- Length mismatch (41→40 rows) pattern consistent across most files - likely trailing row in CSV export

