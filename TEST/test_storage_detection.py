#!/usr/bin/env python3
"""
Test script per verifica del nuovo sistema di rilevamento storage unificato
Testa:
1. QueryDosDevice scan di tutti i drive
2. Classificazione automatica (HDD/SSD/NVMe/USB/RamDrive)
3. Integrazione con StorageDetector
"""

import sys
import os
import time
from pathlib import Path

# Aggiungi parent directory al path
sys.path.insert(0, str(Path(__file__).parent))

from src.ramdrive_handler import RamDriveManager
from src.storage_detector import StorageDetector


def test_scan_all_drives():
    """Testa il rilevamento di tutti i drive via QueryDosDevice"""
    print("\n" + "="*70)
    print("TEST 1: Scansione di tutti i drive con QueryDosDevice")
    print("="*70 + "\n")
    
    manager = RamDriveManager()
    
    # Misura tempo di scansione
    start = time.time()
    drives = manager.scan_all_drives()
    elapsed = time.time() - start
    
    print(f"⏱️  Tempo scansione: {elapsed*1000:.1f}ms")
    print(f"📊 Drive trovati: {len(drives)}")
    print(f"🔍 Classificazione drive:\n")
    
    for letter, storage_type in sorted(drives.items()):
        print(f"  {letter}: → {storage_type.upper()}")
    
    return drives


def test_ramdrive_detection():
    """Testa il rilevamento del RamDrive"""
    print("\n" + "="*70)
    print("TEST 2: Rilevamento RamDrive")
    print("="*70 + "\n")
    
    manager = RamDriveManager()
    
    start = time.time()
    ramdrive_letter = manager.get_ramdrive_letter()
    elapsed = time.time() - start
    
    print(f"⏱️  Tempo rilevamento: {elapsed*1000:.1f}ms")
    
    if ramdrive_letter:
        info = manager.get_ramdrive_info()
        print(f"✅ RamDrive trovato: {ramdrive_letter}:")
        print(f"   - Totale: {info['total_formatted']}")
        print(f"   - Libero: {info['free_formatted']}")
        print(f"   - Software: {', '.join(info['software']) if info['software'] else 'Sconosciuto'}")
        return info
    else:
        print("❌ Nessun RamDrive rilevato")
        return None


def test_storage_detector_integration():
    """Testa l'integrazione tra RamDriveManager e StorageDetector"""
    print("\n" + "="*70)
    print("TEST 3: Integrazione StorageDetector con RamDriveManager")
    print("="*70 + "\n")
    
    manager = RamDriveManager()
    detector = StorageDetector(ramdrive_manager=manager)
    
    # Test su drive comuni
    test_paths = ['C:', 'D:', 'E:', 'Z:']
    
    print("🔍 Rilevamento tipo storage per percorsi:\n")
    
    for path in test_paths:
        if os.path.exists(f"{path}\\"):
            start = time.time()
            info = detector.get_storage_type(path)
            elapsed = time.time() - start
            
            print(f"  {path}:\\ → {info['name']:<15} ({info['speed']:<20}) | ⏱️  {elapsed*1000:.1f}ms")


def test_optimal_settings():
    """Testa il calcolo dei parametri ottimali"""
    print("\n" + "="*70)
    print("TEST 4: Calcolo parametri ottimali (Buffer + Threads)")
    print("="*70 + "\n")
    
    manager = RamDriveManager()
    detector = StorageDetector(ramdrive_manager=manager)
    
    # Test su combinazioni di drive
    test_cases = [
        ('C:\\Documents', 'D:\\Backup'),  # Presumibilmente HDD → HDD
        ('C:\\', 'E:\\'),                  # Dipende da hardware
        ('C:\\', 'C:\\'),                  # Stesso drive
    ]
    
    print("⚙️  Parametri ottimali per varie combinazioni:\n")
    
    for source, dest in test_cases:
        if os.path.exists(source) and os.path.exists(dest):
            optimal = detector.get_optimal_settings(source, dest)
            print(f"  {source} → {dest}")
            print(f"    Sorgente: {optimal['source_type']}")
            print(f"    Destinazione: {optimal['dest_type']}")
            print(f"    Buffer: {optimal['buffer_mb']}MB | Thread: {optimal['threads']}")
            print(f"    Info: {optimal['info']}\n")


def main():
    """Esegue tutti i test"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║  ADVANCED FILE MOVER - Storage Detection System Test Suite        ║")
    print("╚" + "="*68 + "╝")
    
    try:
        # Test 1: Scansione drive
        drives = test_scan_all_drives()
        
        # Test 2: RamDrive
        ram_info = test_ramdrive_detection()
        
        # Test 3: Integrazione StorageDetector
        test_storage_detector_integration()
        
        # Test 4: Parametri ottimali
        test_optimal_settings()
        
        print("\n" + "="*70)
        print("✅ TUTTI I TEST COMPLETATI CON SUCCESSO")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRORE DURANTE I TEST: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
