
import os
import sys
import threading
import logging
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from db_connect import get_signatures, test_connection
import scanner
from scanner import ScanStatus

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

APP_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("NeuralDefender.GUI")

# Color palette (dark theme)
COLORS = {
    "bg": "#12181f",
    "surface": "#1a232e",
    "surface_alt": "#212c3a",
    "accent": "#2bb6b6",
    "accent_hover": "#35d0d0",
    "text": "#e8edf2",
    "text_dim": "#8a97a6",
    "safe": "#3ddc84",
    "infected": "#ff5c5c",
    "warning": "#ffb84d",
    "border": "#2a3644",
}

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"


def asset_path(filename: str) -> str:
    """Resolve a bundled asset relative to this script, not the cwd."""
    return os.path.join(APP_DIR, filename)


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

class NeuralDefenderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected_path = None       # file OR directory
        self.is_directory = False
        self.signatures_cache = None
        self.scan_in_progress = False

        self._configure_window()
        self._configure_styles()
        self._build_layout()
        self._refresh_db_status()

    # -- window setup -----------------------------------------------------

    def _configure_window(self):
        self.root.title("Neural Defender - Antivirus")
        self.root.geometry("900x600")
        self.root.minsize(760, 520)
        self.root.configure(bg=COLORS["bg"])

        icon_ico = asset_path("Logo.ico")
        if sys.platform == "win32" and os.path.exists(icon_ico):
            try:
                self.root.iconbitmap(icon_ico)
            except tk.TclError:
                logger.warning("Could not set .ico window icon")

        logo_png = asset_path("Logo_small.png")
        if os.path.exists(logo_png):
            try:
                self._icon_img = tk.PhotoImage(file=logo_png)
                self.root.iconphoto(True, self._icon_img)
            except tk.TclError:
                logger.warning("Could not set .png window icon")

    def _configure_styles(self):
        style = ttk.Style()
        # 'clam' is the most themeable built-in ttk theme
        style.theme_use("clam")

        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="#0a1015",
            font=(FONT_FAMILY, 11, "bold"),
            padding=(14, 10),
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLORS["accent_hover"]), ("disabled", COLORS["border"])],
            foreground=[("disabled", COLORS["text_dim"])],
        )

        style.configure(
            "Secondary.TButton",
            background=COLORS["surface_alt"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 10),
            padding=(10, 8),
            borderwidth=1,
        )
        style.map("Secondary.TButton", background=[("active", COLORS["border"])])

        style.configure(
            "ND.Horizontal.TProgressbar",
            troughcolor=COLORS["surface_alt"],
            background=COLORS["accent"],
            bordercolor=COLORS["surface_alt"],
            lightcolor=COLORS["accent"],
            darkcolor=COLORS["accent"],
        )

    # -- layout -------------------------------------------------------------

    def _build_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()

        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 0))
        body.columnconfigure(0, weight=0, minsize=280)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLORS["surface"], height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        logo_png = asset_path("Logo_small.png")
        if os.path.exists(logo_png):
            try:
                logo_img = tk.PhotoImage(file=logo_png)
                logo_label = tk.Label(header, image=logo_img, bg=COLORS["surface"])
                logo_label.image = logo_img  # keep reference
                logo_label.grid(row=0, column=0, padx=(18, 10), pady=10)
            except tk.TclError:
                pass

        title_frame = tk.Frame(header, bg=COLORS["surface"])
        title_frame.grid(row=0, column=1, sticky="w", pady=10)
        tk.Label(
            title_frame, text="Neural Defender", font=(FONT_FAMILY, 18, "bold"),
            bg=COLORS["surface"], fg=COLORS["text"],
        ).pack(anchor="w")
        tk.Label(
            title_frame, text="Signature-based malware scanner", font=(FONT_FAMILY, 9),
            bg=COLORS["surface"], fg=COLORS["text_dim"],
        ).pack(anchor="w")

        btns = tk.Frame(header, bg=COLORS["surface"])
        btns.grid(row=0, column=2, padx=16)
        ttk.Button(btns, text="Help", style="Secondary.TButton", command=self.show_help).pack(side="left", padx=4)
        ttk.Button(btns, text="Support", style="Secondary.TButton", command=self.show_support).pack(side="left", padx=4)

        self.db_status_dot = tk.Label(header, text="●", font=(FONT_FAMILY, 14), bg=COLORS["surface"], fg=COLORS["warning"])
        self.db_status_dot.grid(row=0, column=3, padx=(0, 4))
        self.db_status_label = tk.Label(
            header, text="Checking DB...", font=(FONT_FAMILY, 9),
            bg=COLORS["surface"], fg=COLORS["text_dim"],
        )
        self.db_status_label.grid(row=0, column=4, padx=(0, 18))

    def _build_left_panel(self, parent):
        panel = tk.Frame(parent, bg=COLORS["surface"])
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        for i in range(6):
            panel.rowconfigure(i, weight=0)

        pad = {"padx": 18, "pady": (16, 6)}

        tk.Label(panel, text="SCAN TARGET", font=(FONT_FAMILY, 10, "bold"),
                 bg=COLORS["surface"], fg=COLORS["text_dim"]).grid(row=0, column=0, sticky="w", **pad)

        self.file_label = tk.Label(
            panel, text="No file or folder selected", font=(FONT_FAMILY, 10),
            bg=COLORS["surface_alt"], fg=COLORS["text"], wraplength=240,
            justify="left", anchor="w", padx=10, pady=10,
        )
        self.file_label.grid(row=1, column=0, sticky="ew", padx=18)

        ttk.Button(panel, text="📄  Select File", style="Secondary.TButton",
                   command=self.select_file).grid(row=2, column=0, sticky="ew", padx=18, pady=(12, 6))
        ttk.Button(panel, text="📁  Select Folder", style="Secondary.TButton",
                   command=self.select_folder).grid(row=3, column=0, sticky="ew", padx=18, pady=6)

        self.scan_btn = ttk.Button(panel, text="▶  Start Scan", style="Accent.TButton", command=self.start_scan)
        self.scan_btn.grid(row=4, column=0, sticky="ew", padx=18, pady=(20, 6))

        self.progress = ttk.Progressbar(panel, style="ND.Horizontal.TProgressbar", mode="determinate")
        self.progress.grid(row=5, column=0, sticky="ew", padx=18, pady=(10, 4))

        self.progress_label = tk.Label(
            panel, text="", font=(FONT_FAMILY, 8), bg=COLORS["surface"], fg=COLORS["text_dim"],
        )
        self.progress_label.grid(row=6, column=0, sticky="w", padx=18)

        self.status_label = tk.Label(
            panel, text="", font=(FONT_FAMILY, 15, "bold"),
            bg=COLORS["surface"], fg=COLORS["text"],
        )
        self.status_label.grid(row=7, column=0, sticky="w", padx=18, pady=(20, 10))

    def _build_right_panel(self, parent):
        panel = tk.Frame(parent, bg=COLORS["surface"])
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        tk.Label(panel, text="SCAN OUTPUT", font=(FONT_FAMILY, 10, "bold"),
                 bg=COLORS["surface"], fg=COLORS["text_dim"]).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

        text_frame = tk.Frame(panel, bg=COLORS["surface"])
        text_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(
            text_frame, bg=COLORS["surface_alt"], fg=COLORS["text"],
            insertbackground=COLORS["text"], wrap="word", relief="flat",
            font=("Consolas" if sys.platform == "win32" else "Menlo", 10),
            padx=12, pady=10,
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, command=self.output_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=scrollbar.set)

        # Tags for colored log lines
        self.output_text.tag_configure("safe", foreground=COLORS["safe"])
        self.output_text.tag_configure("infected", foreground=COLORS["infected"])
        self.output_text.tag_configure("error", foreground=COLORS["warning"])
        self.output_text.tag_configure("dim", foreground=COLORS["text_dim"])

        self._log("Neural Defender ready. Select a file or folder to begin.", "dim")

    def _build_footer(self):
        footer = tk.Label(
            self.root,
            text="Neural Defender  •  Built by Aditya, Domain, Shyam, Paras",
            font=(FONT_FAMILY, 9), bg=COLORS["bg"], fg=COLORS["text_dim"],
        )
        footer.grid(row=2, column=0, sticky="w", padx=20, pady=8)

    # -- logging helper -------------------------------------------------------

    def _log(self, message: str, tag: str = None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.output_text.see(tk.END)

    def _clear_log(self):
        self.output_text.delete("1.0", tk.END)

    # -- DB status ------------------------------------------------------------

    def _refresh_db_status(self):
        def check():
            ok, msg = test_connection()
            self.root.after(0, lambda: self._apply_db_status(ok, msg))
        threading.Thread(target=check, daemon=True).start()

    def _apply_db_status(self, ok: bool, msg: str):
        if ok:
            self.db_status_dot.config(fg=COLORS["safe"])
            self.db_status_label.config(text="DB Connected")
        else:
            self.db_status_dot.config(fg=COLORS["infected"])
            self.db_status_label.config(text=f"DB Offline")
            logger.warning("DB status: %s", msg)

    # -- selection ------------------------------------------------------------

    def select_file(self):
        path = filedialog.askopenfilename(title="Select a file to scan")
        if not path:
            return
        self.selected_path = path
        self.is_directory = False
        self.file_label.config(text=f"File:\n{os.path.basename(path)}")
        self._clear_log()
        self._log(f"Selected file: {path}", "dim")
        self.status_label.config(text="")

    def select_folder(self):
        path = filedialog.askdirectory(title="Select a folder to scan")
        if not path:
            return
        self.selected_path = path
        self.is_directory = True
        self.file_label.config(text=f"Folder:\n{os.path.basename(path) or path}")
        self._clear_log()
        self._log(f"Selected folder: {path}", "dim")
        self.status_label.config(text="")

    # -- scanning ---------------------------------------------------------------

    def start_scan(self):
        if self.scan_in_progress:
            return
        if not self.selected_path:
            messagebox.showwarning("No Target", "Please select a file or folder before scanning.")
            return

        self.scan_in_progress = True
        self.scan_btn.config(state="disabled")
        self._clear_log()
        self.status_label.config(text="Scanning...", fg=COLORS["warning"])
        self.progress.config(value=0, maximum=100)
        self.progress_label.config(text="")

        thread = threading.Thread(target=self._run_scan, daemon=True)
        thread.start()

    def _run_scan(self):
        signatures = get_signatures()
        if not signatures:
            self.root.after(0, self._on_no_signatures)
            return

        if self.is_directory:
            self._run_folder_scan(signatures)
        else:
            self._run_single_scan(signatures)

    def _on_no_signatures(self):
        self._log("No signatures available - check database connection or credentials.", "error")
        self.status_label.config(text="⚠ No Signatures", fg=COLORS["warning"])
        self.scan_btn.config(state="normal")
        self.scan_in_progress = False

    def _run_single_scan(self, signatures):
        self.root.after(0, lambda: self._log(f"Scanning: {os.path.basename(self.selected_path)}", "dim"))
        result = scanner.scan_file(self.selected_path, signatures)
        self.root.after(0, lambda: self._handle_single_result(result))

    def _handle_single_result(self, result: scanner.ScanResult):
        self.progress.config(value=100)
        if result.status == ScanStatus.SAFE:
            self._log(result.message, "safe")
            self.status_label.config(text="✓ SAFE", fg=COLORS["safe"])
        elif result.status == ScanStatus.INFECTED:
            self._log(result.message, "infected")
            self.status_label.config(text="⚠ INFECTED", fg=COLORS["infected"])
            self._offer_quarantine([result.file_path])
        else:
            self._log(result.message, "error")
            self.status_label.config(text="✗ ERROR", fg=COLORS["warning"])

        self.scan_btn.config(state="normal")
        self.scan_in_progress = False

    def _run_folder_scan(self, signatures):
        def progress_cb(current, total, fname):
            pct = int((current / total) * 100) if total else 100
            self.root.after(0, lambda: self._update_progress(pct, current, total, fname))

        results = scanner.scan_directory(self.selected_path, signatures, progress_callback=progress_cb)
        self.root.after(0, lambda: self._handle_folder_results(results))

    def _update_progress(self, pct, current, total, fname):
        self.progress.config(value=pct)
        self.progress_label.config(text=f"{current}/{total}  {fname}")

    def _handle_folder_results(self, results: list):
        infected = [r for r in results if r.status == ScanStatus.INFECTED]
        errors = [r for r in results if r.status == ScanStatus.ERROR]
        safe_count = len(results) - len(infected) - len(errors)

        self._log(f"Scan complete: {len(results)} files scanned.", "dim")
        self._log(f"  Safe: {safe_count}", "safe")
        if infected:
            self._log(f"  Infected: {len(infected)}", "infected")
            for r in infected:
                self._log(f"    - {r.file_path}", "infected")
        if errors:
            self._log(f"  Errors: {len(errors)}", "error")

        if infected:
            self.status_label.config(text=f"⚠ {len(infected)} INFECTED", fg=COLORS["infected"])
            self._offer_quarantine([r.file_path for r in infected])
        else:
            self.status_label.config(text="✓ ALL SAFE", fg=COLORS["safe"])

        self.scan_btn.config(state="normal")
        self.scan_in_progress = False

    def _offer_quarantine(self, infected_paths: list):
        count = len(infected_paths)
        plural = "file" if count == 1 else "files"
        if messagebox.askyesno(
            "Infected File(s) Found",
            f"{count} infected {plural} detected.\n\n"
            "Move to quarantine now? (Recommended - this is reversible, "
            "unlike permanent deletion.)",
        ):
            for path in infected_paths:
                dest = scanner.quarantine_file(path)
                if dest:
                    self._log(f"Quarantined -> {dest}", "safe")
                else:
                    self._log(f"Failed to quarantine {path}", "error")

    # -- info dialogs -----------------------------------------------------------

    def show_help(self):
        messagebox.showinfo(
            "Help",
            "How to use Neural Defender:\n\n"
            "1. Click 'Select File' or 'Select Folder' to choose a scan target.\n"
            "2. Click 'Start Scan' to begin.\n"
            "3. Results appear in the output panel on the right.\n"
            "4. Infected files can be moved to quarantine (not deleted) "
            "for safety.\n\n"
            "Quarantined files are stored in:\n"
            f"{scanner.QUARANTINE_DIR}",
        )

    def show_support(self):
        messagebox.showinfo(
            "Support",
            "Contact the Developers:\n\n"
            "Name      Branch\n"
            "Aditya    AI & DS\n"
            "Paras     AI & DS\n"
            "Shyam     AI & DS\n"
            "Domain    AI & DS",
        )


def main():
    root = tk.Tk()
    app = NeuralDefenderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
