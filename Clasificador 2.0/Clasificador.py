import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
from datetime import datetime

class XMLClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clasificador de XML CFDI")
        self.root.geometry("700x320")  # Ventana más grande
        
        # Variables
        self.source_dir = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Listo para comenzar")
        
        # UI Components
        self.create_widgets()
        
        # Marca de agua más visible
        self.watermark = ttk.Label(
            self.root, 
            text="Fundación UNAM / Ing. Domauri Guerrero",
            font=('Arial', 10, 'italic'),
            foreground='gray'
        )
        self.watermark.place(relx=1.0, rely=1.0, anchor='se', x=-15, y=-15)
        
    def create_widgets(self):
        # Source Directory
        ttk.Label(self.root, text="Carpeta con XMLs:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(self.root, textvariable=self.source_dir, width=65).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Examinar...", command=self.browse_source).grid(row=0, column=2, padx=5, pady=5)
        
        # Destination Directory
        ttk.Label(self.root, text="Carpeta destino:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ttk.Entry(self.root, textvariable=self.dest_dir, width=65).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.root, text="Examinar...", command=self.browse_dest).grid(row=1, column=2, padx=5, pady=5)
        
        # Progress Bar
        ttk.Label(self.root, text="Progreso:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        ttk.Progressbar(self.root, variable=self.progress_var, maximum=100).grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Status
        ttk.Label(self.root, text="Estado:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        ttk.Label(self.root, textvariable=self.status_var).grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=5)
        
        # Process Button
        ttk.Button(self.root, text="Clasificar XMLs", command=self.process_files).grid(row=4, column=1, pady=15)
        
    def browse_source(self):
        directory = filedialog.askdirectory()
        if directory:
            self.source_dir.set(directory)
            
    def browse_dest(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dest_dir.set(directory)
    
    def process_files(self):
        source = self.source_dir.get()
        dest = self.dest_dir.get()
        
        if not source or not dest:
            messagebox.showerror("Error", "Debe seleccionar ambas carpetas")
            return
            
        try:
            xml_files = [f for f in Path(source).glob("*.xml") if f.is_file()]
            total_files = len(xml_files)
            
            if total_files == 0:
                messagebox.showinfo("Información", "No se encontraron archivos XML en la carpeta seleccionada")
                return
                
            self.status_var.set(f"Procesando 0 de {total_files} archivos...")
            self.root.update()
            
            for i, xml_file in enumerate(xml_files, 1):
                try:
                    self.process_single_file(xml_file, dest)
                except Exception as e:
                    print(f"Error procesando {xml_file.name}: {str(e)}")
                
                # Update progress
                progress = (i / total_files) * 100
                self.progress_var.set(progress)
                self.status_var.set(f"Procesando {i} de {total_files} archivos...")
                self.root.update()
                
            messagebox.showinfo("Completado", f"Procesados {total_files} archivos correctamente")
            self.status_var.set("Proceso completado")
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {str(e)}")
            self.status_var.set("Error en el proceso")
    
    def process_single_file(self, xml_file, dest_dir):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Namespace handling
            ns = {'cfdi': 'http://www.sat.gob.mx/cfd/4'}
            
            # Get Fecha (formato completo YYYY-MM-DD)
            fecha_completa = root.get('Fecha', 'SIN_FECHA')
            try:
                # Extraer solo la parte de la fecha (YYYY-MM-DD) antes de la 'T'
                fecha_parts = fecha_completa.split('T')
                fecha_folder = fecha_parts[0] if len(fecha_parts) > 0 else 'SIN_FECHA'
                # Validar que sea una fecha válida
                datetime.strptime(fecha_folder, '%Y-%m-%d')
            except (ValueError, IndexError):
                fecha_folder = 'SIN_FECHA'
            
            # Get Serie
            serie = root.get('Serie', 'SIN_SERIE')
            
            # Get Description from Conceptos
            descripcion = ""
            for concepto in root.findall('.//cfdi:Concepto', ns):
                descripcion = concepto.get('Descripcion', '')
                if descripcion:  # Take the first description found
                    break
            
            # Extract code from description (e.g., "Donativo - 99.00.100")
            code = "SIN_CODIGO"
            if "Donativo -" in descripcion:
                match = re.search(r"Donativo - (\d{2}\.\d{2}\.\d{3})", descripcion)
                if match:
                    code = match.group(1)
            elif any(char.isdigit() for char in descripcion):
                # Try to find any pattern like 99.00.313 in description
                match = re.search(r"(\d{2}\.\d{2}\.\d{3})", descripcion)
                if match:
                    code = match.group(1)
            
            # Create destination paths - ahora con jerarquía Fecha (día completo) -> Serie -> Código
            fecha_dir = os.path.join(dest_dir, fecha_folder)
            serie_dir = os.path.join(fecha_dir, f"Serie {serie}")
            code_dir = os.path.join(serie_dir, code)
            
            os.makedirs(code_dir, exist_ok=True)
            
            # Copy file to destination
            dest_path = os.path.join(code_dir, xml_file.name)
            shutil.copy2(xml_file, dest_path)
            
        except ET.ParseError as e:
            print(f"Error parsing XML {xml_file.name}: {str(e)}")
            # Move to error folder
            error_dir = os.path.join(dest_dir, "ERRORES")
            os.makedirs(error_dir, exist_ok=True)
            shutil.copy2(xml_file, os.path.join(error_dir, xml_file.name))
        except Exception as e:
            print(f"Error processing {xml_file.name}: {str(e)}")
            error_dir = os.path.join(dest_dir, "ERRORES")
            os.makedirs(error_dir, exist_ok=True)
            shutil.copy2(xml_file, os.path.join(error_dir, xml_file.name))

if __name__ == "__main__":
    root = tk.Tk()
    app = XMLClassifierApp(root)
    root.mainloop()