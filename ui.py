import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import datetime

from config import ALL_FORMATS, MACHINE_READABLE_FORMATS, OUTPUT_FORMATS, DB_PATH
from file_processing import detect_file_readability, process_file
from db_ops import get_all_documents, search_documents, rebuild_fts_index


def create_gui():
    class DocumentProcessorGUI:
        def __init__(self, master):
            self.master = master
            self.master.title("Advanced Document Manager with Readability Detection")
            self.master.geometry("1200x800")

            self.selected_files = []  # (file_path, custom_name, tags, description, force_ocr)

            self.create_widgets()
            self.refresh_document_list()

        def create_widgets(self):
            self.notebook = ttk.Notebook(self.master)
            self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

            self.process_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.process_frame, text="Process Files")
            self.create_process_tab()

            self.search_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.search_frame, text="Search & Browse")
            self.create_search_tab()

        def create_process_tab(self):
            title_label = tk.Label(self.process_frame, text="Advanced Document Processor",
                                   font=("Arial", 16, "bold"))
            title_label.pack(pady=10)

            file_frame = ttk.LabelFrame(self.process_frame, text="File Selection", padding=10)
            file_frame.pack(fill="x", padx=20, pady=10)

            file_buttons = ttk.Frame(file_frame)
            file_buttons.pack(fill="x", pady=(0, 10))

            ttk.Button(file_buttons, text="Select Files",
                       command=self.select_files).pack(side="left")
            ttk.Button(file_buttons, text="Clear Selection",
                       command=self.clear_files).pack(side="left", padx=(10, 0))
            ttk.Button(file_buttons, text="Edit File Info",
                       command=self.edit_file_info).pack(side="left", padx=(10, 0))

            self.files_text = tk.Text(file_frame, height=8, width=70)
            scrollbar_files = ttk.Scrollbar(file_frame, orient="vertical", command=self.files_text.yview)
            self.files_text.configure(yscrollcommand=scrollbar_files.set)
            self.files_text.pack(side="left", fill="both", expand=True)
            scrollbar_files.pack(side="right", fill="y")

            options_frame = ttk.LabelFrame(self.process_frame, text="Processing Options", padding=10)
            options_frame.pack(fill="x", padx=20, pady=10)

            format_subframe = ttk.Frame(options_frame)
            format_subframe.pack(fill="x", pady=(0, 10))
            ttk.Label(format_subframe, text="Output Format:").pack(anchor="w")

            self.output_format = tk.StringVar(value="txt")
            format_row = ttk.Frame(format_subframe)
            format_row.pack(fill="x", pady=(5, 0))

            for i, (format_key, format_name) in enumerate(OUTPUT_FORMATS.items()):
                ttk.Radiobutton(format_row, text=format_name,
                                variable=self.output_format,
                                value=format_key).pack(side="left", padx=(0, 20))

            global_options = ttk.Frame(options_frame)
            global_options.pack(fill="x", pady=(10, 0))
            self.force_ocr_all = tk.BooleanVar()
            ttk.Checkbutton(global_options, text="Force OCR for all files (ignore machine readability)",
                            variable=self.force_ocr_all).pack(anchor="w")

            ttk.Button(self.process_frame, text="Process Files",
                       command=self.process_files,
                       style="Accent.TButton").pack(pady=20)

            results_frame = ttk.LabelFrame(self.process_frame, text="Processing Results", padding=10)
            results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            self.results_text = tk.Text(results_frame, height=12)
            scrollbar_results = ttk.Scrollbar(results_frame, orient="vertical",
                                              command=self.results_text.yview)
            self.results_text.configure(yscrollcommand=scrollbar_results.set)
            self.results_text.pack(side="left", fill="both", expand=True)
            scrollbar_results.pack(side="right", fill="y")

        def create_search_tab(self):
            search_frame = ttk.LabelFrame(self.search_frame, text="Search Documents", padding=10)
            search_frame.pack(fill="x", padx=20, pady=10)

            search_row1 = ttk.Frame(search_frame)
            search_row1.pack(fill="x", pady=(0, 5))
            ttk.Label(search_row1, text="Search:").pack(side="left")
            self.search_var = tk.StringVar()
            self.search_entry = ttk.Entry(search_row1, textvariable=self.search_var, width=30)
            self.search_entry.pack(side="left", padx=(5, 10))
            self.search_entry.bind("<Return>", lambda e: self.search_documents())
            ttk.Button(search_row1, text="Search",
                       command=self.search_documents).pack(side="left", padx=(5, 10))
            ttk.Button(search_row1, text="Show All",
                       command=self.refresh_document_list).pack(side="left")

            search_row2 = ttk.Frame(search_frame)
            search_row2.pack(fill="x", pady=(5, 0))

            ttk.Label(search_row2, text="Search Type:").pack(side="left")
            self.search_type = tk.StringVar(value="all")
            search_types = [("All", "all"), ("Name", "name"), ("Content", "content"), ("Tags", "tags")]
            for text, value in search_types:
                ttk.Radiobutton(search_row2, text=text, variable=self.search_type,
                                value=value).pack(side="left", padx=(5, 0))

            ttk.Label(search_row2, text="Filter:").pack(side="left", padx=(20, 5))
            self.readability_filter = tk.StringVar(value="all")
            readability_filters = [("All Files", "all"), ("Machine Readable", "machine_readable"),
                                   ("Non-Machine Readable", "non_machine_readable")]
            for text, value in readability_filters:
                ttk.Radiobutton(search_row2, text=text, variable=self.readability_filter,
                                value=value).pack(side="left", padx=(5, 0))

            list_frame = ttk.LabelFrame(self.search_frame, text="Documents", padding=10)
            list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

            columns = ("ID", "Name", "Custom Name", "Format", "Readable", "Size", "Words", "Tags", "Date")
            self.doc_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

            column_widths = {
                "ID": 50, "Name": 150, "Custom Name": 150, "Format": 80,
                "Readable": 100, "Size": 80, "Words": 80, "Tags": 120, "Date": 120
            }
            for col in columns:
                self.doc_tree.heading(col, text=col)
                self.doc_tree.column(col, width=column_widths[col])

            tree_scroll_v = ttk.Scrollbar(list_frame, orient="vertical", command=self.doc_tree.yview)
            tree_scroll_h = ttk.Scrollbar(list_frame, orient="horizontal", command=self.doc_tree.xview)
            self.doc_tree.configure(yscrollcommand=tree_scroll_v.set, xscrollcommand=tree_scroll_h.set)

            tree_frame = ttk.Frame(list_frame)
            tree_frame.pack(fill="both", expand=True)

            self.doc_tree.pack(side="left", fill="both", expand=True)
            tree_scroll_v.pack(side="right", fill="y")
            tree_scroll_h.pack(side="bottom", fill="x")

            self.doc_tree.bind("<Double-1>", self.view_document_details)

            action_frame = ttk.Frame(self.search_frame)
            action_frame.pack(fill="x", padx=20, pady=(0, 20))
            ttk.Button(action_frame, text="View Details",
                      command=self.view_document_details).pack(side="left", padx=(0, 10))
            ttk.Button(action_frame, text="Open File",
                      command=self.open_selected_file).pack(side="left", padx=(0, 10))
            ttk.Button(action_frame, text="Delete",
                      command=self.delete_selected_document).pack(side="left", padx=(0, 10))
            ttk.Button(action_frame, text="Rebuild Search Index",
                      command=self.rebuild_search_index).pack(side="left", padx=(0, 10))

        def select_files(self):
            filetypes = [("All Supported", " ".join([f"*.{ext}" for ext in ALL_FORMATS.keys()]))]
            filetypes.append(("Machine Readable", " ".join([f"*.{ext}" for ext in MACHINE_READABLE_FORMATS.keys()])))
            filetypes.append(("Images/Scanned", " ".join([f"*.{ext}" for ext in ['jpg','jpeg','png','tiff','bmp','gif','webp']])))
            for ext, desc in ALL_FORMATS.items():
                filetypes.append((desc, f"*.{ext}"))
            filetypes.append(("All files", "*.*"))

            files = filedialog.askopenfilenames(
                title="Select files to process",
                filetypes=filetypes
            )

            if files:
                for file_path in files:
                    base_name = Path(file_path).stem
                    self.selected_files.append((file_path, base_name, "", "", False))
                self.update_files_display()

        def clear_files(self):
            self.selected_files = []
            self.update_files_display()

        def edit_file_info(self):
            if not self.selected_files:
                messagebox.showwarning("Warning", "Please select files first.")
                return
            self.edit_dialog()

        def edit_dialog(self):
            dialog = tk.Toplevel(self.master)
            dialog.title("Edit File Information and Processing Options")
            dialog.geometry("1000x700")
            dialog.transient(self.master)
            dialog.grab_set()

            columns = ("File Path", "Custom Name", "Tags", "Description", "Force OCR")
            edit_tree = ttk.Treeview(dialog, columns=columns, show="headings", height=15)

            column_widths = {"File Path": 250, "Custom Name": 150, "Tags": 150, "Description": 200, "Force OCR": 80}
            for col in columns:
                edit_tree.heading(col, text=col)
                edit_tree.column(col, width=column_widths[col])

            for i, (file_path, custom_name, tags, description, force_ocr) in enumerate(self.selected_files):
                edit_tree.insert("", "end", iid=i, values=(
                    file_path, custom_name, tags, description, "Yes" if force_ocr else "No"
                ))

            edit_tree.pack(fill="both", expand=True, padx=10, pady=10)

            def edit_selected():
                selection = edit_tree.selection()
                if not selection:
                    messagebox.showwarning("Warning", "Please select a file to edit.")
                    return
                item_id = selection[0]
                current_values = edit_tree.item(item_id)['values']

                edit_item_dialog = tk.Toplevel(dialog)
                edit_item_dialog.title("Edit File Information")
                edit_item_dialog.geometry("600x400")
                edit_item_dialog.transient(dialog)
                edit_item_dialog.grab_set()

                info_frame = ttk.LabelFrame(edit_item_dialog, text="File Information", padding=10)
                info_frame.pack(fill="x", padx=10, pady=5)

                file_path = current_values[0]
                is_readable = detect_file_readability(file_path)

                tk.Label(info_frame, text=f"File: {os.path.basename(file_path)}",
                        font=("Arial", 10, "bold")).pack(anchor="w")
                tk.Label(info_frame, text=f"Format: {Path(file_path).suffix.upper()}",
                        fg="blue").pack(anchor="w")
                tk.Label(info_frame, text=f"Readability: {'Machine Readable' if is_readable else 'Requires OCR'}",
                        fg="green" if is_readable else "orange").pack(anchor="w")

                name_frame = ttk.LabelFrame(edit_item_dialog, text="Custom Name", padding=10)
                name_frame.pack(fill="x", padx=10, pady=5)
                name_var = tk.StringVar(value=current_values[1])
                name_entry = ttk.Entry(name_frame, textvariable=name_var, width=60)
                name_entry.pack(fill="x")

                tags_frame = ttk.LabelFrame(edit_item_dialog, text="Tags (comma-separated)", padding=10)
                tags_frame.pack(fill="x", padx=10, pady=5)
                tags_var = tk.StringVar(value=current_values[2])
                tags_entry = ttk.Entry(tags_frame, textvariable=tags_var, width=60)
                tags_entry.pack(fill="x")

                desc_frame = ttk.LabelFrame(edit_item_dialog, text="Description", padding=10)
                desc_frame.pack(fill="both", expand=True, padx=10, pady=5)
                desc_text = tk.Text(desc_frame, height=4, wrap=tk.WORD)
                desc_text.insert("1.0", current_values[3])
                desc_text.pack(fill="both", expand=True)

                options_frame = ttk.LabelFrame(edit_item_dialog, text="Processing Options", padding=10)
                options_frame.pack(fill="x", padx=10, pady=5)
                force_ocr_var = tk.BooleanVar(value=current_values[4] == "Yes")
                ttk.Checkbutton(options_frame, text="Force OCR (ignore machine readability)",
                               variable=force_ocr_var).pack(anchor="w")

                def save_changes():
                    new_name = name_var.get().strip()
                    new_tags = tags_var.get().strip()
                    new_description = desc_text.get("1.0", tk.END).strip()
                    new_force_ocr = force_ocr_var.get()
                    if not new_name:
                        messagebox.showerror("Error", "Custom name cannot be empty.")
                        return
                    idx = int(item_id)
                    file_path = self.selected_files[idx][0]
                    self.selected_files[idx] = (file_path, new_name, new_tags, new_description, new_force_ocr)
                    edit_tree.item(item_id, values=(file_path, new_name, new_tags, new_description,
                                                    "Yes" if new_force_ocr else "No"))
                    edit_item_dialog.destroy()

                ttk.Button(edit_item_dialog, text="Save Changes", command=save_changes).pack(pady=10)

            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill="x", padx=10, pady=10)
            ttk.Button(button_frame, text="Edit Selected", command=edit_selected).pack(side="left", padx=(0, 10))

            def apply_changes():
                self.update_files_display()
                dialog.destroy()

            ttk.Button(button_frame, text="Apply Changes", command=apply_changes).pack(side="left", padx=(0, 10))
            ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side="left")

        def update_files_display(self):
            self.files_text.delete(1.0, tk.END)
            if self.selected_files:
                for file_path, custom_name, tags, description, force_ocr in self.selected_files:
                    original_name = os.path.basename(file_path)
                    is_readable = detect_file_readability(file_path)
                    display_text = f"File: {original_name}\n"
                    display_text += f"Custom Name: {custom_name}\n"
                    display_text += f"Readability: {'Machine Readable' if is_readable else 'Requires OCR'}\n"
                    if force_ocr:
                        display_text += "Processing: Force OCR\n"
                    if tags:
                        display_text += f"Tags: {tags}\n"
                    if description:
                        display_text += f"Description: {description}\n"
                    display_text += "-" * 60 + "\n"
                    self.files_text.insert(tk.END, display_text)
            else:
                self.files_text.insert(tk.END, "No files selected")

        def process_files(self):
            if not self.selected_files:
                messagebox.showwarning("Warning", "Please select at least one file.")
                return
            output_fmt = self.output_format.get()
            force_ocr_global = self.force_ocr_all.get()
            self.results_text.delete(1.0, tk.END)
            try:
                processed_count = 0
                failed_count = 0
                for file_path, custom_name, tags, description, force_ocr_individual in self.selected_files:
                    try:
                        force_ocr = force_ocr_global or force_ocr_individual
                        is_readable = detect_file_readability(file_path)
                        self.results_text.insert(tk.END, f"Processing: {custom_name}\n")
                        self.results_text.insert(tk.END, f"  File Type: {Path(file_path).suffix.upper()}\n")
                        self.results_text.insert(tk.END, f"  Readability: {'Machine Readable' if is_readable else 'Requires OCR'}\n")
                        self.results_text.insert(tk.END, f"  Processing Method: {'OCR' if force_ocr or not is_readable else 'Direct Extraction'}\n")
                        self.master.update()
                        result = process_file(file_path, output_fmt, custom_name, tags, description, force_ocr)
                        if result['readable']:
                            self.results_text.insert(tk.END, f"✓ SUCCESS: Text extracted and saved\n")
                            self.results_text.insert(tk.END, f"  Word Count: {result['word_count']}\n")
                            self.results_text.insert(tk.END, f"  Output: {result['output_format'].upper()} format\n")
                            processed_count += 1
                        else:
                            self.results_text.insert(tk.END, f"✗ FAILED: Could not extract readable text\n")
                            failed_count += 1
                        self.results_text.insert(tk.END, "-" * 60 + "\n")
                        self.master.update()
                    except Exception as e:
                        self.results_text.insert(tk.END, f"✗ ERROR processing '{custom_name}': {str(e)}\n")
                        failed_count += 1
                self.results_text.insert(tk.END, f"\nPROCESSING SUMMARY:\n")
                self.results_text.insert(tk.END, f"Successfully processed: {processed_count}\n")
                self.results_text.insert(tk.END, f"Failed: {failed_count}\n")
                self.results_text.insert(tk.END, f"Total files: {len(self.selected_files)}\n")
                self.results_text.insert(tk.END, f"Database: {DB_PATH}\n")
                if processed_count > 0:
                    storage_dir = os.path.join(os.path.dirname(__file__), "storage")
                    self.results_text.insert(tk.END, f"Files stored in: {storage_dir}\n")
                    self.refresh_document_list()
                self.selected_files = []
                self.update_files_display()
            except Exception as e:
                messagebox.showerror("Error", f"Processing failed: {str(e)}")

        def search_documents(self):
            query = self.search_var.get().strip()
            if not query:
                messagebox.showwarning("Warning", "Please enter a search term.")
                return
            search_type = self.search_type.get()
            readability_filter = self.readability_filter.get()
            try:
                results = search_documents(query, search_type, readability_filter)
                self.populate_document_list(results)
                count = len(results)
                filter_text = {
                    "all": "all files",
                    "machine_readable": "machine readable files",
                    "non_machine_readable": "non-machine readable files"
                }
                messagebox.showinfo("Search Results",
                                    f"Found {count} results in {filter_text[readability_filter]} "
                                    f"searching by {search_type}")
            except Exception as e:
                messagebox.showerror("Error", f"Search failed: {str(e)}")

        def refresh_document_list(self):
            try:
                readability_filter = getattr(self, 'readability_filter', None)
                filter_value = readability_filter.get() if readability_filter else "all"
                results = get_all_documents(filter_value)
                self.populate_document_list(results)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load documents: {str(e)}")

        def populate_document_list(self, results):
            for item in self.doc_tree.get_children():
                self.doc_tree.delete(item)
            for row in results:
                doc_id, name, custom_name, path, original_format, is_machine_readable, readable, \
                extracted_text_path, output_format, output_path, processing_method, file_size, \
                word_count, tags, description, ingested_at, updated_at, content = row
                if file_size:
                    if file_size > 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    elif file_size > 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size} B"
                else:
                    size_str = "N/A"
                if is_machine_readable:
                    readable_str = "Machine ✓" if readable else "Machine ✗"
                else:
                    readable_str = "OCR ✓" if readable else "OCR ✗"
                try:
                    date_obj = datetime.datetime.fromisoformat(updated_at)
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = updated_at
                word_str = str(word_count) if word_count else "0"
                self.doc_tree.insert("", "end", values=(
                    doc_id, name, custom_name or "N/A", original_format.upper(),
                    readable_str, size_str, word_str, tags or "N/A", date_str
                ))

        def view_document_details(self, event=None):
            selection = self.doc_tree.selection()
            if not selection:
                if event is None:
                    messagebox.showwarning("Warning", "Please select a document to view.")
                return
            item = self.doc_tree.item(selection[0])
            doc_id = item['values'][0]
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""SELECT d.*, et.content FROM documents d 
                        LEFT JOIN extracted_texts et ON d.id = et.doc_id
                        WHERE d.id = ?""", (doc_id,))
            result = c.fetchone()
            conn.close()
            if not result:
                messagebox.showerror("Error", "Document not found.")
                return
            details_dialog = tk.Toplevel(self.master)
            details_dialog.title(f"Document Details - {result[1]}")
            details_dialog.geometry("900x700")
            details_dialog.transient(self.master)
            details_notebook = ttk.Notebook(details_dialog)
            details_notebook.pack(fill="both", expand=True, padx=10, pady=10)
            info_frame = ttk.Frame(details_notebook)
            details_notebook.add(info_frame, text="Information")
            info_text = tk.Text(info_frame, wrap=tk.WORD, padx=10, pady=10)
            info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=info_text.yview)
            info_text.configure(yscrollcommand=info_scroll.set)
            info_content = f"""Document Information:

