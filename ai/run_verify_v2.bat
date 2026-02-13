@echo off
set OMP_NUM_THREADS=1
python -u verify_system.py > check_log.txt 2>&1
echo Done.
