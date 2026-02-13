@echo off
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set OPENBLAS_NUM_THREADS=1
python test_messy_potato_file.py
type messy_results.txt
