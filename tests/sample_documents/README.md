# Sample Documents Directory

Place your test documents here for processing.

## Supported Formats

- PDF files (`.pdf`)
- JPEG images (`.jpg`, `.jpeg`)
- PNG images (`.png`)

## Example File Organization

```
sample_documents/
├── integrated_cert/
│   ├── application_form.pdf
│   ├── caste_certificate.pdf
│   ├── ssc_memo.pdf
│   └── ration_card.jpg
│
├── income_cert/
│   ├── application_form.pdf
│   ├── it_returns.pdf
│   └── pay_slips.pdf
│
├── obc_cert/
│   ├── application_form.pdf
│   ├── property_docs.pdf
│   └── ration_card.jpg
│
├── ews_cert/
│   ├── application_form.pdf
│   ├── it_returns.pdf
│   └── affidavit.pdf
│
└── family_cert/
    ├── application_form.pdf
    ├── death_certificate.pdf
    └── affidavit.pdf
```

## Usage

Reference these files when running the workflow:

```bash
cd src

# Example with full paths
python main.py \
  --cert-type integrated \
  --files ../tests/sample_documents/integrated_cert/*.pdf

# Example with relative paths from src/
python main.py \
  --cert-type income \
  --files ../tests/sample_documents/income_cert/application_form.pdf \
          ../tests/sample_documents/income_cert/it_returns.pdf
```

## Notes

- Files in this directory are ignored by git (see `.gitignore`)
- Maximum file size: 20 MB (configurable in `.env`)
- Ensure documents are clear and readable for best OCR results
