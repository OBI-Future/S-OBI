# S-OBI data archive

The S-OBI dataset is distributed as the single GitHub Release asset `sentence-OBI.zip`. The repository intentionally contains no extracted dataset, Excel file, original data table, task file, gold annotation, or benchmark image.

## Download and verify

From the repository root, use the downloader so the archive is verified and extracted with the same safe path handling as the toolkit:

```bash
python scripts/download_data.py
```

For an existing local archive, run `python scripts/download_data.py --archive /path/to/sentence-OBI.zip`. The checksum file records the SHA-256 digest and filename for the release asset. The expected extracted root is `data/sentence-OBI/`.

## Scope

The supplied archive contains 95 base inscriptions, 695 benchmark items, 95 original JPG images, and 505 PNG benchmark images. It includes the task records and gold annotations required by the provided scorer. See [`../docs/dataset.md`](../docs/dataset.md) for the schema and the known metadata caveat.

## Data terms

The supplied archive does not include an independent data license statement. The MIT license in the repository applies to repository code and does not automatically apply to the archive, images, annotations, or other data. The data license is therefore currently unspecified.

Before redistributing the archive, republishing individual images, or creating a derivative dataset, confirm that the proposed use is permitted by the relevant rights holders and the release terms. This note records the current materials faithfully; it does not grant additional rights.

## Integrity and known packaging details

- The v1.0.0 archive is 37,027,607 bytes.
- macOS `__MACOSX/` entries are packaging metadata and may be ignored.
- `transforms.jsonl` contains 570 records, including 65 records whose referenced images are absent.
- The 695 formal benchmark task records have valid image references according to the release audit.
