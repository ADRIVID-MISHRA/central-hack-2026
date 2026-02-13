@echo off
set OMP_NUM_THREADS=1
python verify_system.py
type verification_report.txt
