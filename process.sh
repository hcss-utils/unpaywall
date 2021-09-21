#!/bin/bash

for pdf in data/raw_pdfs/*.pdf;
do
    python s2orc-doc2json/doc2json/grobid2json/process_pdf.py -i $pdf -o data/processed_pdfs
done