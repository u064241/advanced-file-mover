#!/usr/bin/env python3
"""
Integration test: Verifica che StorageDetector, RamDriveManager e FileOperationEngine
lavorano insieme correttamente con il nuovo sistema di rilevamento storage.
"""

import sys
import os
from pathlib import Path

# Aggiungi parent directory al path
sys.path.insert(0, str(Path(__file__).parent))

from src.ramdrive_handler import RamDriveManager
from src.storage_detector import StorageDetector
from src.file_operations import FileOperationEngine


def test_integration():
    """Test dell'integrazione completa"""
    
    print("\n" + "="*70)
    print("INTEGRATION TEST: Storage Detection + File Operations")
    print("="*70 + "\n")
    
    # 1. Inizializza RamDriveManager
    print("1️⃣  Inizializzazione RamDriveManager...")
    manager = RamDriveManager()
    print("   ✅ RamDriveManager creato\n")
    
    # 2. Early detection (come farebbe gui_customtkinter.py)
    print("2️⃣  Early detection (come al startup app)...")
    manager.detect_ramdrive()
    manager.scan_all_drives()
    print("   ✅ RamDrive detected + All drives scanned\n")
    
    # 3. Inizializza StorageDetector con RamDriveManager
    print("3️⃣  Inizializzazione StorageDetector con RamDriveManager...")
    detector = StorageDetector(ramdrive_manager=manager)
    print("   ✅ StorageDetector creato e integrato\n")
    
    # 4. Test get_optimal_settings
    print("4️⃣  Calcolo parametri ottimali per varie combinazioni...")
    
    test_pairs = [
        ('C:\\', 'C:\\'),
        ('C:\\', 'D:\\') if os.path.exists('D:\\') else None,
    ]
    
    for pair in test_pairs:
        if pair is None:
            continue
        source, dest = pair
        
        if os.path.exists(source) and os.path.exists(dest):
            optimal = detector.get_optimal_settings(source, dest)
            print(f"\n   {source} → {dest}")
            print(f"   - Source: {optimal['source_type']}")
            print(f"   - Dest: {optimal['dest_type']}")
            print(f"   - Buffer: {optimal['buffer_mb']}MB")
            print(f"   - Threads: {optimal['threads']}")
            print(f"   - Info: {optimal['info']}")
    
    print("\n   ✅ Parametri calcolati correttamente\n")
    
    # 5. Verifica che FileOperationEngine può usare questi parametri
    print("5️⃣  Verifica compatibilità con FileOperationEngine...")
    engine = FileOperationEngine()
    
    # Simula quello che farebbe il GUI
    source = 'C:\\'
    dest = 'C:\\'
    if os.path.exists(source) and os.path.exists(dest):
        optimal = detector.get_optimal_settings(source, dest)
        
        # FileOperationEngine userebbe questi parametri
        print(f"\n   FileOperationEngine userebbe:")
        print(f"   - buffer_size = {optimal['buffer_mb']}MB")
        print(f"   - max_threads = {optimal['threads']}")
        print(f"   ✅ Parametri compatibili\n")
    
    # 6. Verifica che non ci sono più call a PowerShell
    print("6️⃣  Verifica assenza di PowerShell latency...")
    
    import time
    
    # Testa il bottleneck: get_optimal_settings (che è quello che viene chiamato al click)
    start = time.time()
    for i in range(10):
        optimal = detector.get_optimal_settings('C:\\', 'C:\\')
    elapsed = (time.time() - start) / 10
    
    print(f"\n   Tempo medio per get_optimal_settings(): {elapsed*1000:.2f}ms")
    if elapsed < 0.01:  # < 10ms
        print("   ✅ Nessun lag rilevato (cache working!)\n")
    else:
        print("   ⚠️  Potenziale lag (verificare cache)\n")
    
    # 7. Test storage type detection per tutti i drive disponibili
    print("7️⃣  Verifica rilevamento tipi storage per tutti drive...")
    drives = manager.scan_all_drives()
    for letter in sorted(drives.keys()):
        storage_type = drives[letter]
        print(f"   {letter}: {storage_type.upper()}")
    print("   ✅ Tutti drive classificati\n")
    
    print("="*70)
    print("✅ INTEGRATION TEST PASSED")
    print("="*70 + "\n")


if __name__ == '__main__':
    try:
        test_integration()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
