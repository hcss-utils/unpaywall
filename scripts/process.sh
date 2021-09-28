#!/bin/bash

find ../data/raw_pdfs/ -empty -delete

for pdf in ../data/raw_pdfs/*.pdf;
do
    python ../s2orc-doc2json/doc2json/grobid2json/process_pdf.py -i $pdf -t ../data/tmp -o ../data/processed_pdfs
done