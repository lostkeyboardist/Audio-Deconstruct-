"""
Audio Utility App - Minimal Tkinter GUI.

Tabs: Stem Separator, Audio Converter.
Uses TaskQueue (queue_manager) for background work; engines run in queue worker.
"""

import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog

from queue_manager import TaskQueue


class AudioUtilityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Utility App")

        # Single task queue; callback runs on worker thread, we schedule UI update via after(0, ...)
        self.task_queue = TaskQueue()
        self.task_queue.on_task_update = self._on_task_update
        self.task_queue.start_processing()

        # Notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._build_stem_separator_tab()
        self._build_audio_converter_tab()

        # ETA label above queue panel
        self.eta_label = ttk.Label(root, text="ETA: 0 minutes 0 seconds")
        self.eta_label.pack(fill=tk.X, padx=5, pady=(0, 2))
        ttk.Button(root, text="Show Progress", command=self._show_progress_window).pack(fill=tk.X, padx=5, pady=(0, 2))

        # Queue panel at bottom (always visible)
        self.queue_frame = ttk.LabelFrame(root, text="Queue", padding=5)
        self.queue_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        pause_resume_frame = ttk.Frame(self.queue_frame)
        pause_resume_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(pause_resume_frame, text="Pause", command=self.task_queue.pause).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pause_resume_frame, text="Resume", command=self.task_queue.resume).pack(side=tk.LEFT)
        columns = ("ID", "File", "Operation", "Status")
        self.queue_tree = ttk.Treeview(self.queue_frame, columns=columns, show="headings", height=4)
        for col in columns:
            self.queue_tree.heading(col, text=col)
        self.queue_tree.tag_configure("waiting", foreground="gray")
        self.queue_tree.tag_configure("processing", foreground="blue")
        self.queue_tree.tag_configure("done", foreground="green")
        self.queue_tree.tag_configure("failed", foreground="red")
        self.queue_tree.pack(fill=tk.X)
        self.queue_tree.bind("<<TreeviewSelect>>", self._on_queue_selection_changed)

        # Move Up / Move Down buttons
        move_frame = ttk.Frame(self.queue_frame)
        move_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(move_frame, text="Move Up", command=self._on_move_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(move_frame, text="Move Down", command=self._on_move_down).pack(side=tk.LEFT)

        self._build_progress_window()

    def _build_progress_window(self):
        """Create detachable mini progress window (Toplevel). Created once at init."""
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Progress")
        self.progress_window.resizable(False, False)
        self.progress_window.protocol("WM_DELETE_WINDOW", self._hide_progress_window)
        f = ttk.Frame(self.progress_window, padding=8)
        f.pack(fill=tk.BOTH, expand=True)
        self._progress_task_id_label = ttk.Label(f, text="Task ID: —")
        self._progress_task_id_label.pack(anchor=tk.W)
        self._progress_operation_label = ttk.Label(f, text="Operation: —")
        self._progress_operation_label.pack(anchor=tk.W)
        self._progress_status_label = ttk.Label(f, text="Status: —")
        self._progress_status_label.pack(anchor=tk.W)
        self._progress_eta_label = ttk.Label(f, text="ETA: 0 minutes 0 seconds")
        self._progress_eta_label.pack(anchor=tk.W)
        self._progress_attached = True
        self.progress_window.transient(self.root)
        self._progress_detach_btn = ttk.Button(f, text="Detach", command=self._on_progress_detach_attach)
        self._progress_detach_btn.pack(anchor=tk.W, pady=(8, 0))

    def _hide_progress_window(self):
        """Hide progress window without destroying it."""
        self.progress_window.withdraw()

    def _show_progress_window(self):
        """Show and bring progress window to front."""
        self.progress_window.deiconify()
        self.progress_window.lift()

    def _on_progress_detach_attach(self):
        """Toggle progress window between attached (transient) and detached."""
        self._progress_attached = not self._progress_attached
        if self._progress_attached:
            self.progress_window.transient(self.root)
            self._progress_detach_btn.config(text="Detach")
        else:
            self.progress_window.transient()
            self._progress_detach_btn.config(text="Attach")

    def _refresh_queue_display(self):
        """Clear and repopulate the queue tree from task_queue.get_tasks()."""
        for i in self.queue_tree.get_children():
            self.queue_tree.delete(i)
        for t in self.task_queue.get_tasks():
            self.queue_tree.insert(
                "",
                tk.END,
                values=(
                    t["id"],
                    Path(t["file_path"]).name,
                    t["operation"],
                    t["status"],
                ),
                tags=(t["status"],),
            )

    def _on_queue_selection_changed(self, event=None):
        """Called when queue tree selection changes (binding)."""
        pass

    def _on_move_up(self):
        """Move selected task up; refresh queue display."""
        sel = self.queue_tree.selection()
        if not sel:
            return
        values = self.queue_tree.item(sel[0])["values"]
        task_id = int(values[0])
        if self.task_queue.move_task(task_id, "up"):
            self._refresh_queue_display()

    def _on_move_down(self):
        """Move selected task down; refresh queue display."""
        sel = self.queue_tree.selection()
        if not sel:
            return
        values = self.queue_tree.item(sel[0])["values"]
        task_id = int(values[0])
        if self.task_queue.move_task(task_id, "down"):
            self._refresh_queue_display()

    # -------------------------------------------------------------------------
    # STEM SEPARATOR TAB
    # -------------------------------------------------------------------------
    def _build_stem_separator_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Stem Separator")

        row = 0

        # Select Audio File
        ttk.Button(tab, text="Select Audio File", command=self._stem_select_file).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2)
        )
        row += 1
        self.stem_file_label = ttk.Label(tab, text="No file selected", foreground="gray")
        self.stem_file_label.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Select Output Folder
        ttk.Button(tab, text="Select Output Folder", command=self._stem_select_folder).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2)
        )
        row += 1
        self.stem_folder_label = ttk.Label(tab, text="No folder selected", foreground="gray")
        self.stem_folder_label.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Model selection
        ttk.Label(tab, text="Model").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.stem_model_var = tk.StringVar(value="htdemucs")
        stem_model_combo = ttk.Combobox(
            tab,
            textvariable=self.stem_model_var,
            values=["htdemucs", "htdemucs_ft"],
            state="readonly",
            width=20,
        )
        stem_model_combo.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Shifts selection
        ttk.Label(tab, text="Shifts (higher = better quality, slower)").grid(
            row=row, column=0, sticky=tk.W
        )
        row += 1
        self.stem_shifts_var = tk.StringVar(value="1")
        stem_shifts_combo = ttk.Combobox(
            tab,
            textvariable=self.stem_shifts_var,
            values=[1, 2, 4],
            state="readonly",
            width=10,
        )
        stem_shifts_combo.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Overlap selection
        ttk.Label(tab, text="Overlap (smoother stitching, slower)").grid(
            row=row, column=0, sticky=tk.W
        )
        row += 1
        self.stem_overlap_var = tk.StringVar(value="0.25")
        stem_overlap_combo = ttk.Combobox(
            tab,
            textvariable=self.stem_overlap_var,
            values=[0.25, 0.5],
            state="readonly",
            width=10,
        )
        stem_overlap_combo.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Separate Stems button (adds task to queue)
        self.stem_btn = ttk.Button(tab, text="Separate Stems", command=self._run_separate_stems)
        self.stem_btn.grid(row=row, column=0, sticky=tk.W, pady=(5, 10))
        row += 1

        # Log / result Text widget
        ttk.Label(tab, text="Result:").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.stem_log = tk.Text(tab, height=8, width=60, wrap=tk.WORD)
        self.stem_log.grid(row=row, column=0, sticky=tk.NSEW, pady=(0, 5))
        tab.grid_rowconfigure(row, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self.stem_file_paths = []
        self.stem_folder_path = ""

    def _stem_select_file(self):
        paths = filedialog.askopenfilenames(
            title="Select Audio File(s)",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                ("All files", "*.*"),
            ],
        )
        if paths:
            self.stem_file_paths = list(paths)
            if len(self.stem_file_paths) == 1:
                self.stem_file_label.config(text=Path(self.stem_file_paths[0]).name, foreground="black")
            else:
                self.stem_file_label.config(text=f"{len(self.stem_file_paths)} files selected", foreground="black")

    def _stem_select_folder(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.stem_folder_path = path
            self.stem_folder_label.config(text=path, foreground="black")

    def _run_separate_stems(self):
        """Validate inputs and add stem-separation tasks to the queue (one per file)."""
        self.stem_log.delete(1.0, tk.END)
        if not self.stem_file_paths:
            self.stem_log.insert(tk.END, "Error: Please select at least one audio file.\n")
            return
        if not self.stem_folder_path:
            self.stem_log.insert(tk.END, "Error: Please select an output folder.\n")
            return
        try:
            model = self.stem_model_var.get()
            selected_shifts = int(self.stem_shifts_var.get())
            selected_overlap = float(self.stem_overlap_var.get())
        except (ValueError, TypeError) as e:
            self.stem_log.insert(tk.END, f"Error: Invalid shifts or overlap. Please use valid numbers.\n{e}\n")
            return

        params = {
            "output_dir": self.stem_folder_path,
            "model": model,
            "use_gpu": True,
            "shifts": selected_shifts,
            "overlap": selected_overlap,
        }
        for file_path in self.stem_file_paths:
            self.task_queue.add_task(file_path, "stem", params)
        self.stem_log.insert(tk.END, f"Added {len(self.stem_file_paths)} task(s) to queue.\n")

    # -------------------------------------------------------------------------
    # AUDIO CONVERTER TAB
    # -------------------------------------------------------------------------
    def _build_audio_converter_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Audio Converter")

        row = 0

        # Select Audio File
        ttk.Button(tab, text="Select Audio File", command=self._convert_select_file).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2)
        )
        row += 1
        self.convert_file_label = ttk.Label(tab, text="No file selected", foreground="gray")
        self.convert_file_label.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Select Output Folder
        ttk.Button(tab, text="Select Output Folder", command=self._convert_select_folder).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2)
        )
        row += 1
        self.convert_folder_label = ttk.Label(tab, text="No folder selected", foreground="gray")
        self.convert_folder_label.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Output format dropdown
        ttk.Label(tab, text="Output format").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.convert_format_var = tk.StringVar(value="wav")
        convert_format_combo = ttk.Combobox(
            tab,
            textvariable=self.convert_format_var,
            values=["mp3", "wav", "mpeg"],
            state="readonly",
            width=15,
        )
        convert_format_combo.grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Auto chain: add stem-separation task after each successful conversion
        self.auto_chain_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            tab,
            text="Auto-separate after conversion",
            variable=self.auto_chain_var,
        ).grid(row=row, column=0, sticky=tk.W)
        row += 2

        # Convert Audio button (adds task to queue)
        self.convert_btn = ttk.Button(tab, text="Convert Audio", command=self._run_convert_audio)
        self.convert_btn.grid(row=row, column=0, sticky=tk.W, pady=(5, 10))
        row += 1

        # Result Text widget
        ttk.Label(tab, text="Result:").grid(row=row, column=0, sticky=tk.W)
        row += 1
        self.convert_log = tk.Text(tab, height=8, width=60, wrap=tk.WORD)
        self.convert_log.grid(row=row, column=0, sticky=tk.NSEW, pady=(0, 5))
        tab.grid_rowconfigure(row, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self.convert_file_paths = []
        self.convert_folder_path = ""

    def _convert_select_file(self):
        paths = filedialog.askopenfilenames(
            title="Select Audio File(s)",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                ("All files", "*.*"),
            ],
        )
        if paths:
            self.convert_file_paths = list(paths)
            if len(self.convert_file_paths) == 1:
                self.convert_file_label.config(text=Path(self.convert_file_paths[0]).name, foreground="black")
            else:
                self.convert_file_label.config(text=f"{len(self.convert_file_paths)} files selected", foreground="black")

    def _convert_select_folder(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.convert_folder_path = path
            self.convert_folder_label.config(text=path, foreground="black")

    def _run_convert_audio(self):
        """Validate inputs and add convert tasks to the queue (one per file)."""
        self.convert_log.delete(1.0, tk.END)
        if not self.convert_file_paths:
            self.convert_log.insert(tk.END, "Error: Please select at least one audio file.\n")
            return
        if not self.convert_folder_path:
            self.convert_log.insert(tk.END, "Error: Please select an output folder.\n")
            return

        params = {
            "output_dir": self.convert_folder_path,
            "output_format": self.convert_format_var.get(),
        }
        for file_path in self.convert_file_paths:
            self.task_queue.add_task(file_path, "convert", params)
        self.convert_log.insert(tk.END, f"Added {len(self.convert_file_paths)} task(s) to queue.\n")

    # -------------------------------------------------------------------------
    # Task queue callback: runs on worker thread; schedule UI update on main thread
    # -------------------------------------------------------------------------
    def _on_task_update(self, task):
        """Called from queue worker thread; schedule UI update via root.after(0, ...)."""
        self.root.after(0, self._apply_task_update, task)

    def _apply_task_update(self, task):
        """Runs on main thread. Update tab log and refresh the queue panel."""
        # Update the appropriate tab log
        log = self.stem_log if task["operation"] == "stem" else self.convert_log
        log.delete(1.0, tk.END)
        log.insert(tk.END, f"Task ID: {task['id']}\n")
        log.insert(tk.END, f"Operation: {task['operation']}\n")
        log.insert(tk.END, f"Status: {task['status']}\n")
        if task["status"] == "processing":
            log.insert(tk.END, "Processing...\n")
        if task["status"] in ("done", "failed") and task.get("result"):
            r = task["result"]
            log.insert(tk.END, f"message: {r.get('message', '')}\n")
            log.insert(tk.END, f"output_path: {r.get('output_path', '')}\n")

        self._refresh_queue_display()

        eta = self.task_queue.get_eta()
        minutes = int(eta // 60)
        seconds = int(eta % 60)
        eta_text = f"ETA: {minutes} minutes {seconds} seconds"
        self.eta_label.config(text=eta_text)

        if self.progress_window.winfo_exists():
            self._progress_task_id_label.config(text=f"Task ID: {task['id']}")
            self._progress_operation_label.config(text=f"Operation: {task['operation']}")
            self._progress_status_label.config(text=f"Status: {task['status']}")
            self._progress_eta_label.config(text=eta_text)

        # Auto chain: when a convert task finishes and option is on, add a stem task
        if (
            task["operation"] == "convert"
            and task["status"] == "done"
            and self.auto_chain_var.get()
        ):
            result = task.get("result")
            if result and result.get("output_path"):
                output_path = result["output_path"]
                output_dir = str(Path(output_path).parent)
                stem_params = {
                    "output_dir": output_dir,
                    "model": "htdemucs",
                    "use_gpu": True,
                    "shifts": 1,
                    "overlap": 0.25,
                }
                self.task_queue.add_task(output_path, "stem", stem_params)
                self.convert_log.insert(tk.END, "Auto-added stem task.\n")


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioUtilityApp(root)
    root.mainloop()
