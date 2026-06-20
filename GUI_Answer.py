import json
import os
import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

# Import the metadata parser from your cleanup script
from Cleanup_and_Inventory import parse_filename

JSON_FILE = "inventory.json"
INPUT_DIR = "papers"
TARGET_DOC_TYPES = ["qp", "ms"]


class PaperFinderGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("O-Level 5090 Past Paper Finder")
        self.root.geometry("450x320")
        self.root.resizable(False, False)

        # 1. Run Background Organizer on startup
        self.run_background_organizer()

        # 2. Load the freshly generated Database
        self.data = self.load_data(JSON_FILE)
        if not self.data:
            self.root.destroy()
            return

        # Initialize tracking variables for GUI selections
        self.selected_year = tk.StringVar()
        self.selected_session = tk.StringVar()
        self.selected_variant = tk.StringVar()

        # 3. Build Interface
        self.create_widgets()
        self.populate_years()

    def run_background_organizer(self):
        """Silently scans the papers directory on startup and updates inventory.json."""
        if not os.path.exists(INPUT_DIR):
            return  # No folder to organize yet

        pairs = {}
        unpaired_files = []

        for root_dir, _, files in os.walk(INPUT_DIR):
            for file in files:
                if not file.lower().endswith(".pdf"):
                    continue

                file_path = os.path.join(root_dir, file)

                # Skip empty/corrupted files
                try:
                    if os.path.getsize(file_path) == 0:
                        continue
                except OSError:
                    continue

                meta = parse_filename(file)
                if not meta or meta["doc_type"] not in TARGET_DOC_TYPES:
                    continue

                key = (meta["year"], meta["session"], meta["variant"])
                if key not in pairs:
                    pairs[key] = {
                        "year": meta["year"],
                        "session": meta["session"],
                        "session_code": meta["session_code"],
                        "variant": meta["variant"],
                        "qp_path": None,
                        "ms_path": None,
                    }

                if meta["doc_type"] == "qp":
                    pairs[key]["qp_path"] = file_path
                elif meta["doc_type"] == "ms":
                    pairs[key]["ms_path"] = file_path

        complete_inventory = []
        for key, data in pairs.items():
            if data["qp_path"] and data["ms_path"]:
                complete_inventory.append(data)
            else:
                unpaired_files.append(data)

        full_inventory = complete_inventory + unpaired_files

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(full_inventory, f, indent=2, ensure_ascii=False)

    def load_data(self, json_path):
        """Loads the JSON database of past papers."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror(
                "Error",
                f"The database file '{json_path}' was not found.\n"
                "Please run the scraper ('Success.py') first to download papers.",
            )
            return None
        except json.JSONDecodeError:
            messagebox.showerror(
                "Error", "Failed to decode database JSON. Check syntax."
            )
            return None

    def create_widgets(self):
        """Creates the GUI layout."""
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=15, pady=10)

        title_label = ttk.Label(
            header_frame,
            text="O-Level 5090 Biology",
            font=("Arial", 14, "bold"),
        )
        title_label.pack(anchor="w")

        subtitle_label = ttk.Label(
            header_frame,
            text="Database auto-synced. Select options to open documents:",
            font=("Arial", 10, "italic"),
        )
        subtitle_label.pack(anchor="w", pady=(2, 10))

        input_frame = ttk.LabelFrame(self.root, text=" Filter Options ")
        input_frame.pack(fill="x", padx=15, pady=5)

        # Year Dropdown
        ttk.Label(input_frame, text="Year:").grid(
            row=0, column=0, padx=10, pady=8, sticky="w"
        )
        self.year_combo = ttk.Combobox(
            input_frame,
            textvariable=self.selected_year,
            state="readonly",
            width=25,
        )
        self.year_combo.grid(row=0, column=1, padx=10, pady=8)
        self.year_combo.bind("<<ComboboxSelected>>", self.on_year_selected)

        # Session Dropdown
        ttk.Label(input_frame, text="Session:").grid(
            row=1, column=0, padx=10, pady=8, sticky="w"
        )
        self.session_combo = ttk.Combobox(
            input_frame,
            textvariable=self.selected_session,
            state="disabled",
            width=25,
        )
        self.session_combo.grid(row=1, column=1, padx=10, pady=8)
        self.session_combo.bind(
            "<<ComboboxSelected>>", self.on_session_selected
        )

        # Variant Dropdown
        ttk.Label(input_frame, text="Variant:").grid(
            row=2, column=0, padx=10, pady=8, sticky="w"
        )
        self.variant_combo = ttk.Combobox(
            input_frame,
            textvariable=self.selected_variant,
            state="disabled",
            width=25,
        )
        self.variant_combo.grid(row=2, column=1, padx=10, pady=8)
        self.variant_combo.bind(
            "<<ComboboxSelected>>", self.on_variant_selected
        )

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=15, pady=15)

        self.btn_qp = ttk.Button(
            button_frame,
            text="Open Question Paper (QP)",
            state="disabled",
            command=self.open_qp,
        )
        self.btn_qp.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_ms = ttk.Button(
            button_frame,
            text="Open Mark Scheme (MS)",
            state="disabled",
            command=self.open_ms,
        )
        self.btn_ms.pack(side="right", expand=True, fill="x", padx=(5, 0))

    def populate_years(self):
        years = sorted(
            list(set(str(entry.get("year")) for entry in self.data)),
            reverse=True,
        )
        self.year_combo["values"] = years

    def on_year_selected(self, event):
        year = self.selected_year.get()
        self.selected_session.set("")
        self.selected_variant.set("")
        self.session_combo["values"] = []
        self.variant_combo["values"] = []
        self.session_combo.config(state="readonly")
        self.variant_combo.config(state="disabled")
        self.btn_qp.config(state="disabled")
        self.btn_ms.config(state="disabled")

        sessions = set()
        for entry in self.data:
            if str(entry.get("year")) == year:
                if entry.get("session"):
                    sessions.add(entry["session"])
        self.session_combo["values"] = sorted(list(sessions))

    def on_session_selected(self, event):
        year = self.selected_year.get()
        session = self.selected_session.get()
        self.selected_variant.set("")
        self.variant_combo["values"] = []
        self.variant_combo.config(state="readonly")
        self.btn_qp.config(state="disabled")
        self.btn_ms.config(state="disabled")

        variants = set()
        for entry in self.data:
            if (
                str(entry.get("year")) == year
                and entry.get("session") == session
            ):
                if entry.get("variant") is not None:
                    variants.add(str(entry["variant"]))
        self.variant_combo["values"] = sorted(
            list(variants), key=lambda x: int(x) if x.isdigit() else x
        )

    def on_variant_selected(self, event):
        self.btn_qp.config(state="normal")
        self.btn_ms.config(state="normal")

    def get_selected_match(self):
        year = self.selected_year.get()
        session = self.selected_session.get()
        variant = self.selected_variant.get()
        for entry in self.data:
            if (
                str(entry.get("year")) == year
                and entry.get("session") == session
                and str(entry.get("variant")) == variant
            ):
                return entry
        return None

    def open_document(self, path_key):
        match = self.get_selected_match()
        if not match:
            messagebox.showerror("Error", "Could not locate paper mapping.")
            return

        file_path = match.get(path_key)
        if not file_path:
            messagebox.showinfo(
                "Info", "This document is not available for this variant."
            )
            return

        normalized_path = os.path.normpath(file_path)
        if not os.path.exists(normalized_path):
            messagebox.showerror(
                "File Not Found", f"Could not find file on disk:\n{file_path}"
            )
            return

        try:
            if platform.system() == "Windows":
                os.startfile(normalized_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", normalized_path], check=True)
            else:
                subprocess.run(["xdg-open", normalized_path], check=True)
        except Exception as e:
            messagebox.showerror(
                "Error", f"Failed to open document:\n{str(e)}"
            )

    def open_qp(self):
        self.open_document("qp_path")

    def open_ms(self):
        self.open_document("ms_path")


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    elif "clam" in style.theme_names():
        style.theme_use("clam")

    app = PaperFinderGUI(root)
    root.mainloop()