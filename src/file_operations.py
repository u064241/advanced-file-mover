"""
Engine core per operazioni file ottimizzate
"""
import os
import shutil
import threading
import time
import tempfile
from pathlib import Path
from typing import Callable, Optional
from enum import Enum


class OperationType(Enum):
    """Tipo di operazione"""
    COPY = "copy"
    MOVE = "move"


class FileOperationEngine:
    """Engine ottimizzato per copia/spostamento file"""
    
    # Dimensioni buffer (tutte in bytes)
    BUFFER_SIZE = 10 * 1024 * 1024  # 10 MB default
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100 MB
    LARGE_FILE_BUFFER = 50 * 1024 * 1024  # 50 MB per file grandi
    
    def __init__(self,
                 buffer_size: int = BUFFER_SIZE,
                 use_ramdrive: bool = True,
                 ramdrive_letter: Optional[str] = None,
                 num_threads: int = 4):
        """
        Inizializza engine
        
        Args:
            buffer_size: Dimensione buffer in bytes
            use_ramdrive: Usare RamDrive se disponibile
            ramdrive_letter: Lettera RamDrive (A-Z)
            num_threads: Numero thread per operazioni parallele
        """
        self.buffer_size = buffer_size
        self.use_ramdrive = use_ramdrive
        self.ramdrive_letter = ramdrive_letter
        self.num_threads = num_threads
        
        # Progress tracking
        self.current_file = ""
        self.total_size = 0
        self.processed_size = 0
        self.current_speed = 0  # bytes/sec
        self.is_cancelled = False

        # File counting (per mostrare 1/n)
        self.file_index = 0
        self.file_count = 0
        
        # Callback
        self.on_progress: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Imposta callback per progress"""
        self.on_progress = callback
    
    def set_error_callback(self, callback: Callable):
        """Imposta callback per errori"""
        self.on_error = callback
    
    def set_complete_callback(self, callback: Callable):
        """Imposta callback per completamento"""
        self.on_complete = callback
    
    def cancel(self):
        """Cancella operazione in corso"""
        self.is_cancelled = True
    
    def reset_progress(self):
        """Resetta lo stato del progresso per una nuova operazione"""
        self.current_file = ""
        self.total_size = 0
        self.processed_size = 0
        self.current_speed = 0
        self.is_cancelled = False

        self.file_index = 0
        self.file_count = 0
    
    def copy(self, source: str, destination: str) -> bool:
        """
        Copia file/cartella da source a destination
        
        Returns:
            True se successo, False se errore
        """
        return self._perform_operation(source, destination, OperationType.COPY)
    
    def move(self, source: str, destination: str) -> bool:
        """
        Sposta file/cartella da source a destination
        
        Returns:
            True se successo, False se errore
        """
        return self._perform_operation(source, destination, OperationType.MOVE)
    
    def _perform_operation(self, source: str, destination: str, 
                          operation: OperationType) -> bool:
        """Esegue operazione (copy/move)"""
        ramdrive_temp_path = None
        try:
            if not os.path.exists(source):
                self._log_error(f"Sorgente non trovata: {source}")
                return False

            self.processed_size = 0
            self.is_cancelled = False

            files_to_process = None

            # Calcola size totale (ottimizzato per directory: un solo passaggio)
            if os.path.isfile(source):
                self.total_size = self._get_total_size(source)
                self.file_count = 1
                self.file_index = 0
            else:
                plan = self._prepare_directory_plan(source, destination)
                if plan is None:
                    return False
                files_to_process, total_size = plan
                self.total_size = total_size
                self.file_count = len(files_to_process)
                self.file_index = 0
            
            # Decidi se usare flusso a 2 fasi (con RamDrive) o diretto
            use_ramdrive_buffer = False
            ramdrive_temp_path = None
            
            # Determina se la destinazione è il ramdrive stesso
            dest_drive = os.path.splitdrive(destination)[0].upper()
            destination_is_ramdrive = self.ramdrive_letter and dest_drive == f"{self.ramdrive_letter.upper()}:"
            
            if (self.use_ramdrive and self.ramdrive_letter and 
                operation == OperationType.COPY and
                not destination_is_ramdrive):  # NON usare flusso 2-fasi se target è ramdrive
                # Verifica se RamDrive ha spazio sufficiente
                try:
                    ram_drive = f"{self.ramdrive_letter.upper()}:\\"
                    if os.path.exists(ram_drive):
                        ram_usage = shutil.disk_usage(ram_drive)
                        if ram_usage.free >= self.total_size:
                            # RamDrive ha spazio: usa flusso a 2 fasi SOLO se destinazione non è ramdrive
                            use_ramdrive_buffer = True
                            ramdrive_temp_path = os.path.join(ram_drive, f".transfer_{int(time.time())}")
                            self._log_info(f"✅ RamDrive buffer intermedio disponibile: {self.ramdrive_letter}:")
                        else:
                            # RamDrive insufficiente: fallback a diretto
                            ram_free_gb = ram_usage.free / (1024**3)
                            required_gb = self.total_size / (1024**3)
                            self._log_info(f"⚠️ RamDrive insufficiente ({ram_free_gb:.2f}GB liberi, {required_gb:.2f}GB richiesti): trasferimento diretto")
                except:
                    pass
            elif destination_is_ramdrive:
                # Destinazione è ramdrive: usa streaming diretto con buffer grande
                self._log_info(f"✅ Trasferimento diretto a RamDrive con buffer ottimizzato")
            
            # CONTROLLO SPAZIO DESTINAZIONE
            dest_drive = os.path.splitdrive(destination)[0]
            if dest_drive:
                try:
                    usage = shutil.disk_usage(dest_drive)
                    free_space = usage.free
                    
                    if operation == OperationType.COPY:
                        required = self.total_size
                    else:  # MOVE
                        required = 0
                    
                    if free_space < required:
                        free_gb = free_space / (1024**3)
                        required_gb = required / (1024**3)
                        self._log_error(
                            f"Spazio insufficiente in destinazione! Disponibile: {free_gb:.2f}GB, "
                            f"Richiesto: {required_gb:.2f}GB"
                        )
                        return False
                except:
                    pass
            
            # Esegui operazione
            if os.path.isfile(source):
                # Singolo file
                self.file_index = 1
                return self._handle_file_with_ramdrive(source, destination, operation, 
                                                       use_ramdrive_buffer, ramdrive_temp_path)
            else:
                # Directory
                return self._handle_directory_with_ramdrive(
                    source,
                    destination,
                    operation,
                    use_ramdrive_buffer,
                    ramdrive_temp_path,
                    files_to_process=files_to_process,
                )
        
        except Exception as e:
            self._log_error(f"Errore operazione: {e}")
            return False
        finally:
            # Pulizia cartella temporanea ramdrive
            if ramdrive_temp_path and os.path.exists(ramdrive_temp_path):
                try:
                    import shutil
                    shutil.rmtree(ramdrive_temp_path, ignore_errors=True)
                    self._log_info(f"✅ Cartella temporanea rimossa: {ramdrive_temp_path}")
                except Exception as e:
                    self._log_error(f"⚠️ Errore rimozione cartella temporanea: {e}")
    
    def _get_total_size(self, path: str) -> int:
        """Calcola size totale di file/directory"""
        if os.path.isfile(path):
            return os.path.getsize(path)
        
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total += os.path.getsize(filepath)
                    except:
                        pass
        except:
            pass
        
        return total

    def _prepare_directory_plan(self, source: str, destination: str):
        """Prepara lista file e total_size con un solo os.walk."""
        try:
            self.current_file = "Scansione...(0 file)"
            # Durante la scansione teniamo processed_size a 0, ma aggiorniamo total_size
            # progressivamente per dare un minimo di feedback alla UI.
            self.processed_size = 0
            self.total_size = 0

            last_report_ts = time.time()
            file_count = 0
            files_to_process = []
            total_size = 0

            def _on_walk_error(err):
                try:
                    self._log_error(f"Errore accesso directory durante scansione: {getattr(err, 'filename', '')} ({err})")
                except Exception:
                    pass

            for root, dirs, files in os.walk(source, onerror=_on_walk_error):
                if self.is_cancelled:
                    return None

                rel_path = os.path.relpath(root, source)
                dst_root = destination if rel_path == '.' else os.path.join(destination, rel_path)

                for filename in files:
                    if self.is_cancelled:
                        return None

                    src_file = os.path.join(root, filename)
                    dst_file = os.path.join(dst_root, filename)
                    files_to_process.append((src_file, dst_file))
                    file_count += 1
                    try:
                        total_size += os.path.getsize(src_file)
                    except Exception:
                        pass

                    # Update UI (throttled)
                    now = time.time()
                    if (now - last_report_ts) >= 0.2:
                        self.total_size = total_size
                        self.current_file = f"Scansione...({int(file_count)} file)"
                        self._report_progress()
                        last_report_ts = now

            # Report finale scansione
            self.total_size = total_size
            self.current_file = f"Scansione...({int(file_count)} file)"
            self._report_progress()

            return files_to_process, total_size
        except Exception as e:
            self._log_error(f"Errore preparazione directory: {e}")
            return None

    def _format_exc(self, e: Exception) -> str:
        try:
            winerror = getattr(e, 'winerror', None)
            if winerror is not None:
                return f"[WinError {winerror}] {e}"
        except Exception:
            pass
        try:
            return str(e)
        except Exception:
            return repr(e)
    
    def _handle_file(self, source: str, destination: str,
                    operation: OperationType) -> bool:
        """Gestisce copia/spostamento singolo file"""
        try:
            # Se destination è una directory, aggiungi il nome del file
            if os.path.isdir(destination):
                destination = os.path.join(destination, os.path.basename(source))
            
            # Creare directory destinazione se necessaria
            dest_dir = os.path.dirname(destination)
            if dest_dir and not os.path.exists(dest_dir):
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                except Exception as e:
                    self._log_error(f"Errore creazione directory destinazione: {dest_dir} ({self._format_exc(e)})")
                    return False
            
            self.current_file = os.path.basename(source)
            if self.file_count <= 0:
                self.file_count = 1
            if self.file_index <= 0:
                self.file_index = 1
            self._report_progress()
            
            # Ottimizza buffer in base a sorgente/destinazione
            file_size = os.path.getsize(source)
            
            # Se target è ramdrive, usa buffer minimo (è già RAM)
            dest_drive = os.path.splitdrive(destination)[0].upper()
            is_ramdrive = self.ramdrive_letter and dest_drive == f"{self.ramdrive_letter.upper()}:"
            
            if is_ramdrive:
                # RamDrive: buffer ottimizzato (trasferimento RAM->RAM)
                use_buffer = 8 * 1024 * 1024  # 8 MB
            elif file_size > self.LARGE_FILE_THRESHOLD:
                # File grandi: buffer grande
                use_buffer = self.LARGE_FILE_BUFFER
            else:
                # File normali: buffer standard
                use_buffer = self.buffer_size
            
            # Copia effettiva con buffering
            try:
                src_fh = open(source, 'rb')
            except Exception as e:
                self._log_error(f"Errore apertura sorgente: {source} ({self._format_exc(e)})")
                return False

            try:
                dst_fh = open(destination, 'wb')
            except Exception as e:
                try:
                    src_fh.close()
                except Exception:
                    pass
                self._log_error(f"Errore apertura destinazione: {destination} ({self._format_exc(e)})")
                return False

            with src_fh as src, dst_fh as dst:
                while True:
                    if self.is_cancelled:
                        os.remove(destination)
                        return False
                    
                    buffer = src.read(use_buffer)
                    if not buffer:
                        break
                    
                    dst.write(buffer)
                    self.processed_size += len(buffer)
                    self._report_progress()
            
            # Se move, cancellare sorgente
            if operation == OperationType.MOVE:
                os.remove(source)
            
            if self.on_complete:
                self.on_complete()
            
            return True
        
        except Exception as e:
            self._log_error(f"Errore copia file: {source} -> {destination} ({self._format_exc(e)})")
            if os.path.exists(destination):
                try:
                    os.remove(destination)
                except:
                    pass
            return False
    
    def _handle_directory(self, source: str, destination: str,
                         operation: OperationType) -> bool:
        """Gestisce copia/spostamento directory"""
        try:
            # Creare directory destinazione
            if not os.path.exists(destination):
                os.makedirs(destination, exist_ok=True)
            
            files_to_process = []
            
            # Raccogliere tutti i file
            for dirpath, dirnames, filenames in os.walk(source):
                for filename in filenames:
                    src_file = os.path.join(dirpath, filename)
                    rel_path = os.path.relpath(src_file, source)
                    dst_file = os.path.join(destination, rel_path)
                    files_to_process.append((src_file, dst_file))
            
            # Processare file
            for i, (src_file, dst_file) in enumerate(files_to_process, start=1):
                if self.is_cancelled:
                    return False
                
                # Creare subdirectory se necessaria
                dst_dir = os.path.dirname(dst_file)
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
                
                self.file_count = max(self.file_count, len(files_to_process))
                self.file_index = i
                self.current_file = os.path.basename(src_file)
                self._report_progress()
                
                # Ottimizza buffer in base a destinazione
                file_size = os.path.getsize(src_file)
                
                # Se target è ramdrive, usa buffer minimo
                dest_drive = os.path.splitdrive(dst_file)[0].upper()
                is_ramdrive = self.ramdrive_letter and dest_drive == f"{self.ramdrive_letter.upper()}:"
                
                if is_ramdrive:
                    # RamDrive: buffer ottimizzato (trasferimento RAM->RAM)
                    use_buffer = 8 * 1024 * 1024  # 8 MB
                elif file_size > self.LARGE_FILE_THRESHOLD:
                    # File grandi: buffer grande
                    use_buffer = self.LARGE_FILE_BUFFER
                else:
                    # File normali: buffer standard
                    use_buffer = self.buffer_size
                
                try:
                    with open(src_file, 'rb') as src, open(dst_file, 'wb') as dst:
                        while True:
                            buffer = src.read(use_buffer)
                            if not buffer:
                                break
                            dst.write(buffer)
                            self.processed_size += len(buffer)
                    
                    # Se move, cancellare sorgente
                    if operation == OperationType.MOVE:
                        os.remove(src_file)
                except Exception as e:
                    self._log_error(f"Errore file {src_file}: {e}")
            
            # Se move, cancellare directory source (se vuota)
            if operation == OperationType.MOVE:
                try:
                    os.rmdir(source)
                except:
                    pass  # Directory non vuota, ignorare
            
            return True
        except Exception as e:
            self._log_error(f"Errore directory: {e}")
            return False
    
    def _handle_file_with_ramdrive(self, source: str, destination: str,
                                  operation: OperationType,
                                  use_ramdrive_buffer: bool = False,
                                  ramdrive_temp_path: Optional[str] = None) -> bool:
        """Gestisce singolo file con supporto RamDrive 2-fasi"""
        try:
            if os.path.isdir(destination):
                destination = os.path.join(destination, os.path.basename(source))
            
            dest_dir = os.path.dirname(destination)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            self.current_file = os.path.basename(source)
            self._report_progress()
            
            # Flusso a 2 fasi con RamDrive
            if use_ramdrive_buffer and ramdrive_temp_path:
                return self._copy_via_ramdrive(source, destination, ramdrive_temp_path, operation)
            else:
                # Flusso diretto
                return self._handle_file(source, destination, operation)
        
        except Exception as e:
            self._log_error(f"Errore file {source}: {e}")
            return False
    
    def _handle_directory_with_ramdrive(self, source: str, destination: str,
                                       operation: OperationType,
                                       use_ramdrive_buffer: bool = False,
                                       ramdrive_temp_path: Optional[str] = None,
                                       files_to_process=None) -> bool:
        """Gestisce directory con supporto RamDrive 2-fasi"""
        try:
            if not os.path.exists(destination):
                os.makedirs(destination, exist_ok=True)

            if files_to_process is None:
                plan = self._prepare_directory_plan(source, destination)
                if plan is None:
                    return False
                files_to_process, total_size = plan
                self.total_size = total_size
            
            # Processare file
            for i, (src_file, dst_file) in enumerate(files_to_process, start=1):
                if self.is_cancelled:
                    return False
                
                dst_dir = os.path.dirname(dst_file)
                if not os.path.exists(dst_dir):
                    try:
                        os.makedirs(dst_dir, exist_ok=True)
                    except Exception as e:
                        self._log_error(f"Errore creazione directory: {dst_dir} ({self._format_exc(e)})")
                        return False
                
                self.file_count = max(self.file_count, len(files_to_process))
                self.file_index = i
                self.current_file = os.path.basename(src_file)
                
                # Flusso a 2 fasi o diretto
                if use_ramdrive_buffer and ramdrive_temp_path:
                    temp_file = os.path.join(ramdrive_temp_path, os.path.basename(src_file))
                    os.makedirs(ramdrive_temp_path, exist_ok=True)
                    if not self._copy_via_ramdrive(src_file, dst_file, ramdrive_temp_path, operation):
                        return False
                else:
                    if not self._handle_file(src_file, dst_file, operation):
                        return False
            
            if operation == OperationType.MOVE:
                try:
                    os.rmdir(source)
                except:
                    pass
            
            return True
        except Exception as e:
            self._log_error(f"Errore directory: {source} -> {destination} ({self._format_exc(e)})")
            return False
    
    def _copy_via_ramdrive(self, source: str, destination: str,
                          ramdrive_temp_path: str, operation: OperationType) -> bool:
        """Copia file a 2 fasi: Sorgente → RamDrive → Destinazione"""
        try:
            # Fase 1: Sorgente → RamDrive
            temp_file = os.path.join(ramdrive_temp_path, os.path.basename(source))
            os.makedirs(ramdrive_temp_path, exist_ok=True)
            
            if not self._copy_file_internal(source, temp_file, use_buffer=8 * 1024 * 1024):
                return False
            
            # Fase 2: RamDrive → Destinazione
            if not self._copy_file_internal(temp_file, destination, use_buffer=self.buffer_size):
                try:
                    os.remove(temp_file)
                except:
                    pass
                return False
            
            # Cleanup temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            # Se move, cancella source
            if operation == OperationType.MOVE:
                try:
                    os.remove(source)
                except:
                    pass
            
            return True
        except Exception as e:
            self._log_error(f"Errore copia via RamDrive: {e}")
            return False
    
    def _copy_file_internal(self, source: str, destination: str, use_buffer: int) -> bool:
        """Copia file con buffer specificato (senza delete source)"""
        try:
            with open(source, 'rb') as src, open(destination, 'wb') as dst:
                while True:
                    if self.is_cancelled:
                        try:
                            os.remove(destination)
                        except:
                            pass
                        return False
                    
                    buffer = src.read(use_buffer)
                    if not buffer:
                        break
                    
                    dst.write(buffer)
                    self.processed_size += len(buffer)
                    self._report_progress()
            
            return True
        except Exception as e:
            self._log_error(f"Errore copia interna: {source} -> {destination} ({self._format_exc(e)})")
            return False
            if self.on_complete:
                self.on_complete()
            
            return True
        
        except Exception as e:
            self._log_error(f"Errore copia directory: {e}")
            return False
    
    def _report_progress(self):
        """Riporta progress"""
        if self.on_progress:
            progress_data = {
                'current_file': self.current_file,
                'total_size': self.total_size,
                'processed_size': self.processed_size,
                'speed': self.current_speed,
                'percentage': (self.processed_size / max(self.total_size, 1)) * 100,
                'file_index': int(self.file_index),
                'file_count': int(self.file_count),
            }
            self.on_progress(progress_data)
    
    def _log_error(self, message: str):
        """Log errore"""
        if self.on_error:
            self.on_error(message)
