#!/usr/bin/env python3
"""
Test specifico per RamDrive: verifica che i parametri ottimali siano corretti
quando si copia verso/da RamDrive
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ramdrive_handler import RamDriveManager
from src.storage_detector import StorageDetector


def test_ramdrive_optimal_settings():
    """Test specifico per RamDrive parameters"""
    
    print("\n" + "="*70)
    print("TEST: RamDrive Optimal Parameters")
    print("="*70 + "\n")
    
    manager = RamDriveManager()
    manager.detect_ramdrive()
    manager.scan_all_drives()
    
    ram_info = manager.get_ramdrive_info()
    
    if not ram_info['available']:
        print("❌ RamDrive non disponibile - test skipped\n")
        return False
    
    print(f"✅ RamDrive found: {ram_info['letter']}:")
    print(f"   - Total: {ram_info['total_formatted']}")
    print(f"   - Free: {ram_info['free_formatted']}\n")
    
    # Crea detector
    detector = StorageDetector(ramdrive_manager=manager)
    
    # Verifica che il tipo di storage per RamDrive sia corretto
    ramdrive_path = f"{ram_info['letter']}:\\"
    ram_type = manager.get_storage_type(ramdrive_path)
    
    print(f"Storage type for {ramdrive_path}: {ram_type}")
    assert ram_type == "ram", f"❌ Expected 'ram', got '{ram_type}'"
    print("✅ RamDrive correctly identified as 'ram'\n")
    
    # Test 1: HDD → RamDrive
    print("Test 1: HDD → RamDrive")
    if os.path.exists("C:\\") and os.path.exists(ramdrive_path):
        optimal = detector.get_optimal_settings("C:\\", ramdrive_path)
        print(f"  Source: {optimal['source_type']}")
        print(f"  Dest: {optimal['dest_type']}")
        print(f"  Buffer: {optimal['buffer_mb']}MB (expected: 8MB for RamDrive)")
        print(f"  Threads: {optimal['threads']} (expected: 16 for RamDrive)")
        print(f"  Info: {optimal['info']}")
        
        # Verifica che buffer/threads siano ottimizzati per RamDrive
        assert optimal['buffer_mb'] == 8, f"❌ Expected 8MB buffer for RamDrive, got {optimal['buffer_mb']}"
        assert optimal['threads'] == 16, f"❌ Expected 16 threads for RamDrive, got {optimal['threads']}"
        print("  ✅ PASSED\n")
    
    # Test 2: RamDrive → HDD
    print("Test 2: RamDrive → HDD")
    if os.path.exists("C:\\") and os.path.exists(ramdrive_path):
        optimal = detector.get_optimal_settings(ramdrive_path, "C:\\")
        print(f"  Source: {optimal['source_type']}")
        print(f"  Dest: {optimal['dest_type']}")
        print(f"  Buffer: {optimal['buffer_mb']}MB (expected: 8MB for RamDrive)")
        print(f"  Threads: {optimal['threads']} (expected: 16 for RamDrive)")
        print(f"  Info: {optimal['info']}")
        
        # RamDrive ha priorità (priority 10 vs HDD priority 1)
        assert optimal['buffer_mb'] == 8, f"❌ Expected 8MB buffer for RamDrive, got {optimal['buffer_mb']}"
        assert optimal['threads'] == 16, f"❌ Expected 16 threads for RamDrive, got {optimal['threads']}"
        print("  ✅ PASSED\n")
    
    # Test 3: RamDrive → RamDrive
    print("Test 3: RamDrive → RamDrive")
    if os.path.exists(ramdrive_path):
        optimal = detector.get_optimal_settings(ramdrive_path, ramdrive_path)
        print(f"  Source: {optimal['source_type']}")
        print(f"  Dest: {optimal['dest_type']}")
        print(f"  Buffer: {optimal['buffer_mb']}MB (expected: 8MB)")
        print(f"  Threads: {optimal['threads']} (expected: 16)")
        print(f"  Info: {optimal['info']}")
        
        assert optimal['buffer_mb'] == 8, f"❌ Expected 8MB buffer, got {optimal['buffer_mb']}"
        assert optimal['threads'] == 16, f"❌ Expected 16 threads, got {optimal['threads']}"
        print("  ✅ PASSED\n")
    
    print("="*70)
    print("✅ ALL RAMDRIVE TESTS PASSED")
    print("="*70 + "\n")
    
    return True


if __name__ == '__main__':
    try:
        test_ramdrive_optimal_settings()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
