#!/usr/bin/env python3
"""
Master Test Suite - Esegue TUTTI i test in sequenza
Validazione completa del sistema di classificazione storage con dati mock
"""

import subprocess
import sys
import time
from pathlib import Path


def run_test(test_file: str, description: str) -> bool:
    """Esegue un singolo test file"""
    
    print(f"\n{'─'*70}")
    print(f"🧪 {description}")
    print(f"📁 {test_file}")
    print(f"{'─'*70}\n")
    
    start = time.time()
    
    # Usa Python 3.12 da .venv312
    python_exe = Path("C:/SOURCECODE/.venv312/Scripts/python.exe")
    if not python_exe.exists():
        print(f"⚠️  Warning: {python_exe} non trovato, uso Python di sistema")
        python_exe = sys.executable
    
    try:
        result = subprocess.run(
            [str(python_exe), test_file],
            capture_output=False,
            text=True,
            cwd=Path(__file__).parent
        )
        
        elapsed = time.time() - start
        
        if result.returncode == 0:
            print(f"\n✅ PASSED ({elapsed:.1f}s)")
            return True
        else:
            print(f"\n❌ FAILED ({elapsed:.1f}s)")
            return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    """Master test suite"""
    
    print("\n" + "╔" + "="*68 + "╗")
    print("║  MASTER TEST SUITE - Advanced File Mover Pro (Python 3.12)      ║")
    print("║  Complete validation with mock data                            ║")
    print("╚" + "="*68 + "╝")
    
    # Verifica ambiente Python
    python_exe = Path("C:/SOURCECODE/.venv312/Scripts/python.exe")
    if python_exe.exists():
        print(f"\n🐍 Using: {python_exe}")
    else:
        print(f"\n🐍 Using: {sys.executable} (fallback)")
        print(f"⚠️  Nota: .venv312 non trovato in C:\\SOURCECODE, uso Python di sistema")
    
    tests = [
        ("test_storage_mock.py", "Basic Mock Data Classification (5 tests)"),
        ("test_advanced_mock.py", "Advanced Scenarios & Edge Cases (4 scenarios)"),
        ("test_integration.py", "Integration Test (StorageDetector + RamDriveManager)"),
        ("test_ramdrive_params.py", "RamDrive Parameter Verification"),
    ]
    
    print("\n" + "="*70)
    print("TEST EXECUTION PLAN")
    print("="*70)
    print(f"\nTotal tests: {len(tests)}")
    for i, (file, desc) in enumerate(tests, 1):
        print(f"{i}. {desc}")
    
    print("\n" + "="*70)
    print("STARTING TEST EXECUTION")
    print("="*70)
    
    results = []
    total_time = 0
    
    for test_file, description in tests:
        start = time.time()
        passed = run_test(test_file, description)
        elapsed = time.time() - start
        total_time += elapsed
        results.append((description, passed, elapsed))
    
    # Summary
    print("\n\n" + "="*70)
    print("TEST EXECUTION SUMMARY")
    print("="*70 + "\n")
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    
    for desc, passed, elapsed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} ({elapsed:.1f}s) - {desc}")
    
    print("\n" + "="*70)
    print(f"Results: {passed_count}/{total_count} tests passed")
    print(f"Total execution time: {total_time:.1f}s")
    print("="*70)
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED - SYSTEM IS PRODUCTION READY! 🎉\n")
        print("Key Achievements:")
        print("  ✅ Storage type classification verified")
        print("  ✅ Device path parsing validated")
        print("  ✅ Parameter optimization confirmed")
        print("  ✅ RamDrive priority working correctly")
        print("  ✅ Edge cases handled properly")
        print("  ✅ Multiple scenarios tested")
        print("  ✅ No hardware dependencies")
        print("\n")
        return True
    else:
        print(f"\n❌ {total_count - passed_count} tests failed - review logs above\n")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