Original Name: {result[1]}
Custom Name: {result[2] or 'N/A'}
File Path: {result[3]}
Original Format: {result[4].upper()}
Machine Readable: {'Yes' if result[5] else 'No'}
Text Extracted: {'Yes' if result[6] else 'No'}
Output Format: {result[8] or 'N/A'}
Processing Method: {result[10]}
File Size: {result[11]} bytes ({result[11] / 1024:.1f} KB)
Word Count: {result[12]}
Tags: {result[13] or 'None'}
Description: {result[14] or 'None'}
Created: {result[15]}
Updated: {result[16]}

Processing Details:
- Readability Detection: {'Detected as machine readable' if result[5] else 'Detected as requiring OCR'}
- Extraction Method: {result[10]}
- Text Available: {'Yes, searchable' if result[17] else 'No text content'}
"""
            info_text.insert("1.0", info_content)
            info_text.configure(state="disabled")
            info_text.pack(side="left", fill="both", expand=True)
            info_scroll.pack(side="right", fill="y")
            if result[17]:
                content_frame = ttk.Frame(details_notebook)
                details_notebook.add(content_frame, text="Content")
                content_text = tk.Text(content_frame, wrap=tk.WORD, padx=10, pady=10)
                content_scroll = ttk.Scrollbar(content_frame, orient="vertical", command=content_text.yview)
                content_text.configure(yscrollcommand=content_scroll.set)
                content_text.insert("1.0", result[17])
                content_text.configure(state="disabled")
                content_text.pack(side="left", fill="both", expand=True)
                content_scroll.pack(side="right", fill="y")

        def open_selected_file(self):
            selection = self.doc_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a document to open.")
                return
            item = self.doc_tree.item(selection[0])
            doc_id = item['values'][0]
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT path, output_path FROM documents WHERE id = ?", (doc_id,))
            result = c.fetchone()
            conn.close()
            if not result:
                messagebox.showerror("Error", "Document not found.")
                return
            file_path = result[1] if result[1] and os.path.exists(result[1]) else result[0]
            if os.path.exists(file_path):
                try:
                    if sys.platform.startswith('darwin'):
                        os.system(f'open "{file_path}"')
                    elif sys.platform.startswith('win'):
                        os.system(f'start "" "{file_path}"')
                    else:
                        os.system(f'xdg-open "{file_path}"')
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open file: {str(e)}")
            else:
                messagebox.showerror("Error", "File not found on disk.")

        def delete_selected_document(self):
            selection = self.doc_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a document to delete.")
                return
            item = self.doc_tree.item(selection[0])
            doc_id = item['values'][0]
            doc_name = item['values'][2]
            if not messagebox.askyesno("Confirm Delete",
                                       f"Are you sure you want to delete '{doc_name}'?\n"
                                       "This will remove the database entry and associated files."):
                return
            try:
                import sqlite3
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT path, extracted_text_path, output_path FROM documents WHERE id = ?", (doc_id,))
                result = c.fetchone()
                if result:
                    c.execute("DELETE FROM documents_fts WHERE doc_id = ?", (doc_id,))
                    c.execute("DELETE FROM extracted_texts WHERE doc_id = ?", (doc_id,))
                    c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                    conn.commit()
                    for file_path in result:
                        if file_path and os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f"Warning: Could not delete file {file_path}: {e}")
                conn.close()
                self.refresh_document_list()
                messagebox.showinfo("Success", f"Document '{doc_name}' deleted successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete document: {str(e)}")

        def rebuild_search_index(self):
            try:
                rebuild_fts_index()
                messagebox.showinfo("Success", "Search index rebuilt successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rebuild search index: {str(e)}")

    root = tk.Tk()
    app = DocumentProcessorGUI(root)
    root.mainloop()


